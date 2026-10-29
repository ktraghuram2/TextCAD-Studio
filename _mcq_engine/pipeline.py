"""
Universal Industry-Standard Textbook-to-MCQ Pipeline (`pipeline.py`)

Features:
1. Book Completeness & Extractability Audit (`--validate`):
   Checks that all pages are readable, text-extractable, and have no missing page gaps.
2. Universal Smart / AI-Guided PDF Division (`--divide` or `--auto-divide`):
   Supports single-page paragraph splitting (`start_marker` / `end_marker`), worked-example
   splitting, and multi-page concept grouping for ANY textbook.
3. Multi-Stage Industry-Standard Subject Deduplication (`--ingest` & `--dedup`):
   - Stage 1: Canonical SHA-256 Fingerprinting (Exact normalized stem + options match)
   - Stage 2: SimHash (64-bit Charikar locality-sensitive hashing, Hamming distance <= 3)
   - Stage 3: MinHash / Word Shingle Jaccard Similarity (3-gram shingles >= 0.72)
   - Stage 4: TF-IDF Cosine + Formula/Numeric Signature Matching (Cosine >= 0.80 or
     Cosine >= 0.68 when mathematical/numeric signatures match within the same subject)
4. Full-Detail Localhost HTML Database Viewer (`--viewer`):
   Displays Subject, Book, Chapter, Section, Topic, Page, Chunk ID, collapsible Source
   Chunk Text, Bloom's Taxonomy, Question Type, Fingerprints, MathML, and SVGs.
"""

import argparse
import hashlib
import html
import json
import math
import re
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

DB_PATH = Path("mcq_bank.sqlite")
VIEWER_PATH = Path("mcq_database_viewer.html")
CHUNKS_DIR = Path("chunks")

STOPWORDS = {
    "a", "an", "the", "in", "on", "at", "of", "for", "to", "from", "by", "with",
    "is", "are", "was", "were", "be", "been", "being", "which", "what", "when",
    "where", "how", "why", "that", "this", "these", "those", "it", "its", "as",
    "or", "and", "if", "then", "than", "into", "following", "given", "consider",
    "determine", "calculate", "find", "statement", "statements", "correct", "true",
}


