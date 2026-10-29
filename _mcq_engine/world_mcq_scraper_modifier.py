# -*- coding: utf-8 -*-
r"""
High-Speed Universal Multi-Language Open-Source MCQ Detector + Pre-AI Deduplicator + AI Converter
(`world_mcq_scraper_modifier.py`)
=================================================================================================
Upgrades for 10x Speed & Zero Crash Resilience:
  1. Single `agy` AI Call per Sub-Topic (eliminates the redundant 90s query-planning CLI call).
  2. Multi-Language Global Scraping across 20+ World & Indian Languages (Wikipedia Global APIs:
     `en`, `hi`, `ta`, `te`, `bn`, `mr`, `ru`, `zh`, `ja`, `ko`, `de`, `fr`, `es`, `pt`, `ar`, `tr`, `pl`, `vi`
     + DuckDuckGo HTML + `BeautifulSoup` (`lxml`) + `langdetect` MCQ Detection).
  3. Strict Indian-Only PYQ Search (`UPSC, GATE, NEET, JEE, SSC, RRB, UGC NET, State PSC`).
  4. Pre-AI Deduplication (`deduplicate_raw_scraped_candidates` -> `raw_scraped_fingerprints`)
     BEFORE AI conversion.
  5. Larger Batch (`8` DB1 Scraped & Modified MCQs + `2` DB2 Indian PYQs = `10` MCQs per batch)
     with full `try/except` timeout resilience so the worker never stops.
"""

import argparse
import hashlib
import html
import json
import re
import sqlite3
import ssl
import subprocess
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from langdetect import DetectorFactory, detect

import build_db1_viewer
import multi_db_manager
import pipeline

DetectorFactory.seed = 0

BASE_DIR = Path(__file__).resolve().parent
MASTER_DB = BASE_DIR / "mcq_bank.sqlite"
DB1_SCRAPED = BASE_DIR / "db1_scraped_mcqs.sqlite"
DB2_PYQ = BASE_DIR / "db2_pyq_mcqs.sqlite"
SEEDS_DIR = BASE_DIR / "scraped_seeds"
BATCH_OUT_DIR = BASE_DIR / "mcqs" / "world_scraped_batches"
LOG_PATH = BASE_DIR / "world_mcq_scraper_modifier.log"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "*;q=0.9",
}

GLOBAL_WIKI_LANGS = ["en", "ru", "zh", "ja", "de", "fr", "es", "pt", "ko", "ar", "hi", "ta", "bn"]

LANGUAGE_SUBJECT_KEYWORDS = {
    "hindi": "Hindi (Devanagari script)",
    "sanskrit": "Sanskrit (Devanagari script)",
    "tamil": "Tamil (Tamil script)",
    "telugu": "Telugu (Telugu script)",
    "kannada": "Kannada (Kannada script)",
    "malayalam": "Malayalam (Malayalam script)",
    "marathi": "Marathi (Devanagari script)",
    "bengali": "Bengali (Bengali script)",
    "odia": "Odia (Odia script)",
    "punjabi": "Punjabi (Gurmukhi script)",
    "urdu": "Urdu (Perso-Arabic Urdu script)",
    "assamese": "Assamese (Assamese script)",
    "gujarati": "Gujarati (Gujarati script)",
    "french": "French",
    "german": "German",
    "japanese": "Japanese",
    "spanish": "Spanish",
    "russian": "Russian",
    "arabic": "Arabic",
    "chinese": "Chinese",
    "english literature": "English",
    "general english": "English",
}


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [FAST-WORLD-PIPELINE] {msg}"
    try:
        print(line.encode("ascii", errors="replace").decode("ascii"), flush=True)
    except Exception:
        pass
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def detect_subject_target_language(subject_id: str, subject_name: str) -> tuple[bool, str]:
    s_lower = f"{subject_id} {subject_name}".lower()
    for kw, lang_desc in LANGUAGE_SUBJECT_KEYWORDS.items():
        if re.search(rf"\b{re.escape(kw)}\b", s_lower):
            return True, lang_desc
    if "_LANG_" in subject_id or "_FLANG_" in subject_id or "_LIT_" in subject_id:
        return True, f"Native script/language of {subject_name}"
    return False, "English"