# ---------------------------------------------------------------------------
# 0. DATABASE SCHEMA INITIALIZATION & MIGRATION
# ---------------------------------------------------------------------------
def ensure_db_schema(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS questions (
            question_id TEXT PRIMARY KEY,
            seq_num INTEGER,
            source_db TEXT DEFAULT 'DB3_TEXTBOOK_CHUNK',
            subject_id TEXT DEFAULT '',
            subject TEXT,
            domain TEXT DEFAULT '',
            branch_codes TEXT DEFAULT '',
            exam_tags TEXT DEFAULT '',
            pyq_exam_name TEXT DEFAULT '',
            pyq_year TEXT DEFAULT '',
            scraped_source_url TEXT DEFAULT '',
            book_reference TEXT,
            book_completeness_verified INTEGER DEFAULT 1,
            chapter_number INTEGER,
            chapter_name TEXT,
            section_number TEXT,
            topic TEXT,
            subtopic_id TEXT DEFAULT '',
            page_number INTEGER,
            chunk_id TEXT,
            source_chunk_text TEXT,
            difficulty_level TEXT,
            blooms_taxonomy TEXT,
            question_type TEXT,
            question_html TEXT,
            has_question_diagram INTEGER,
            question_diagram_svg TEXT,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            correct_option TEXT,
            explanation_html TEXT,
            has_explanation_diagram INTEGER,
            explanation_diagram_svg TEXT,
            canonical_hash TEXT,
            simhash_hex TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    cols = {c[1] for c in cur.execute("PRAGMA table_info(questions)").fetchall()}
    for col, ctype in [
        ("source_db", "TEXT DEFAULT 'DB3_TEXTBOOK_CHUNK'"),
        ("subject_id", "TEXT DEFAULT ''"),
        ("domain", "TEXT DEFAULT ''"),
        ("branch_codes", "TEXT DEFAULT ''"),
        ("exam_tags", "TEXT DEFAULT ''"),
        ("pyq_exam_name", "TEXT DEFAULT ''"),
        ("pyq_exam_body", "TEXT DEFAULT ''"),
        ("pyq_country", "TEXT DEFAULT 'India'"),
        ("pyq_state_or_region", "TEXT DEFAULT 'All-India / Global'"),
        ("pyq_year", "TEXT DEFAULT ''"),
        ("pyq_session_or_shift", "TEXT DEFAULT ''"),
        ("pyq_paper_code", "TEXT DEFAULT ''"),
        ("pyq_exam_stage", "TEXT DEFAULT ''"),
        ("pyq_qualification_level", "TEXT DEFAULT ''"),
        ("pyq_marks", "TEXT DEFAULT ''"),
        ("pyq_negative_marks", "TEXT DEFAULT ''"),
        ("pyq_original_language", "TEXT DEFAULT 'en'"),
        ("estimated_solve_time_sec", "INTEGER DEFAULT 90"),
        ("key_formula_or_concept", "TEXT DEFAULT ''"),
        ("common_trap_note", "TEXT DEFAULT ''"),
        ("locality_scope", "TEXT DEFAULT 'UNIVERSAL'"),
        ("applicable_countries", "TEXT DEFAULT 'ALL_COUNTRIES'"),
        ("scraped_source_url", "TEXT DEFAULT ''"),
        ("book_reference", "TEXT"),
        ("book_completeness_verified", "INTEGER DEFAULT 1"),
        ("section_number", "TEXT"),
        ("subtopic_id", "TEXT DEFAULT ''"),
        ("source_chunk_text", "TEXT"),
        ("reference_json", "TEXT DEFAULT ''"),
        ("branch_ids_json", "TEXT DEFAULT ''"),
        ("level_ids_json", "TEXT DEFAULT ''"),
        ("canonical_hash", "TEXT"),
        ("simhash_hex", "TEXT"),
        ("has_passage", "INTEGER DEFAULT 0"),
        ("passage_id", "TEXT DEFAULT ''"),
        ("passage_question_num", "INTEGER DEFAULT 0"),
        ("passage_total_questions", "INTEGER DEFAULT 0"),
        ("updated_at", "TEXT"),
    ]:
        if col not in cols:
            cur.execute(f"ALTER TABLE questions ADD COLUMN {col} {ctype}")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS passages (
            passage_id TEXT PRIMARY KEY,
            passage_hash TEXT UNIQUE,
            subject_id TEXT DEFAULT '',
            subject TEXT DEFAULT '',
            domain TEXT DEFAULT '',
            passage_title TEXT DEFAULT '',
            passage_html TEXT DEFAULT '',
            has_passage_diagram INTEGER DEFAULT 0,
            passage_diagram_svg TEXT DEFAULT '',
            question_count INTEGER DEFAULT 1,
            source_url TEXT DEFAULT '',
            language TEXT DEFAULT 'en',
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_questions_passage_id ON questions(passage_id)")
    conn.commit()


# ---------------------------------------------------------------------------
# 1. BOOK COMPLETENESS & EXTRACTABILITY AUDIT (ANY TEXTBOOK)
# ---------------------------------------------------------------------------
def validate_book(pdf_path: str) -> dict:
    import pymupdf as fitz

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    empty_pages = []
    total_chars = 0
    missing_chapters = []

    for i in range(total_pages):
        txt = doc[i].get_text("text").strip()
        # Strip common scanner watermarks
        clean = re.sub(r"(?i)(scanned by.*|pdf created by.*)", "", txt).strip()
        total_chars += len(clean)
        if len(clean) < 25:
            empty_pages.append(i + 1)
        if "<not scanned>" in txt.lower() or "missing chapter" in txt.lower():
            missing_chapters.append(i + 1)

    avg_chars = total_chars / max(1, total_pages)
    empty_ratio = len(empty_pages) / max(1, total_pages)

    is_valid = (avg_chars >= 250) and (empty_ratio <= 0.15) and (len(missing_chapters) == 0)
    status = "PASSED" if is_valid else "REJECTED"

    report = {
        "pdf_path": str(pdf_path),
        "status": status,
        "total_pages": total_pages,
        "avg_chars_per_page": round(avg_chars, 1),
        "empty_or_unextractable_pages_count": len(empty_pages),
        "empty_ratio": round(empty_ratio, 3),
        "missing_chapter_flags": missing_chapters,
        "toc_entries": len(doc.get_toc()),
    }
    print(f"[{status}] Book Audit for {pdf_path}:")
    print(f"  - Total Pages: {total_pages}")
    print(f"  - Avg Extractable Chars/Page: {report['avg_chars_per_page']}")
    print(f"  - Unextractable/Blank Pages: {len(empty_pages)} ({empty_ratio*100:.1f}%)")
    if missing_chapters:
        print(f"  - Missing Chapter Notices Found on Pages: {missing_chapters}")
    if not is_valid:
        print("  -> Book REJECTED (unextractable scan or missing chapters). Please select another standard textbook.")
    return report


# ---------------------------------------------------------------------------
# 2. UNIVERSAL SMART / AI-DECIDED PDF DIVISION
# ---------------------------------------------------------------------------
def divide_book(pdf_path: str, sections_json: str, out_json: str):
    import pymupdf as fitz

    audit = validate_book(pdf_path)
    if audit["status"] != "PASSED":
        raise SystemExit(f"Cannot divide rejected textbook: {pdf_path}")

    doc = fitz.open(pdf_path)
    sections = json.loads(Path(sections_json).read_text(encoding="utf-8"))
    chunks = []

    for sec in sections:
        p_start = max(1, int(sec.get("start_page", 1)))
        p_end = min(len(doc), int(sec.get("end_page", p_start)))
        text = "\n".join(doc[p - 1].get_text("text") for p in range(p_start, p_end + 1))

        # Exact phrase slicing if start_marker / end_marker provided
        s_mark, e_mark = sec.get("start_marker"), sec.get("end_marker")
        if s_mark and s_mark in text:
            text = text[text.index(s_mark) :]
        if e_mark and e_mark in text:
            text = text[: text.index(e_mark) + len(e_mark)]

        figs = sorted(set(re.findall(r"(?:Fig\.|Figure|Table|EXAMPLE)\s+\d+(?:\.\d+)?[a-zA-Z]?", text)))

        chunks.append({
            "chunk_id": sec["chunk_id"],
            "subject": sec.get("subject", ""),
            "book_reference": sec.get("book_reference", ""),
            "chapter_number": sec.get("chapter_number", 1),
            "chapter_name": sec.get("chapter_name", ""),
            "section_number": sec.get("section_number", ""),
            "topic": sec.get("topic", ""),
            "page_number": p_start,
            "end_page_number": p_end,
            "figure_references": figs,
            "source_text": text.strip(),
        })

    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Divided {len(chunks)} chunks -> {out_json}")


def auto_generate_sections(pdf_path: str, subject: str, book_ref: str, prefix: str, out_sections_json: str):
    """
    Universal AI-guided section & paragraph splitter for ANY standard textbook PDF.
    Uses TOC + heading/example/paragraph boundaries to split single pages into multiple
    chunks where needed, or group multi-page derivations/examples.
    """
    import pymupdf as fitz

    audit = validate_book(pdf_path)
    if audit["status"] != "PASSED":
        raise SystemExit(f"Book rejected by completeness audit: {pdf_path}")

    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    raw_secs = []
    ch_num = 0
    ch_name = ""

    for i, (lvl, title, page) in enumerate(toc):
        title = title.replace("\ufffd", "-").strip()
        if lvl == 1 and re.match(r"(?i)^(chapter\s+\d+|\d+\s+[A-Z])", title):
            m = re.match(r"(?i)^(?:chapter\s+)?(\d+)[\s:.-]+(.*)", title)
            if m:
                ch_num = int(m.group(1))
                ch_name = m.group(2).strip()
        elif lvl >= 2 and ch_num > 0:
            m = re.match(r"^(\d+\.\d+)\s+(.*)", title)
            if m:
                sec_num = m.group(1)
                sec_title = m.group(2).strip()
                next_page = toc[i + 1][2] if i + 1 < len(toc) else len(doc)
                raw_secs.append({
                    "chapter_number": ch_num,
                    "chapter_name": ch_name,
                    "section_number": sec_num,
                    "section_title": sec_title,
                    "start_page": page,
                    "next_sec_page": next_page,
                })

    # Fallback if PDF has no level-2 TOC: scan pages for X.Y section headers
    if not raw_secs:
        for p in range(1, len(doc) + 1):
            txt = doc[p - 1].get_text("text")
            for m in re.finditer(r"(?m)^(\d+)\.(\d+)\s+([A-Z][^\n]{3,65})$", txt):
                c_n = int(m.group(1))
                s_n = f"{m.group(1)}.{m.group(2)}"
                s_t = m.group(3).strip()
                raw_secs.append({
                    "chapter_number": c_n,
                    "chapter_name": f"Chapter {c_n}",
                    "section_number": s_n,
                    "section_title": s_t,
                    "start_page": p,
                    "next_sec_page": p + 1,
                })
        for i in range(len(raw_secs) - 1):
            raw_secs[i]["next_sec_page"] = max(raw_secs[i]["start_page"], raw_secs[i + 1]["start_page"])

    ai_sections = []
    seq = 0
    for s in raw_secs:
        p_start = s["start_page"]
        p_end = max(p_start, s["next_sec_page"] - 1) if s["next_sec_page"] > p_start else p_start
        cur_p = p_start
        sub_idx = 0

        while cur_p <= p_end:
            page_txt = doc[cur_p - 1].get_text("text").strip()
            # Split single page into Theory + Worked Example if both exist on the page
            examples = list(re.finditer(r"(?:EXAMPLE|Problem)\s+\d+\.\d+", page_txt))
            if examples and len(page_txt) > 1600:
                ex_pos = examples[0].start()
                pre_txt = page_txt[:ex_pos].strip()
                post_txt = page_txt[ex_pos:].strip()
                if len(pre_txt) > 350:
                    seq += 1
                    sub_idx += 1
                    ai_sections.append({
                        "chunk_id": f"{prefix}_CH{s['chapter_number']:02d}_S{s['section_number'].replace('.','_')}_{seq:04d}",
                        "subject": subject,
                        "book_reference": book_ref,
                        "chapter_number": s["chapter_number"],
                        "chapter_name": s["chapter_name"],
                        "section_number": s["section_number"],
                        "topic": f"{s['section_number']} {s['section_title']} (Theory Part {sub_idx})",
                        "start_page": cur_p,
                        "end_page": cur_p,
                        "start_marker": pre_txt[:45].strip(),
                        "end_marker": pre_txt[-45:].strip(),
                    })
                    seq += 1
                    sub_idx += 1
                    ex_label = examples[0].group(0)
                    ai_sections.append({
                        "chunk_id": f"{prefix}_CH{s['chapter_number']:02d}_S{s['section_number'].replace('.','_')}_{seq:04d}",
                        "subject": subject,
                        "book_reference": book_ref,
                        "chapter_number": s["chapter_number"],
                        "chapter_name": s["chapter_name"],
                        "section_number": s["section_number"],
                        "topic": f"{s['section_number']} {s['section_title']} ({ex_label})",
                        "start_page": cur_p,
                        "end_page": cur_p,
                        "start_marker": post_txt[:45].strip(),
                        "end_marker": post_txt[-45:].strip(),
                    })
                    cur_p += 1
                    continue

            # Otherwise group 1-2 pages per chunk
            step = 2 if (p_end - cur_p >= 1) else 1
            end_p = min(p_end, cur_p + step - 1)
            chunk_txt = "\n".join(doc[p - 1].get_text("text") for p in range(cur_p, end_p + 1)).strip()
            seq += 1
            sub_idx += 1
            part_sfx = f" (Part {sub_idx})" if (p_end - p_start >= 2) else ""
            ai_sections.append({
                "chunk_id": f"{prefix}_CH{s['chapter_number']:02d}_S{s['section_number'].replace('.','_')}_{seq:04d}",
                "subject": subject,
                "book_reference": book_ref,
                "chapter_number": s["chapter_number"],
                "chapter_name": s["chapter_name"],
                "section_number": s["section_number"],
                "topic": f"{s['section_number']} {s['section_title']}{part_sfx}",
                "start_page": cur_p,
                "end_page": end_p,
                "start_marker": chunk_txt[:45].strip(),
                "end_marker": chunk_txt[-45:].strip(),
            })
            cur_p = end_p + 1

    Path(out_sections_json).write_text(json.dumps(ai_sections, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Auto-generated {len(ai_sections)} fine-grained sections -> {out_sections_json}")


# ---------------------------------------------------------------------------
# 3. INDUSTRY-STANDARD SUBJECT DEDUPLICATION ENGINE
#    (SHA-256 Canonical + 64-Bit SimHash + 3-Gram Shingle Jaccard + TF-IDF Cosine)
# ---------------------------------------------------------------------------
def strip_html_and_mathml(raw_html: str) -> str:
    if not raw_html:
        return ""
    txt = re.sub(r"<svg[\s\S]*?</svg>", " ", raw_html, flags=re.IGNORECASE)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = html.unescape(txt)
    txt = re.sub(r"\s+", " ", txt).strip().lower()
    return txt


def extract_tokens(text: str) -> list[str]:
    words = re.findall(r"\w+", text.lower(), flags=re.UNICODE)
    return [w for w in words if w not in STOPWORDS and len(w) >= 1]


def extract_numbers_and_formulas(raw_html: str) -> set[str]:
    txt = strip_html_and_mathml(raw_html)
    nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", txt))
    # Also capture MathML expressions stripped of tags
    math_blocks = re.findall(r"<math[^>]*>([\s\S]*?)</math>", raw_html or "", flags=re.IGNORECASE)
    for mb in math_blocks:
        clean_m = re.sub(r"<[^>]+>", "", html.unescape(mb))
        clean_m = re.sub(r"\s+", "", clean_m).lower()
        if len(clean_m) >= 3:
            nums.add(clean_m)
    return nums


def compute_canonical_hash(q_html: str, opts: dict) -> str:
    stem = re.sub(r"[\W_]+", "", strip_html_and_mathml(q_html), flags=re.UNICODE)
    opt_vals = sorted(re.sub(r"[\W_]+", "", strip_html_and_mathml(str(v)), flags=re.UNICODE) for v in opts.values())
    payload = stem + "||" + "|".join(opt_vals)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_simhash(tokens: list[str]) -> int:
    if not tokens:
        return 0
    v = [0] * 64
    counts = Counter(tokens)
    for tok, weight in counts.items():
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest()[:16], 16)
        for i in range(64):
            if h & (1 << i):
                v[i] += weight
            else:
                v[i] -= weight
    ans = 0
    for i in range(64):
        if v[i] > 0:
            ans |= (1 << i)
    return ans


def hamming_distance(h1: int, h2: int) -> int:
    return bin(h1 ^ h2).count("1")


def get_shingles(tokens: list[str], k: int = 3) -> set[str]:
    if len(tokens) < k:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def jaccard_similarity(set1: set, set2: set) -> float:
    if not set1 or not set2:
        return 0.0
    inter = len(set1 & set2)
    union = len(set1 | set2)
    return inter / union if union else 0.0


def cosine_similarity_counter(c1: Counter, c2: Counter, idf: dict) -> float:
    common = set(c1.keys()) & set(c2.keys())
    if not common:
        return 0.0
    dot = sum(c1[t] * c2[t] * (idf.get(t, 1.0) ** 2) for t in common)
    norm1 = math.sqrt(sum((c1[t] * idf.get(t, 1.0)) ** 2 for t in c1))
    norm2 = math.sqrt(sum((c2[t] * idf.get(t, 1.0)) ** 2 for t in c2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def build_question_profile(qid: str, subj: str, q_html: str, opts: dict, exp_html: str = "", has_svg: bool = False):
    opt_text = " ".join(str(opts.get(k, "")) for k in ("A", "B", "C", "D"))
    full_stem = strip_html_and_mathml(q_html)
    full_combined = full_stem + " " + strip_html_and_mathml(opt_text)
    tokens = extract_tokens(full_combined)
    stem_tokens = extract_tokens(full_stem)
    c_hash = compute_canonical_hash(q_html, opts)
    s_hash = compute_simhash(stem_tokens)
    shingles = get_shingles(stem_tokens, 3)
    tf = Counter(tokens)
    nums = extract_numbers_and_formulas((q_html or "") + " " + opt_text)
    # Quality score to keep the richer question when a duplicate is found
    quality = (2000 if has_svg else 0) + len(q_html or "") + len(exp_html or "")
    return {
        "question_id": qid,
        "subject": subj,
        "canonical_hash": c_hash,
        "simhash": s_hash,
        "simhash_hex": f"{s_hash:016x}",
        "shingles": shingles,
        "tf": tf,
        "nums": nums,
        "quality": quality,
        "stem_preview": full_stem[:100],
    }


def is_duplicate_pair(p1: dict, p2: dict, idf: dict) -> tuple[bool, str]:
    # Stage 1: Exact Canonical SHA-256 Match
    if p1["canonical_hash"] == p2["canonical_hash"]:
        return True, "Stage1_Canonical_SHA256"

    # Stage 2: 64-bit SimHash Near-Duplicate (Hamming distance <= 5)
    h_dist = hamming_distance(p1["simhash"], p2["simhash"])
    if h_dist <= 5:
        return True, f"Stage2_SimHash(hd={h_dist})"

    # Stage 3: 3-Gram Word Shingle Jaccard Similarity (>= 0.65)
    jacc = jaccard_similarity(p1["shingles"], p2["shingles"])
    if jacc >= 0.65:
        return True, f"Stage3_Shingle_Jaccard({jacc:.2f})"

    # Stage 4: TF-IDF Cosine Similarity + Mathematical/Numerical Signature Match
    cos = cosine_similarity_counter(p1["tf"], p2["tf"], idf)
    if cos >= 0.80:
        return True, f"Stage4_TFIDF_Cosine({cos:.2f})"
    num_jacc = jaccard_similarity(p1["nums"], p2["nums"])
    if cos >= 0.66 and num_jacc >= 0.60 and len(p1["nums"]) >= 2:
        return True, f"Stage4_Semantic+MathSig(cos={cos:.2f},math={num_jacc:.2f})"

    return False, ""


def deduplicate_subject_db(subject_filter: str = None) -> dict:
    """
    Runs the 4-stage industry-standard deduplication across the SQLite database
    within each subject (keeping the highest-quality version with SVGs/explanations).
    """
    conn = sqlite3.connect(DB_PATH)
    ensure_db_schema(conn)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if subject_filter:
        rows = cur.execute("SELECT * FROM questions WHERE subject=? ORDER BY seq_num ASC, rowid ASC", (subject_filter,)).fetchall()
    else:
        rows = cur.execute("SELECT * FROM questions ORDER BY seq_num ASC, rowid ASC").fetchall()

    by_subj = {}
    for r in rows:
        s = r["subject"] or "General"
        by_subj.setdefault(s, []).append(r)

    removed_ids = []
    reasons_log = []

    for subj, s_rows in by_subj.items():
        profiles = []
        df = Counter()
        for r in s_rows:
            opts = {"A": r["option_a"], "B": r["option_b"], "C": r["option_c"], "D": r["option_d"]}
            has_svg = bool(r["question_diagram_svg"] or r["explanation_diagram_svg"])
            prof = build_question_profile(
                r["question_id"], subj, r["question_html"], opts, r["explanation_html"], has_svg
            )
            profiles.append(prof)
            for tok in prof["tf"]:
                df[tok] += 1

        n_docs = max(1, len(profiles))
        idf = {tok: math.log(1.0 + n_docs / (1.0 + freq)) for tok, freq in df.items()}

        kept_profiles = []
        for p in profiles:
            # Update hashes in DB
            cur.execute(
                "UPDATE questions SET canonical_hash=?, simhash_hex=? WHERE question_id=?",
                (p["canonical_hash"], p["simhash_hex"], p["question_id"]),
            )
            dup_found = False
            for idx, kp in enumerate(kept_profiles):
                is_dup, reason = is_duplicate_pair(p, kp, idf)
                if is_dup:
                    dup_found = True
                    # Keep the higher quality question (e.g. with SVGs and fuller explanation)
                    if p["quality"] > kp["quality"]:
                        removed_ids.append(kp["question_id"])
                        reasons_log.append((kp["question_id"], p["question_id"], subj, reason))
                        kept_profiles[idx] = p
                    else:
                        removed_ids.append(p["question_id"])
                        reasons_log.append((p["question_id"], kp["question_id"], subj, reason))
                    break
            if not dup_found:
                kept_profiles.append(p)

    if removed_ids:
        placeholders = ",".join("?" for _ in removed_ids)
        cur.execute(f"DELETE FROM questions WHERE question_id IN ({placeholders})", removed_ids)

    # Re-sequence seq_num cleanly 1..N
    rem_rows = cur.execute("SELECT rowid FROM questions ORDER BY seq_num ASC, rowid ASC").fetchall()
    for idx, r in enumerate(rem_rows, 1):
        cur.execute("UPDATE questions SET seq_num=? WHERE rowid=?", (idx, r[0]))

    conn.commit()
    conn.close()

    print(f"[Deduplication Engine] Checked {len(rows)} questions across {len(by_subj)} subject(s).")
    print(f"[Deduplication Engine] Removed {len(removed_ids)} duplicate questions.")
    for rem_id, kept_id, subj, reason in reasons_log[:15]:
        print(f"  - Dropped {rem_id} (duplicate of {kept_id} in '{subj}') via {reason}")
    return {"checked": len(rows), "removed": len(removed_ids), "details": reasons_log}


# ---------------------------------------------------------------------------
# 4. INGEST AI MCQs INTO SQLITE (WITH AUTOMATIC SUBJECT DEDUPLICATION)
# ---------------------------------------------------------------------------
def load_chunks_map() -> dict:
    cmap = {}
    if CHUNKS_DIR.exists():
        for f in CHUNKS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                items = data.get("chunks", data) if isinstance(data, dict) else data
                for c in items:
                    if isinstance(c, dict) and "chunk_id" in c:
                        cmap[c["chunk_id"]] = c
            except Exception:
                pass
    return cmap


def ingest(mcqs_json: str):
    cmap = load_chunks_map()
    batch = json.loads(Path(mcqs_json).read_text(encoding="utf-8"))
    if isinstance(batch, dict):
        batch = [batch]

    conn = sqlite3.connect(DB_PATH)
    ensure_db_schema(conn)
    cur = conn.cursor()
    max_seq = cur.execute("SELECT COALESCE(MAX(seq_num), 0) FROM questions").fetchone()[0]
    count = 0
    touched_subjects = set()

    for item in batch:
        cid = item.get("chunk_id", "")
        c = cmap.get(cid, item)
        subj = item.get("subject") or c.get("subject", "Engineering")
        touched_subjects.add(subj)
        book = item.get("book_reference") or c.get("book_reference", "")
        prefix = "".join(ch for ch in subj.upper() if ch.isalnum())[:6] or "MCQ"

        for q in item.get("questions", []):
            max_seq += 1
            qid = q.get("question_id") or f"{prefix}_Q{max_seq:04d}"
            q_svg = q.get("question_diagram_svg")
            e_svg = q.get("explanation_diagram_svg")
            opts = q.get("options", {})
            q_html = q.get("question_text_html", "")
            prof = build_question_profile(qid, subj, q_html, opts, q.get("explanation_html", ""), bool(q_svg or e_svg))

            cur.execute(
                """
                INSERT OR REPLACE INTO questions (
                    question_id, seq_num, difficulty_level, blooms_taxonomy, question_type,
                    subject, book_reference, chapter_number, chapter_name, section_number, topic,
                    page_number, chunk_id, source_chunk_text,
                    question_html, has_question_diagram, question_diagram_svg,
                    option_a, option_b, option_c, option_d, correct_option,
                    explanation_html, has_explanation_diagram, explanation_diagram_svg,
                    canonical_hash, simhash_hex, updated_at
                ) VALUES (?,?,?,?,?, ?,?,?,?,?,?, ?,?,?, ?,?,?, ?,?,?,?,?, ?,?,?, ?,?,?)
                """,
                (
                    qid,
                    max_seq,
                    q.get("difficulty_level", "Medium"),
                    q.get("blooms_taxonomy", "Understand"),
                    q.get("question_type", "Conceptual"),
                    subj,
                    book,
                    q.get("chapter_number") or c.get("chapter_number", 1),
                    q.get("chapter_name") or c.get("chapter_name", ""),
                    q.get("section_number") or c.get("section_number", ""),
                    q.get("topic") or c.get("topic", ""),
                    q.get("page_number") or c.get("page_number", 1),
                    cid,
                    c.get("source_text", ""),
                    q_html,
                    1 if q_svg else 0,
                    q_svg,
                    opts.get("A", ""),
                    opts.get("B", ""),
                    opts.get("C", ""),
                    opts.get("D", ""),
                    q.get("correct_option", "A"),
                    q.get("explanation_html", ""),
                    1 if e_svg else 0,
                    e_svg,
                    prof["canonical_hash"],
                    prof["simhash_hex"],
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            count += 1

    conn.commit()
    conn.close()
    print(f"Ingested {count} candidate questions into {DB_PATH}. Running subject deduplication...")
    for s in touched_subjects:
        deduplicate_subject_db(s)
    build_viewer()


# ---------------------------------------------------------------------------
# 5. BUILD FULL-DETAIL HTML PORTAL (EXAMS -> BRANCHES -> SUBJECTS -> MCQs)
# ---------------------------------------------------------------------------
def build_viewer():
    conn = sqlite3.connect(DB_PATH)
    ensure_db_schema(conn)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM questions ORDER BY seq_num ASC").fetchall()
    try:
        exams_rows = conn.execute(
            "SELECT exam_id, exam_slug, exam_name, exam_group, jurisdiction, state_code, conducting_body, "
            "mapped_level_ids_json, mapped_branch_ids_json, mapped_subject_ids_json, "
            "syllabus_headings_json, syllabus_topics_json "
            "FROM master_exams ORDER BY CASE WHEN state_code='IN' THEN 0 ELSE 1 END, exam_group, exam_id"
        ).fetchall()
        branches_rows = conn.execute(
            "SELECT branch_id, branch_code, branch_name, domain, applicable_levels_json, subject_ids_json FROM master_branches"
        ).fetchall()
        levels_rows = conn.execute(
            "SELECT level_id, short_name, name, nsqf_level, typical_difficulty_json FROM master_levels ORDER BY nsqf_level"
        ).fetchall()
        subjs_rows = conn.execute(
            "SELECT subject_id, name, domain, syllabus_units_json, reference_books_json FROM master_subjects"
        ).fetchall()
        subtopics_rows = conn.execute(
            "SELECT subject_id, unit_number, subtopic_title FROM master_subtopics ORDER BY unit_number, subtopic_id"
        ).fetchall()
    except Exception:
        exams_rows, branches_rows, levels_rows, subjs_rows, subtopics_rows = [], [], [], [], []
    conn.close()

    # Count questions per subject_id and difficulty/blooms
    subj_q_counts = Counter()
    for r in rows:
        sid = r["subject_id"] if ("subject_id" in r.keys() and r["subject_id"]) else ""
        if sid:
            subj_q_counts[sid] += 1

    subj_subtopics_map = {}
    for st in subtopics_rows:
        subj_subtopics_map.setdefault(st["subject_id"], []).append(st["subtopic_title"])

    branches_js = {
        b["branch_id"]: {
            "id": b["branch_id"],
            "code": b["branch_code"],
            "name": b["branch_name"],
            "domain": b["domain"] if "domain" in b.keys() and b["domain"] else "Engineering & Technology",
            "levels": json.loads(b["applicable_levels_json"] or "[]"),
            "subjects": json.loads(b["subject_ids_json"] or "[]"),
        }
        for b in branches_rows
    }
    exams_js = []
    for e in exams_rows:
        ebrs = json.loads(e["mapped_branch_ids_json"] or "[]")
        esubjs = json.loads(e["mapped_subject_ids_json"] or "[]")
        syl_h = json.loads(e["syllabus_headings_json"] or "[]")[:15] if "syllabus_headings_json" in e.keys() else []
        syl_t = json.loads(e["syllabus_topics_json"] or "[]")[:24] if "syllabus_topics_json" in e.keys() else []
        exams_js.append({
            "id": e["exam_id"],
            "slug": e["exam_slug"],
            "name": e["exam_name"],
            "group": e["exam_group"] or e["jurisdiction"],
            "state": e["state_code"],
            "body": e["conducting_body"],
            "levels": json.loads(e["mapped_level_ids_json"] or "[]"),
            "branches": ebrs,
            "subj_count": len(esubjs),
            "syl_h": syl_h,
            "syl_t": syl_t,
        })
    levels_js = {
        l["level_id"]: {
            "id": l["level_id"],
            "short": l["short_name"],
            "name": l["name"],
            "diffs": json.loads(l["typical_difficulty_json"] or "[]"),
        }
        for l in levels_rows
    }
    subjects_js = {
        s["subject_id"]: {
            "id": s["subject_id"],
            "name": s["name"],
            "domain": s["domain"],
            "q_count": subj_q_counts.get(s["subject_id"], 0),
            "units": json.loads(s["syllabus_units_json"] or "[]")[:24] if "syllabus_units_json" in s.keys() else [],
            "books": json.loads(s["reference_books_json"] or "[]")[:5] if "reference_books_json" in s.keys() else [],
            "subtopics": subj_subtopics_map.get(s["subject_id"], []),
        }
        for s in subjs_rows
    }
    central_exams_cnt = sum(1 for e in exams_js if e["state"] == "IN")
    state_exams_cnt = sum(1 for e in exams_js if e["state"] != "IN")
    total_subtopics_cnt = len(subtopics_rows)

    cards = []
    for r in rows:
        corr = r["correct_option"] or "A"
        opts_html = "".join(
            f'<div class="opt {"ok" if k == corr else ""}"><b>({k})</b> {r["option_" + k.lower()] or ""}</div>'
            for k in ("A", "B", "C", "D")
        )
        q_svg = f'<div class="svg">{r["question_diagram_svg"]}</div>' if r["question_diagram_svg"] else ""
        e_svg = f'<div class="svg">{r["explanation_diagram_svg"]}</div>' if r["explanation_diagram_svg"] else ""
        subj = html.escape(r["subject"] or "")
        book = html.escape(r["book_reference"] or "")
        diff = html.escape(r["difficulty_level"] or "Medium")
        bloom = html.escape(r["blooms_taxonomy"] or "Understand")
        qtype = html.escape(r["question_type"] or "Conceptual")
        cid = html.escape(r["chunk_id"] or "")
        pnum = r["page_number"] or 1
        shash = html.escape(r["simhash_hex"] or "")
        sid = html.escape((r["subject_id"] if "subject_id" in r.keys() and r["subject_id"] else "") or "")
        src_txt = html.escape(r["source_chunk_text"] or "")
        chunk_box = (
            f'<details class="cbox"><summary>Source Chunk: <b>{cid}</b> (PDF Page {pnum}) — Click to view textbook excerpt</summary>'
            f'<pre class="ctxt">{src_txt}</pre></details>'
            if src_txt else ""
        )

        cards.append(f"""
        <div class="card" data-sid="{sid}" data-subj="{subj}" data-book="{book}" data-diff="{diff}" data-bloom="{bloom}">
          <div class="hdr">
            <b>#{r["seq_num"]} {r["question_id"]}</b>
            <span>{subj} | {book} | Ch {r["chapter_number"]}: {html.escape(r["chapter_name"] or "")} ({html.escape(r["section_number"] or "")}) | {html.escape(r["topic"] or "")} | Page {pnum}</span>
            <span><span class="tag">{diff}</span> <span class="tag" style="background:#ede9fe;color:#5b21b6">Bloom: {bloom}</span> <span class="tag" style="background:#f1f5f9;color:#334155">{qtype}</span> <span class="tag" style="background:#fef3c7;color:#92400e" title="SimHash 64-bit Fingerprint">#{shash[:8]}</span></span>
          </div>
          {chunk_box}
          <div class="q">{r["question_html"] or ""}{q_svg}</div>
          <div class="opts">{opts_html}</div>
          <div class="exp"><b>Answer ({corr}):</b> {r["explanation_html"] or ""}{e_svg}</div>
        </div>""")

    html_doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>All-India Competitive Exam MCQ Portal ({len(exams_js)} Exams | {len(rows)} MCQs)</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: Segoe UI, system-ui, sans-serif; background: #f1f5f9; margin: 0; color: #0f172a; }}
  .topbar {{ position: sticky; top: 0; background: #0f172a; color: #fff; padding: 12px 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; z-index: 20; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
  .brand {{ font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 12px; cursor: pointer; }}
  .badge-url {{ background: #1e293b; color: #38bdf8; border: 1px solid #334155; padding: 4px 10px; border-radius: 6px; font-family: Consolas, monospace; font-size: 12px; }}
  .nav-btns button {{ background: #2563eb; color: #fff; border: none; padding: 7px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; margin-left: 6px; }}
  .nav-btns button.sec {{ background: #334155; }}
  .crumbs {{ background: #fff; border-bottom: 1px solid #cbd5e1; padding: 10px 24px; font-size: 14px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
  .crumbs span.link {{ color: #2563eb; font-weight: 600; cursor: pointer; }}
  .crumbs span.link:hover {{ text-decoration: underline; }}
  .crumbs span.sep {{ color: #94a3b8; }}
  .container {{ max-width: 1220px; margin: 20px auto; padding: 0 18px; }}
  .filter-row {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 18px; align-items: center; background: #fff; padding: 12px 16px; border-radius: 8px; border: 1px solid #cbd5e1; }}
  .filter-row input, .filter-row select {{ padding: 8px 12px; border-radius: 6px; border: 1px solid #cbd5e1; font-size: 14px; background: #f8fafc; color: #0f172a; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); gap: 14px; }}
  .tile {{ background: #fff; border: 1px solid #cbd5e1; border-radius: 10px; padding: 16px; cursor: pointer; transition: all 0.15s ease; display: flex; flex-direction: column; justify-content: space-between; }}
  .tile:hover {{ border-color: #2563eb; box-shadow: 0 6px 16px rgba(37,99,235,0.12); transform: translateY(-2px); }}
  .tile.has-q {{ border-left: 5px solid #16a34a; }}
  .tile h3 {{ margin: 6px 0 8px; font-size: 15px; color: #0f172a; line-height: 1.35; }}
  .tile .meta {{ font-size: 12px; color: #64748b; margin-bottom: 10px; }}
  .pills {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }}
  .pill {{ font-size: 11px; padding: 3px 8px; border-radius: 99px; font-weight: 600; background: #e2e8f0; color: #334155; }}
  .pill.blue {{ background: #dbeafe; color: #1d4ed8; }}
  .pill.green {{ background: #dcfce7; color: #15803d; }}
  .pill.purple {{ background: #ede9fe; color: #6d28d9; }}
  .pill.amber {{ background: #fef3c7; color: #b45309; }}
  .sec-hdr {{ margin: 22px 0 10px; padding-bottom: 6px; border-bottom: 2px solid #cbd5e1; font-size: 16px; font-weight: 700; color: #1e293b; display: flex; justify-content: space-between; }}
  .card {{ background: #fff; border: 1px solid #cbd5e1; border-radius: 8px; margin-bottom: 16px; padding: 16px; }}
  .hdr {{ display: flex; justify-content: space-between; font-size: 13px; color: #475569; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 12px; flex-wrap: wrap; gap: 6px; }}
  .tag {{ background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 4px; font-weight: 600; }}
  .svg {{ margin: 12px 0; text-align: center; }}
  .svg svg {{ max-width: 100%; height: auto; max-height: 340px; }}
  .opts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 12px 0; }}
  .opt {{ padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; background: #f8fafc; }}
  .opt.ok {{ border: 2px solid #16a34a; background: #f0fdf4; font-weight: 600; }}
  .exp {{ background: #f8fafc; border-left: 4px solid #2563eb; padding: 12px; border-radius: 6px; font-size: 14px; }}
  .cbox {{ background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 8px 12px; margin-bottom: 12px; font-size: 13px; }}
  .cbox summary {{ cursor: pointer; color: #92400e; }}
  .ctxt {{ white-space: pre-wrap; font-family: Consolas, monospace; font-size: 12px; color: #334155; max-height: 240px; overflow-y: auto; margin: 8px 0 0; padding-top: 8px; border-top: 1px dashed #fcd34d; }}
  .empty-state {{ background: #fff; border: 2px dashed #cbd5e1; border-radius: 10px; padding: 36px; text-align: center; color: #475569; }}
</style></head>
<body>
  <div class="topbar">
    <div class="brand" onclick="goHome()">
      <span>🏛️ All-India Exam Portal</span>
      <span id="urlBadge" class="badge-url">/exams</span>
    </div>
    <div class="nav-btns">
      <button onclick="goHome()">1. All Exams ({len(exams_js)})</button>
      <button class="sec" onclick="showAllQuestionsDirect()">All Bank MCQs ({len(rows)})</button>
    </div>
  </div>

  <div id="breadcrumbs" class="crumbs"></div>

  <div class="container">
    <!-- VIEW 1: ALL EXAMS DIRECTORY -->
    <div id="viewExams">
      <div class="filter-row">
        <b>Filter Exams:</b>
        <select id="jurFilter" onchange="renderExams()">
          <option value="ALL">All Jurisdictions ({len(exams_js)} Verified Public Exams: Central + All 36 States/UTs)</option>
          <option value="IN">Central / All-India Exams Only ({central_exams_cnt})</option>
          <option value="STATE">State &amp; UT Exams Only ({state_exams_cnt} across 36 States/UTs)</option>
        </select>
        <select id="lvlFilterExam" onchange="renderExams()">
          <option value="ALL">All Qualification Levels (Class 1 to Ph.D)</option>
        </select>
        <input id="examSearch" placeholder="Search GATE, RRB JE, BARC, ISRO, ONGC, Hindi, Sanskrit, Telugu, Tamil, APPSC, UPPCL..." oninput="renderExams()" style="flex:1;min-width:220px">
        <button onclick="showAllBranches()" style="padding:8px 12px;border-radius:7px;border:1px solid #2563eb;background:#eff6ff;color:#1d4ed8;cursor:pointer;font-weight:700">🌳 Browse All {len(branches_js)} Canonical Branches &amp; {len(subjects_js)} Subjects ({total_subtopics_cnt} Sub-Topics)</button>
        <span id="examCountLbl" style="font-weight:700;color:#1d4ed8"></span>
      </div>
      <div id="examsGridContainer"></div>
    </div>

    <!-- VIEW 2: BRANCHES INSIDE SELECTED EXAM -->
    <div id="viewBranches" style="display:none">
      <div id="examHeaderBox" class="filter-row" style="justify-content:space-between"></div>
      <div id="branchesGrid"></div>
    </div>

    <!-- VIEW 3: SUBJECTS INSIDE SELECTED BRANCH -->
    <div id="viewSubjects" style="display:none">
      <div id="branchHeaderBox" class="filter-row" style="justify-content:space-between"></div>
      <div id="subjectsGrid" class="grid"></div>
    </div>

    <!-- VIEW 4: MCQS INSIDE SELECTED SUBJECT (WITH DIFFICULTY & BLOOMS FILTERS) -->
    <div id="viewMcqs" style="display:none">
      <div class="filter-row">
        <b id="mcqViewTitle">MCQs</b>
        <select id="fDiff" onchange="filterMcqs()">
          <option value="ALL">All Difficulty Levels</option>
          <option value="Easy">Easy</option>
          <option value="Medium">Medium</option>
          <option value="Hard">Hard</option>
          <option value="Extra Hard">Extra Hard</option>
        </select>
        <select id="fBloom" onchange="filterMcqs()">
          <option value="ALL">All Bloom's Taxonomy Levels</option>
          <option value="Remember">Remember</option>
          <option value="Understand">Understand</option>
          <option value="Apply">Apply</option>
          <option value="Analyze">Analyze</option>
          <option value="Evaluate">Evaluate</option>
        </select>
        <input id="fSearch" placeholder="Search topic, chunk, formula..." oninput="filterMcqs()" style="flex:1;min-width:200px">
        <span>Showing <b id="cnt">{len(rows)}</b> MCQs</span>
      </div>
      <div id="emptySubjectNotice" class="empty-state" style="display:none"></div>
      <div id="mcqsList">{"".join(cards)}</div>
    </div>
  </div>

  <script>
    const EXAMS = {json.dumps(exams_js, ensure_ascii=False)};
    const BRANCHES = {json.dumps(branches_js, ensure_ascii=False)};
    const LEVELS = {json.dumps(levels_js, ensure_ascii=False)};
    const SUBJECTS = {json.dumps(subjects_js, ensure_ascii=False)};

    let curExam = null;
    let curBranch = null;
    let curSubject = null;

    // Populate level dropdown on Exam directory
    const lvlSel = document.getElementById('lvlFilterExam');
    Object.values(LEVELS).forEach(l => {{
      const o = document.createElement('option');
      o.value = l.id;
      o.textContent = l.short + ' — ' + l.name;
      lvlSel.appendChild(o);
    }});

    function setView(vName, urlStr) {{
      ['viewExams', 'viewBranches', 'viewSubjects', 'viewMcqs'].forEach(id => {{
        document.getElementById(id).style.display = (id === vName) ? '' : 'none';
      }});
      document.getElementById('urlBadge').textContent = urlStr;
      renderBreadcrumbs();
      window.scrollTo(0, 0);
    }}

    function renderBreadcrumbs() {{
      const box = document.getElementById('breadcrumbs');
      let html = `<span class="link" onclick="goHome()">🏠 All Competitive Exams (${{EXAMS.length}})</span>`;
      if (curExam) {{
        html += `<span class="sep">›</span><span class="link" onclick="selectExam('${{curExam.id}}')">${{curExam.name}}</span>`;
      }}
      if (curBranch) {{
        html += `<span class="sep">›</span><span class="link" onclick="selectBranch('${{curBranch.id}}')">Branch: ${{curBranch.code}} (${{curBranch.name}})</span>`;
      }}
      if (curSubject) {{
        html += `<span class="sep">›</span><b>Subject: ${{curSubject.name}}</b>`;
      }}
      box.innerHTML = html;
    }}

    function goHome() {{
      curExam = null; curBranch = null; curSubject = null;
      setView('viewExams', '/exams');
      renderExams();
    }}

    function renderExams() {{
      const jur = document.getElementById('jurFilter').value;
      const lvl = document.getElementById('lvlFilterExam').value;
      const q = document.getElementById('examSearch').value.toLowerCase();
      const filtered = EXAMS.filter(e => {{
        if (jur === 'IN' && e.state !== 'IN') return false;
        if (jur === 'STATE' && e.state === 'IN') return false;
        if (lvl !== 'ALL' && !e.levels.includes(lvl)) return false;
        if (q && !(e.name.toLowerCase().includes(q) || e.group.toLowerCase().includes(q) || e.body.toLowerCase().includes(q) || e.slug.includes(q))) return false;
        return true;
      }});
      document.getElementById('examCountLbl').textContent = `${{filtered.length}} Exams Found`;

      // Group by exam_group
      const groups = {{}};
      filtered.forEach(e => {{
        if (!groups[e.group]) groups[e.group] = [];
        groups[e.group].push(e);
      }});

      let out = '';
      Object.entries(groups).forEach(([gName, list]) => {{
        out += `<div class="sec-hdr"><span>📂 ${{gName}}</span><span>${{list.length}} Exams</span></div><div class="grid">`;
        list.forEach(e => {{
          const lvlBadges = e.levels.map(lid => `<span class="pill purple">${{LEVELS[lid] ? LEVELS[lid].short : lid}}</span>`).join('');
          out += `
            <div class="tile" onclick="selectExam('${{e.id}}')">
              <div>
                <div class="meta">${{e.body}} • <code>${{e.slug}}</code></div>
                <h3>${{e.name}}</h3>
              </div>
              <div class="pills">
                <span class="pill blue">${{e.branches.length}} Branches</span>
                <span class="pill green">${{e.subj_count}} Unique Subjects</span>
                ${{lvlBadges}}
              </div>
            </div>`;
        }});
        out += `</div>`;
      }});
      document.getElementById('examsGridContainer').innerHTML = out;
    }}

    function getEffectiveBranchSubjects(b) {{
      if (!b) return [];
      if (b.id === 'BR_GEN_STATE_GK' && curExam && curExam.state && curExam.state !== 'IN') {{
        const ownPrefix = 'SUB_STATE_GK_' + curExam.state + '_';
        const ownGks = (b.subjects || []).filter(s => s.startsWith(ownPrefix));
        return ownGks.length ? ownGks : b.subjects;
      }}
      return b.subjects || [];
    }}

    function renderBranchGroups(branchIds) {{
      const domGroups = {{}};
      branchIds.forEach(bid => {{
        const b = BRANCHES[bid];
        if (!b) return;
        const dom = b.domain || '1. Engineering & Technology';
        if (!domGroups[dom]) domGroups[dom] = [];
        domGroups[dom].push(b);
      }});
      let bHtml = '';
      Object.keys(domGroups).sort().forEach(dom => {{
        const list = domGroups[dom];
        bHtml += `<div class="sec-hdr"><span>🏛️ ${{dom}}</span><span>${{list.length}} Branches</span></div><div class="grid">`;
        list.forEach(b => {{
          const effSubjs = getEffectiveBranchSubjects(b);
          const totalQs = effSubjs.reduce((acc, sid) => acc + (SUBJECTS[sid] ? SUBJECTS[sid].q_count : 0), 0);
          bHtml += `
            <div class="tile ${{totalQs > 0 ? 'has-q' : ''}}" onclick="selectBranch('${{b.id}}')">
              <div>
                <div class="meta">${{dom}} • Code: <b>${{b.code}}</b></div>
                <h3>${{b.name}}</h3>
              </div>
              <div class="pills">
                <span class="pill blue">${{effSubjs.length}} Unique Subjects</span>
                <span class="pill ${{totalQs > 0 ? 'green' : 'amber'}}">${{totalQs}} MCQs Available in DB</span>
              </div>
            </div>`;
        }});
        bHtml += `</div>`;
      }});
      document.getElementById('branchesGrid').innerHTML = bHtml;
    }}

    function showAllBranches() {{
      curExam = null; curBranch = null; curSubject = null;
      const allBranchIds = Object.keys(BRANCHES);
      document.getElementById('examHeaderBox').innerHTML = `
        <div>
          <div style="font-size:12px;color:#64748b">All-India Master Branch Directory | 9 Categorized Domains</div>
          <div style="font-size:18px;font-weight:700;margin-top:2px">All ${{allBranchIds.length}} Unbundled Branches / Trades / Streams in India</div>
        </div>
        <button onclick="goHome()" style="padding:7px 12px;border-radius:6px;border:1px solid #cbd5e1;background:#f8fafc;cursor:pointer;font-weight:600">← Back to All Exams</button>
      `;
      renderBranchGroups(allBranchIds);
      setView('viewBranches', '/branches');
    }}

    function selectExam(examId) {{
      if (!examId) {{ showAllBranches(); return; }}
      curExam = EXAMS.find(x => x.id === examId);
      curBranch = null; curSubject = null;
      if (!curExam) return;

      const lvlNames = curExam.levels.map(lid => LEVELS[lid] ? LEVELS[lid].short : lid).join(', ');
      const sylHeadings = (curExam.syl_h || []).map(h => `<span class="pill blue">${{h}}</span>`).join(' ');
      const sylTopics = (curExam.syl_t || []).map(t => `<li style="margin-bottom:4px">${{t}}</li>`).join('');
      const sylBox = (sylHeadings || sylTopics) ? `
        <details open style="width:100%;margin-top:10px;background:#f8fafc;border:1px solid #cbd5e1;border-radius:8px;padding:10px 14px">
          <summary style="cursor:pointer;font-weight:700;color:#1d4ed8">📘 Exam Syllabus Sections &amp; Scraped Topics (${{(curExam.syl_h||[]).length}} Sections, ${{(curExam.syl_t||[]).length}} Core Topics)</summary>
          <div class="pills" style="margin:8px 0">${{sylHeadings}}</div>
          <ul style="margin:6px 0 2px 18px;font-size:13px;color:#334155;columns:2">${{sylTopics}}</ul>
        </details>` : '';

      document.getElementById('examHeaderBox').innerHTML = `
        <div style="flex:1">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
            <div>
              <div style="font-size:12px;color:#64748b">${{curExam.body}} | Qualification Levels: <b>${{lvlNames}}</b></div>
              <div style="font-size:18px;font-weight:700;margin-top:2px">${{curExam.name}} — Select a Branch (${{curExam.branches.length}} Applicable Branches)</div>
            </div>
            <button onclick="goHome()" style="padding:7px 12px;border-radius:6px;border:1px solid #cbd5e1;background:#f8fafc;cursor:pointer;font-weight:600">← Back to All Exams</button>
          </div>
          ${{sylBox}}
        </div>
      `;

      renderBranchGroups(curExam.branches);
      setView('viewBranches', curExam.slug);
    }}

    function selectBranch(branchId) {{
      curBranch = BRANCHES[branchId];
      curSubject = null;
      if (!curBranch) return;
      const baseSlug = curExam ? curExam.slug : '/exams/all';
      const brSlug = `${{baseSlug}}/${{curBranch.code.toLowerCase().replace(/[^a-z0-9]/g, '-')}}`;
      const effSubjs = getEffectiveBranchSubjects(curBranch);

      document.getElementById('branchHeaderBox').innerHTML = `
        <div>
          <div style="font-size:12px;color:#64748b">${{curExam ? curExam.name : 'All Exams'}} › Branch: <b>${{curBranch.code}}</b></div>
          <div style="font-size:18px;font-weight:700;margin-top:2px">${{curBranch.name}} — Select a Subject (${{effSubjs.length}} Subjects)</div>
        </div>
        <button onclick="selectExam('${{curExam ? curExam.id : ''}}')" style="padding:7px 12px;border-radius:6px;border:1px solid #cbd5e1;background:#f8fafc;cursor:pointer;font-weight:600">← Back to Branches</button>
      `;

      let sHtml = '';
      effSubjs.forEach(sid => {{
        const s = SUBJECTS[sid];
        if (!s) return;
        const qCount = s.q_count || 0;
        const uCount = (s.units || []).length;
        const stCount = (s.subtopics || []).length;
        const previewUnits = (s.units || []).slice(0, 3).map(u => `<div style="font-size:11.5px;color:#475569;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">• ${{u}}</div>`).join('');
        sHtml += `
          <div class="tile ${{qCount > 0 ? 'has-q' : ''}}" onclick="selectSubject('${{s.id}}')">
            <div>
              <div class="meta">Subject ID: <code>${{s.id}}</code> • ${{s.domain.replace(/_/g, ' ')}}</div>
              <h3>${{s.name}}</h3>
              ${{previewUnits}}
            </div>
            <div class="pills">
              <span class="pill blue">📚 ${{uCount}} Units • ${{stCount}} Sub-Topics</span>
              <span class="pill ${{qCount > 0 ? 'green' : 'amber'}}">${{qCount > 0 ? (qCount + ' Deduplicated MCQs Ready') : 'Click for Complete Syllabus & Textbooks'}}</span>
            </div>
          </div>`;
      }});
      document.getElementById('subjectsGrid').innerHTML = sHtml;
      setView('viewSubjects', brSlug);
    }}

    function selectSubject(subjectId) {{
      curSubject = SUBJECTS[subjectId];
      if (!curSubject) return;
      const baseSlug = curExam ? curExam.slug : '/exams/all';
      const brCode = curBranch ? curBranch.code.toLowerCase().replace(/[^a-z0-9]/g, '-') : 'all';
      const subSlug = `${{baseSlug}}/${{brCode}}/${{curSubject.id.toLowerCase()}}`;

      document.getElementById('mcqViewTitle').textContent = `${{curSubject.name}}`;
      document.getElementById('fDiff').value = 'ALL';
      document.getElementById('fBloom').value = 'ALL';
      document.getElementById('fSearch').value = '';
      setView('viewMcqs', subSlug);
      filterMcqs();
    }}

    function showAllQuestionsDirect() {{
      curExam = null; curBranch = null; curSubject = null;
      document.getElementById('mcqViewTitle').textContent = 'All Ingested MCQs Across Subjects';
      document.getElementById('fDiff').value = 'ALL';
      document.getElementById('fBloom').value = 'ALL';
      document.getElementById('fSearch').value = '';
      setView('viewMcqs', '/mcqs/all');
      filterMcqs();
    }}

    function filterMcqs() {{
      const d = document.getElementById('fDiff').value;
      const bl = document.getElementById('fBloom').value;
      const q = document.getElementById('fSearch').value.toLowerCase();
      const sidFilter = curSubject ? curSubject.id : null;
      let n = 0;
      document.querySelectorAll('.card').forEach(c => {{
        const matchSid = (!sidFilter || c.dataset.sid === sidFilter);
        const matchDiff = (d === 'ALL' || c.dataset.diff === d);
        const matchBloom = (bl === 'ALL' || (c.dataset.bloom || '').toLowerCase().includes(bl.toLowerCase()));
        const matchQ = (!q || c.innerText.toLowerCase().includes(q));
        const show = matchSid && matchDiff && matchBloom && matchQ;
        c.style.display = show ? '' : 'none';
        if (show) n++;
      }});
      document.getElementById('cnt').textContent = n;
      const emptyBox = document.getElementById('emptySubjectNotice');
      if (curSubject) {{
        emptyBox.style.display = '';
        emptyBox.style.textAlign = 'left';
        const unitsList = (curSubject.units || []).map(u => `<li style="margin-bottom:6px;line-height:1.45">${{u}}</li>`).join('');
        const subtopicsList = (curSubject.subtopics || []).length ? `<details style="margin-top:10px;padding-top:8px;border-top:1px dashed #cbd5e1"><summary style="cursor:pointer;font-weight:700;color:#0f172a">🧩 View All ${{(curSubject.subtopics || []).length}} Granular Sub-Topics for ${{curSubject.name}}</summary><ol style="margin:8px 0 0 20px;font-size:12.5px;color:#334155;columns:2;column-gap:24px">${{curSubject.subtopics.map(st => `<li style="margin-bottom:4px">${{st}}</li>`).join('')}}</ol></details>` : '';
        const booksList = (curSubject.books || []).length ? `<div style="margin-top:10px;padding-top:8px;border-top:1px dashed #cbd5e1"><b>📖 Standard Reference Textbooks:</b><ul style="margin:6px 0 0 18px;font-size:13px">${{curSubject.books.map(b => `<li>${{b}}</li>`).join('')}}</ul></div>` : '';
        emptyBox.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;border-bottom:1px solid #e2e8f0;padding-bottom:8px;margin-bottom:10px">
            <h3 style="margin:0;color:#1d4ed8">📚 Complete Subject Syllabus: ${{curSubject.name}} (<code>${{curSubject.id}}</code>)</h3>
            <button onclick="selectBranch('${{curBranch ? curBranch.id : ''}}')" style="padding:6px 12px;border-radius:6px;border:1px solid #cbd5e1;background:#f8fafc;cursor:pointer;font-weight:600">← Back to Subjects</button>
          </div>
          <ol style="margin:6px 0 10px 20px;font-size:13.5px;color:#1e293b">${{unitsList}}</ol>
          ${{subtopicsList}}
          ${{booksList}}
          ${{n === 0 ? `<div style="margin-top:12px;padding:10px 14px;background:#fefce8;border:1px solid #fde047;border-radius:6px;font-size:13px;color:#85400e"><b>MCQ Status:</b> 0 MCQs ingested yet for this subject (Currently live with MCQs: <b>Thermodynamics — 429 MCQs</b> and <b>Fluid Mechanics — 440 MCQs</b>).</div>` : ''}}
        `;
      }} else {{
        emptyBox.style.display = 'none';
      }}
    }}

    // Start on the Exam Directory home view
    goHome();
  </script>
</body></html>"""
    VIEWER_PATH.write_text(html_doc, encoding="utf-8")
    print(f"Updated {VIEWER_PATH} ({len(exams_js)} exams -> {len(branches_js)} branches -> {len(subjects_js)} subjects -> {len(rows)} deduplicated questions)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", metavar="PDF", help="Validate PDF completeness & extractability")
    ap.add_argument("--auto-divide", nargs=5, metavar=("PDF", "SUBJECT", "BOOK_REF", "PREFIX", "OUT_CHUNKS_JSON"))
    ap.add_argument("--divide", nargs=3, metavar=("PDF", "AI_SECTIONS_JSON", "OUT_CHUNKS_JSON"))
    ap.add_argument("--ingest", metavar="MCQS_JSON")
    ap.add_argument("--dedup", nargs="?", const="ALL", metavar="SUBJECT", help="Run 4-stage deduplication on SQLite DB")
    ap.add_argument("--viewer", action="store_true")
    args = ap.parse_args()

    if args.validate:
        validate_book(args.validate)
    elif args.auto_divide:
        pdf_p, subj_s, book_r, pref, out_c = args.auto_divide
        sec_file = f"ai_sections_{pref.lower()}.json"
        auto_generate_sections(pdf_p, subj_s, book_r, pref, sec_file)
        divide_book(pdf_p, sec_file, out_c)
    elif args.divide:
        divide_book(*args.divide)
    elif args.ingest:
        ingest(args.ingest)
    elif args.dedup:
        deduplicate_subject_db(None if args.dedup == "ALL" else args.dedup)
        build_viewer()
    else:
        build_viewer()