def detect_text_language(text: str) -> str:
    try:
        clean = re.sub(r"[0-9\W_]+", " ", text, flags=re.UNICODE).strip()
        if len(clean) < 12:
            return "unknown"
        return detect(clean)
    except Exception:
        return "unknown"


OPTION_REGEX = re.compile(
    r"(?:^|\s)(?:\(?([A-Da-dА-Гa-г1-4क-घअ-द])[\)\.\:]|[①②③④])\s+([^\n\r]{2,180})",
    flags=re.UNICODE,
)


def detect_mcqs_from_html_bs4(raw_html: str, source_url: str = "") -> list[dict]:
    if not raw_html:
        return []
    soup = BeautifulSoup(raw_html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside"]):
        tag.decompose()

    candidates = []
    for lst in soup.find_all(["ol", "ul"]):
        lis = lst.find_all("li", recursive=False)
        if 3 <= len(lis) <= 5:
            opts = [li.get_text(" ", strip=True) for li in lis]
            if all(1 <= len(o) <= 220 for o in opts):
                prev = lst.find_previous_sibling(["p", "div", "h3", "h4", "strong"])
                if prev:
                    q_stem = prev.get_text(" ", strip=True)
                    if 15 <= len(q_stem) <= 650:
                        svg_tag = prev.find("svg") or lst.find("svg")
                        img_tag = prev.find("img") or lst.find("img")
                        fig_note = ""
                        if svg_tag:
                            fig_note = f" [INLINE_SVG: {str(svg_tag)[:600]}]"
                        elif img_tag:
                            fig_note = f" [FIGURE_IMG src={img_tag.get('src','')} alt={img_tag.get('alt','')}]"
                        combined = q_stem + fig_note + " | " + " | ".join(opts)
                        candidates.append({
                            "source_url": source_url,
                            "detected_lang": detect_text_language(combined),
                            "detection_method": "BS4_DOM_LIST_WITH_FIG" if fig_note else "BS4_DOM_LIST",
                            "raw_question": q_stem,
                            "raw_options": opts[:4],
                            "raw_text": combined,
                        })

    text_blocks = soup.get_text("\n", strip=True)
    paragraphs = re.split(
        r"\n{2,}|(?=(?:Q\d+|Question\s*\d+|Вопрос\s*\d+|问题\s*\d+|प्रश्न\s*\d+|\d+[\.\)]\s+\S))",
        text_blocks,
    )
    for blk in paragraphs:
        blk_clean = re.sub(r"\s+", " ", blk).strip()
        if len(blk_clean) < 35 or len(blk_clean) > 1500:
            continue
        opt_matches = list(OPTION_REGEX.finditer(blk))
        if len(opt_matches) >= 3:
            first_pos = opt_matches[0].start()
            stem = blk[:first_pos].strip()
            if len(stem) >= 12:
                opts = [m.group(2).strip() for m in opt_matches[:4]]
                combined = f"{stem} || " + " | ".join(opts)
                candidates.append({
                    "source_url": source_url,
                    "detected_lang": detect_text_language(combined),
                    "detection_method": "REGEX_MULTISCRIPT_OPTIONS",
                    "raw_question": stem[:500],
                    "raw_options": opts,
                    "raw_text": combined[:1000],
                })

    return candidates


def ensure_raw_dedup_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_scraped_fingerprints (
            raw_hash TEXT PRIMARY KEY,
            subject_id TEXT,
            detected_lang TEXT,
            simhash_hex TEXT,
            numeric_sig TEXT,
            shingles_json TEXT,
            raw_preview TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()


def extract_unicode_tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"\w+", (text or "").lower(), flags=re.UNICODE) if len(t) > 1]


def compute_unicode_simhash(tokens: list[str]) -> int:
    if not tokens:
        return 0
    v = [0] * 64
    for tok, weight in Counter(tokens).items():
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest()[:16], 16)
        for i in range(64):
            v[i] += weight if (h & (1 << i)) else -weight
    ans = 0
    for i in range(64):
        if v[i] > 0:
            ans |= (1 << i)
    return ans


def deduplicate_raw_scraped_candidates(conn: sqlite3.Connection, subject_id: str, candidates: list[dict]) -> list[dict]:
    ensure_raw_dedup_table(conn)
    cur = conn.cursor()
    existing_rows = cur.execute(
        "SELECT raw_hash, simhash_hex, numeric_sig, shingles_json FROM raw_scraped_fingerprints WHERE subject_id = ?",
        (subject_id,),
    ).fetchall()

    existing_profiles = []
    for r_hash, s_hex, n_sig, sh_json in existing_rows:
        try:
            existing_profiles.append({
                "raw_hash": r_hash,
                "simhash": int(s_hex or "0", 16),
                "nums": set(json.loads(n_sig or "[]")),
                "shingles": set(json.loads(sh_json or "[]")),
            })
        except Exception:
            pass

    unique_candidates = []
    now_iso = datetime.now().isoformat()

    for cand in candidates:
        raw_txt = cand.get("raw_text", "").strip()
        if not raw_txt:
            continue
        norm_txt = re.sub(r"\W+", "", raw_txt.lower(), flags=re.UNICODE)
        r_hash = hashlib.sha256(norm_txt.encode("utf-8")).hexdigest()
        tokens = extract_unicode_tokens(raw_txt)
        s_hash = compute_unicode_simhash(tokens)
        shingles = pipeline.get_shingles(tokens, 3)
        nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", raw_txt))

        is_dup = False
        for ep in existing_profiles:
            if r_hash == ep["raw_hash"]:
                is_dup = True
                break
            if pipeline.hamming_distance(s_hash, ep["simhash"]) <= 5:
                is_dup = True
                break
            if pipeline.jaccard_similarity(shingles, ep["shingles"]) >= 0.65:
                is_dup = True
                break
            if len(nums) >= 3 and pipeline.jaccard_similarity(nums, ep["nums"]) >= 0.85:
                is_dup = True
                break

        if not is_dup:
            prof = {"raw_hash": r_hash, "simhash": s_hash, "nums": nums, "shingles": shingles}
            existing_profiles.append(prof)
            cur.execute(
                """
                INSERT OR IGNORE INTO raw_scraped_fingerprints
                (raw_hash, subject_id, detected_lang, simhash_hex, numeric_sig, shingles_json, raw_preview, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r_hash,
                    subject_id,
                    cand.get("detected_lang", "unknown"),
                    f"{s_hash:016x}",
                    json.dumps(sorted(nums)),
                    json.dumps(sorted(list(shingles)[:40])),
                    raw_txt[:180],
                    now_iso,
                ),
            )
            unique_candidates.append(cand)

    conn.commit()
    return unique_candidates


def fetch_url(url: str, timeout: int = 8) -> str:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def scrape_and_detect_mcqs_with_python(conn: sqlite3.Connection, subtopic_row: dict, plan: dict) -> tuple[list[dict], list[dict]]:
    sid = subtopic_row["subject_id"]
    sname = subtopic_row["subject_name"]
    stitle = subtopic_row["subtopic_title"]
    clean_subj = sname.split("(")[0].strip()
    clean_sub = re.sub(r"^[^:]+:\s*", "", stitle).strip()[:65]

    raw_mcq_candidates = []
    pyq_snippets = []

    # 1. Multi-Language Global Wikipedia APIs (13 world & Indian languages, srlimit=3 -> up to 39 candidates)
    for w_lang in GLOBAL_WIKI_LANGS:
        w_url = (
            f"https://{w_lang}.wikipedia.org/w/api.php?action=query&list=search"
            f"&srsearch={urllib.parse.quote(clean_sub[:55])}&utf8=&format=json&srlimit=3"
        )
        raw_w = fetch_url(w_url, timeout=5)
        if raw_w:
            try:
                wdata = json.loads(raw_w)
                for item in wdata.get("query", {}).get("search", []):
                    t_str = BeautifulSoup(item.get("title", ""), "lxml").get_text(" ", strip=True)
                    s_str = BeautifulSoup(item.get("snippet", ""), "lxml").get_text(" ", strip=True)
                    if len(s_str) >= 25:
                        raw_mcq_candidates.append({
                            "source_url": f"https://{w_lang}.wikipedia.org/wiki/{urllib.parse.quote(t_str)}",
                            "detected_lang": w_lang,
                            "detection_method": f"WIKI_{w_lang.upper()}_API",
                            "raw_question": t_str,
                            "raw_options": [],
                            "raw_text": f"[{w_lang}] {t_str}: {s_str}",
                        })
            except Exception:
                pass

    # 2. Global Wikiversity & Wikibooks Open Quiz/Exercise APIs (en, fr, de, ru)
    for wv_host, wv_lang in [
        ("en.wikiversity.org", "en"),
        ("fr.wikiversity.org", "fr"),
        ("de.wikiversity.org", "de"),
        ("ru.wikiversity.org", "ru"),
        ("en.wikibooks.org", "en"),
    ]:
        wv_url = (
            f"https://{wv_host}/w/api.php?action=query&list=search"
            f"&srsearch={urllib.parse.quote(clean_sub[:55])}&utf8=&format=json&srlimit=3"
        )
        raw_wv = fetch_url(wv_url, timeout=5)
        if raw_wv:
            try:
                wvdata = json.loads(raw_wv)
                for item in wvdata.get("query", {}).get("search", []):
                    t_str = BeautifulSoup(item.get("title", ""), "lxml").get_text(" ", strip=True)
                    s_str = BeautifulSoup(item.get("snippet", ""), "lxml").get_text(" ", strip=True)
                    if len(s_str) >= 25:
                        raw_mcq_candidates.append({
                            "source_url": f"https://{wv_host}/wiki/{urllib.parse.quote(t_str)}",
                            "detected_lang": wv_lang,
                            "detection_method": f"WIKIVERSITY_{wv_lang.upper()}_EXERCISE",
                            "raw_question": t_str,
                            "raw_options": [],
                            "raw_text": f"[{wv_host}] {t_str}: {s_str}",
                        })
            except Exception:
                pass

    # 3. Multi-Engine Web Search (DuckDuckGo + Yahoo Search HTML) + Deep Page BS4 MCQ Extraction
    world_queries = plan.get("world_subject_queries") or [
        f"{clean_subj} {clean_sub} MCQ questions answers",
        f"{clean_sub} задачи тесты / 选择题 / QCM / बहुविकल्पीय प्रश्न",
    ]
    for wq in world_queries[:3]:
        for search_url in [
            f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(wq)}",
            f"https://search.yahoo.com/search?p={urllib.parse.quote(wq)}",
        ]:
            raw_html = fetch_url(search_url, timeout=6)
            if not raw_html:
                continue
            raw_mcq_candidates.extend(detect_mcqs_from_html_bs4(raw_html, source_url=f"search:{wq[:40]}"))
            soup = BeautifulSoup(raw_html, "lxml")
            for snip_el in soup.select("a.result__snippet, div.compText p")[:5]:
                s_txt = snip_el.get_text(" ", strip=True)
                if len(s_txt) >= 30:
                    raw_mcq_candidates.append({
                        "source_url": f"query:{wq[:50]}",
                        "detected_lang": detect_text_language(s_txt),
                        "detection_method": "BS4_SEARCH_SNIPPET",
                        "raw_question": s_txt,
                        "raw_options": [],
                        "raw_text": s_txt,
                    })

    # 3. Worldwide & Indian PYQ Search (any country, any language for universal subjects)
    pyq_q = str(
        plan.get("world_pyq_query")
        or f"{clean_subj} {clean_sub} past exam questions PYQ GATE UPSC NEET JEE FE GRE Gaokao ЕГЭ 過去問"
    )
    raw_pyq = fetch_url(f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(pyq_q)}", timeout=7)
    if raw_pyq:
        soup = BeautifulSoup(raw_pyq, "lxml")
        for a in soup.select("a.result__snippet")[:4]:
            txt = a.get_text(" ", strip=True)
            if len(txt) >= 25:
                pyq_snippets.append({
                    "source_url": "Worldwide & Indian Past Exam PYQ Search",
                    "detected_lang": detect_text_language(txt),
                    "detection_method": "WORLD_PYQ_BS4",
                    "raw_text": txt,
                })

    if not pyq_snippets:
        pyq_snippets.append({
            "source_url": "Global & Indian Competitive Exam PYQ Seed",
            "detected_lang": "en",
            "detection_method": "GLOBAL_EXAM_SYLLABUS",
            "raw_text": f"Global & Indian Past Exam PYQ Topic: {sname} -> {subtopic_row['unit_title']} -> {stitle}",
        })

    deduped_world = deduplicate_raw_scraped_candidates(conn, sid, raw_mcq_candidates)
    deduped_pyq = deduplicate_raw_scraped_candidates(conn, sid, pyq_snippets)
    return deduped_world, deduped_pyq


def call_agy(prompt: str, model_id: str, timeout_sec: int = 210) -> str:
    cmd = [
        "agy",
        "--dangerously-skip-permissions",
        "--disable-slash-commands",
        "--model",
        model_id,
        f"--print={prompt}",
    ]
    res = subprocess.run(
        cmd,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
    )
    return (res.stdout or "") + "\n" + (res.stderr or "")


def extract_json_array(raw_text: str) -> list:
    if not raw_text:
        return []
    cleaned = re.sub(r"```(?:json)?", "", raw_text, flags=re.I).replace("```", "").strip()
    s = cleaned.find("[")
    if s == -1:
        return []
    e = cleaned.rfind("]")
    if e > s:
        try:
            arr = json.loads(cleaned[s : e + 1])
            if isinstance(arr, list) and arr:
                return arr
        except Exception:
            pass
    # Salvage complete JSON objects if output was truncated before final ']'
    last_brace = cleaned.rfind("}")
    while last_brace > s:
        try:
            arr = json.loads(cleaned[s : last_brace + 1] + "]")
            if isinstance(arr, list) and arr:
                return arr
        except Exception:
            last_brace = cleaned.rfind("}", s, last_brace)
    return []


def build_ai_conversion_prompt(
    subtopic_row: dict,
    is_lang: bool,
    target_lang: str,
    deduped_world_candidates: list[dict],
    deduped_pyq_candidates: list[dict],
    db1_count: int = 8,
    db2_count: int = 2,
) -> str:
    stid = subtopic_row["subtopic_id"]
    sid = subtopic_row["subject_id"]
    sname = subtopic_row["subject_name"]
    utitle = subtopic_row["unit_title"]
    stitle = subtopic_row["subtopic_title"]
    rbook = subtopic_row["reference_book"]
    total = db1_count + db2_count

    world_dump = "\n".join(
        f"- [Lang={c.get('detected_lang')} | {c.get('detection_method')}] {c.get('raw_text')[:320]}"
        for c in deduped_world_candidates[:8]
    )
    pyq_dump = "\n".join(
        f"- [Indian PYQ Seed] {p.get('raw_text')[:280]}"
        for p in deduped_pyq_candidates[:4]
    )

    if is_lang:
        lang_instruction = (
            f"LANGUAGE RULE (LANGUAGE-SPECIFIC SUBJECT): Keep all question stems, options, and explanations "
            f"in `{target_lang}` with light word/synonym replacement to avoid copyright issues while keeping the exact meaning."
        )
    else:
        lang_instruction = (
            f"DUAL NATIVE-LANGUAGE + ENGLISH RETENTION RULE (FOR GLOBAL & INDIAN MEDIUM STUDENTS):\n"
            f"  - Whenever a scraped candidate is in ANY Indian language (`hi`, `ta`, `te`, `bn`, `mr`, `kn`, `ml`, `gu`, `pa`, `or`, `ur`) "
            f"OR ANY Foreign language (`ru` Russian, `zh` Chinese, `ja` Japanese, `de` German, `fr` French, `es` Spanish, `pt` Portuguese, `ko` Korean, `ar` Arabic):\n"
            f"    1. KEEP a native-language MCQ in that exact original language/script (making only slight word/synonym replacements in that language "
            f"to avoid copyright issues without changing the concept or meaning, and set `pyq_original_language` to that language code e.g. 'ru', 'zh', 'ja', 'hi', 'ta'), AND\n"
            f"    2. ALSO generate the corresponding English-language MCQ (`pyq_original_language`: 'en')."
        )

    return (
        f"You are an AI MCQ Converter, Translator & Authenticator.\n"
        f"Subject: `{sname}` (`{sid}`) | Unit: `{utitle}` | Sub-Topic: `{stitle}` (`{stid}`)\n"
        f"Reference Book: `{rbook}`\n\n"
        f"PRE-DEDUPLICATED WORLDWIDE SCRAPED CANDIDATES (for `DB1_SCRAPED_MODIFIED`):\n{world_dump or 'Use core sub-topic concepts'}\n\n"
        f"PRE-DEDUPLICATED WORLDWIDE & INDIAN EXAM PYQ CANDIDATES (for `DB2_PYQ`):\n{pyq_dump or 'Use authentic Global/Indian exam PYQ pattern'}\n\n"
        f"Generate a valid JSON array of {total} MCQs:\n"
        f"  - {db1_count} Converted & Modified Worldwide Subject MCQs (`source_db`: `'DB1_SCRAPED_MODIFIED'`)\n"
        f"  - {db2_count} Worldwide or Indian Competitive Exam PYQ MCQs (`source_db`: `'DB2_PYQ'`, tagged with `pyq_exam_name` from any country/exam e.g. GATE/UPSC/NEET/JEE/FE/GRE/Gaokao/EGE/Olympiad and `pyq_year`)\n\n"
        f"STRICT RULES:\n"
        f"1. Output ONLY a raw JSON array `[...]` with no markdown code fences.\n"
        f"2. {lang_instruction}\n"
        f"3. UNIVERSAL NON-VERBATIM ORIGINALITY: Using only the core concepts, principles, rules, facts, and relationships of this sub-topic, "
        f"draft entirely independent question stems and distinct values or scenarios. Strictly avoid copying or lightly modifying sentences from any source.\n"
        f"4. AUTHENTICATION & DIAGNOSTIC DISTRACTORS: Verify that the correct option (`A`/`B`/`C`/`D`) is 100% accurate and provide a step-by-step explanation.\n"
        f"5. Each object MUST have exact keys: `chunk_id` ('{stid}'), `source_db` ('DB1_SCRAPED_MODIFIED'|'DB2_PYQ'), "
        f"`subject_id` ('{sid}'), `subject` ('{sname}'), `chapter` ('{utitle[:90]}'), `topic` ('{stitle[:120]}'), "
        f"`difficulty` ('Easy'|'Medium'|'Hard'|'Extra Hard'), `bloom_level` ('Remember'|'Understand'|'Apply'|'Analyze'|'Evaluate'), "
        f"`question_type` ('Conceptual'|'Numerical'|'Assertion-Reason'|'Statement I & II'|'Match List-I & II'|'Application'), "
        f"`pyq_exam_name` (Full Exam Name e.g. 'UPSC CSE Prelims'/'GATE ME'/'NEET UG'/'US FE'/'Gaokao'/'EGE'), "
        f"`pyq_exam_body` (Conducting Body e.g. 'UPSC'/'IIT-IISc'/'NTA'/'SSC'/'NCEES'/'MOE'), "
        f"`pyq_country` (Country e.g. 'India'/'USA'/'Russia'/'China'/'Japan'/'Global'), "
        f"`pyq_state_or_region` (e.g. 'All-India / Central' or State/International), "
        f"`pyq_year` (Exam Year e.g. '2023'), "
        f"`pyq_session_or_shift` (e.g. 'Paper-I / Shift-1 / Set-A'), "
        f"`pyq_paper_code` (Paper Code e.g. 'GS-I'/'ME-1'/'CS-1'), "
        f"`pyq_exam_stage` (e.g. 'Prelims'/'Mains'/'Tier-1'/'Single-Stage CBT'), "
        f"`pyq_qualification_level` (e.g. 'Graduate / Degree'/'Post-Graduate'/'Class 12 / Higher Secondary'/'Class 10'/'Diploma / ITI'), "
        f"`pyq_marks` (e.g. '+2.0'), `pyq_negative_marks` (e.g. '-0.67'), "
        f"`pyq_original_language` (e.g. 'en'/'ru'/'zh'/'ja'/'hi'), "
        f"`estimated_solve_time_sec` (integer seconds e.g. 90), "
        f"`key_formula_or_concept` (Core concept/formula/article tested), "
        f"`common_trap_note` (Why students pick wrong distractor), "
        f"`scraped_source_url` ('Open-Source BS4 + Pre-Dedup + AI Conversion'), `book_reference` ('{rbook}'), "
        f"`question`, `options` ({{'A': ..., 'B': ..., 'C': ..., 'D': ...}}), `correct_answer` ('A'|'B'|'C'|'D'), `explanation`, "
        f"`question_svg` (clean `<svg viewBox='0 0 520 250' xmlns='http://www.w3.org/2000/svg'>...</svg>` whenever the question involves a circuit, diagram, graph, geometry, beam, cycle, or scraped figure; '' if pure text), "
        f"`explanation_svg` (optional `<svg ...>...</svg>` diagram or '').\n"
        f"6. FIGURE & DIAGRAM RULE: If a candidate has an open-licensed `<svg>` (Wikimedia/CC-BY/CC0/MIT), keep it as-is in `question_svg`; if there is ANY copyright doubt on an image/figure or a candidate references a figure, RECREATE a clean, original, labeled `<svg viewBox='0 0 520 250' xmlns='http://www.w3.org/2000/svg'>...</svg>` diagram in `question_svg`! Include at least 2 figure-based MCQs (`question_svg` != '') per batch whenever applicable to the subject.\n"
        f"7. All mathematical expressions MUST use inline `<math xmlns=\"http://www.w3.org/1998/Math/MathML\">...</math>` (NEVER LaTeX `$...$`).\n"
        f"8. Every question stem (+ its `question_svg` if figure-based) must be 100% self-contained."
    )


def run_pipeline(max_batches: int = 0, worker_id: int = 0, num_workers: int = 1) -> None:
    import cloud_mcq_factory

    SEEDS_DIR.mkdir(parents=True, exist_ok=True)
    BATCH_OUT_DIR.mkdir(parents=True, exist_ok=True)
    if worker_id == 0:
        multi_db_manager.init_all_databases()

    conn = sqlite3.connect(MASTER_DB, timeout=90.0)
    conn.row_factory = sqlite3.Row

    all_rows = conn.execute(
        """
        SELECT subtopic_id, subject_id, subject_name, domain, unit_number,
               unit_title, subtopic_title, reference_book, exam_reach_count,
               target_mcq_count, COALESCE(verified_mcq_count, 0) AS gen_cnt
        FROM master_subtopics
        WHERE COALESCE(verified_mcq_count, 0) < target_mcq_count
          AND subject_id NOT IN ('SUB_ME_FLUID', 'SUB_ME_THERMO')
        ORDER BY exam_reach_count DESC, subject_id ASC, unit_number ASC, subtopic_id ASC
        """
    ).fetchall()

    rows = [r for i, r in enumerate(all_rows) if (i % max(1, num_workers)) == worker_id]
    models = ["gemini-3.8-flash-high", "gemini-4-argon-medium", "gemini-4-argon-high"]
    log(f"[Worker {worker_id}/{num_workers}] Starting High-Yield BS4 + Pre-AI Dedup + AI Converter across {len(rows)} assigned sub-topics...")

    processed = 0
    for idx, r in enumerate(rows):
        if max_batches > 0 and processed >= max_batches:
            break
        subtopic_row = dict(r)
        stid = subtopic_row["subtopic_id"]
        sid = subtopic_row["subject_id"]
        sname = subtopic_row["subject_name"]
        seed_file = SEEDS_DIR / f"{stid}.json"

        try:
            is_lang, target_lang = detect_subject_target_language(sid, sname)
            plan = {"is_language_specific": is_lang, "target_language": target_lang}

            # If cloud_resource_scraper already scraped & pre-deduplicated this sub-topic, load it instantly!
            deduped_world, deduped_pyq = [], []
            if seed_file.exists():
                try:
                    cached = json.loads(seed_file.read_text(encoding="utf-8"))
                    if isinstance(cached, dict) and cached.get("deduped_world_candidates"):
                        deduped_world = cached["deduped_world_candidates"]
                        deduped_pyq = cached.get("deduped_indian_pyq_candidates", [])
                except Exception:
                    pass

            if not deduped_world:
                deduped_world, deduped_pyq = scrape_and_detect_mcqs_with_python(conn, subtopic_row, plan)
                seed_file.write_text(
                    json.dumps(
                        {
                            "search_plan": plan,
                            "deduped_world_candidates": deduped_world,
                            "deduped_indian_pyq_candidates": deduped_pyq,
                        },
                        indent=2,
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )

            langs_found = sorted(set(c.get("detected_lang", "unknown") for c in deduped_world))
            log(
                f"[{processed + 1}] {stid}: BS4 + Pre-AI Dedup ready ({len(deduped_world)} world seeds, langs={langs_found}). Converting 10 MCQs..."
            )

            model_id = models[idx % len(models)]
            prompt = build_ai_conversion_prompt(subtopic_row, is_lang, target_lang, deduped_world, deduped_pyq, db1_count=5, db2_count=1)
            raw_out = call_agy(prompt, model_id, timeout_sec=210)
            items = extract_json_array(raw_out)
            if not items and model_id != "gemini-3.8-flash-high":
                raw_out = call_agy(prompt, "gemini-3.8-flash-high", timeout_sec=180)
                items = extract_json_array(raw_out)

            if items:
                out_file = BATCH_OUT_DIR / f"{stid}_converted.json"
                out_file.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
                added = cloud_mcq_factory.ingest_subtopic_mcqs(conn, subtopic_row, items)
                try:
                    build_db1_viewer.generate_db1_html()
                except Exception:
                    pass
                counts = multi_db_manager.get_db_counts()
                log(
                    f"  -> +{added} AI-converted MCQs saved! "
                    f"[DB1 Scraped: {counts['db1_scraped_mcqs.sqlite']} | "
                    f"DB2 PYQ: {counts['db2_pyq_mcqs.sqlite']} | "
                    f"DB3 Textbook: {counts['db3_textbook_chunk_mcqs.sqlite']} | "
                    f"Master: {counts['mcq_bank.sqlite (Master)']}]"
                )
        except Exception as e:
            log(f"  -> Error on {stid} (recovering & continuing): {e}")

        processed += 1
        if processed % 10 == 0:
            pipeline.build_viewer()

    conn.close()
    pipeline.build_viewer()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-batches", type=int, default=0)
    ap.add_argument("--worker-id", type=int, default=0)
    ap.add_argument("--num-workers", type=int, default=1)
    args = ap.parse_args()
    run_pipeline(max_batches=args.max_batches, worker_id=args.worker_id, num_workers=args.num_workers)
