# -*- coding: utf-8 -*-
r"""
Universal LaTeX-to-Clean-MathML Converter & Retroactive Database Sanitizer (`mathml_sanitizer.py`)
==================================================================================================
Converts ALL LaTeX math variants into clean, semantic W3C MathML (`<math xmlns="http://www.w3.org/1998/Math/MathML">`):
  1. Previously mis-wrapped `<math...><mrow><mi>\frac{...}...</mi></mrow></math>` blocks
  2. Delimited LaTeX: `$$...$$`, `\[...\]`, `\(...\)`, and `$...$` (while protecting currency like `$50 and $20`)
  3. Bare / undelimited nested-brace LaTeX in stems, options, and explanations (e.g. `\frac{\sqrt{3}}{2}\pi`,
     `\overline{WTY} \cong \overline{TWY}`, `\widehat{\mathrm{WN}}`, `x^{2} + y_{1}`)
  4. Sweeps existing SQLite DBs (`mcq_bank.sqlite`, `db1`, `db2`, `db_staging_queue.sqlite`) in seconds!
"""

import html
import re
import sqlite3
from pathlib import Path

import latex2mathml.converter as l2m

LATEX_CMD_WHITELIST_PREFIX = re.compile(r"\\[a-zA-Z]{1,24}")

# Non-math escape sequences that might appear in plain text
NON_MATH_COMMANDS = {"\\n", "\\r", "\\t", "\\\\", "\\'", '\\"'}

UNICODE_FALLBACK_MAP = {
    r"\AAngstrom": "Å",
    r"\AA": "Å",
    r"\textbullet": "•",
    r"\bullets": "•",
    r"\textcent": "¢",
    r"\textsterling": "£",
    r"\texteuro": "€",
    r"\textyen": "¥",
    r"\textdegree": "°",
    r"\textquotedblright": "”",
    r"\textquotedblleft": "“",
    r"\textquoteright": "’",
    r"\textquoteleft": "‘",
    r"\textasteriskcentered": "*",
    r"\textendash": "–",
    r"\textemdash": "—",
    r"\textminus": "−",
    r"\textpm": "±",
    r"\texttimes": "×",
    r"\textdiv": "÷",
    r"\odot": "⊙",
    r"\angle": "∠",
    r"\triangle": "△",
    r"\cong": "≅",
    r"\sim": "∼",
    r"\approx": "≈",
    r"\neq": "≠",
    r"\leq": "≤",
    r"\le": "≤",
    r"\geq": "≥",
    r"\ge": "≥",
    r"\pm": "±",
    r"\times": "×",
    r"\cdot": "·",
    r"\div": "÷",
    r"\infty": "∞",
    r"\partial": "∂",
    r"\nabla": "∇",
    r"\surd": "√",
    r"\bullet": "•",
    r"\vert": "|",
    r"\pi": "π",
    r"\theta": "θ",
    r"\alpha": "α",
    r"\beta": "β",
    r"\gamma": "γ",
    r"\delta": "δ",
    r"\epsilon": "ε",
    r"\lambda": "λ",
    r"\mu": "μ",
    r"\rho": "ρ",
    r"\sigma": "σ",
    r"\tau": "τ",
    r"\phi": "φ",
    r"\omega": "ω",
    r"\Omega": "Ω",
    r"\Delta": "Δ",
    r"\Sigma": "Σ",
    r"\Gamma": "Γ",
    r"\Lambda": "Λ",
    r"\Theta": "Θ",
    r"\Phi": "Φ",
    r"\Psi": "Ψ",
    r"\rightarrow": "→",
    r"\leftarrow": "←",
    r"\Rightarrow": "⇒",
    r"\circ": "°",
    r"\degree": "°",
}

TEXT_GREEK_RE = re.compile(
    r"\\text(alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega)\b"
)

# OCR-glued macro + variable/unit patterns (e.g. \DeltaH -> \Delta H, \muF -> \mu\mathrm{F}, \omegat -> \omega t)
GLUED_MACRO_RE = re.compile(
    r"\\(Delta|Gamma|Theta|Lambda|Sigma|Phi|Psi|Omega|partial|sum|prod|int|vert|surd|bullet|leq|geq|neq)"
    r"([A-Za-z0-9]+)\b"
)
GLUED_UNIT_GREEK_RE = re.compile(
    r"\\(mu|pi|omega)(F|m|s|g|L|A|V|W|Hz|mol|x|t|r|n|k|i)\b"
)

BROKEN_MI_RE = re.compile(
    r'<math[^>]*>\s*<mrow>\s*<(?:mi|mtext)>([^<]+)</(?:mi|mtext)>\s*</mrow>\s*</math>',
    flags=re.I,
)

LEFTOVER_TAG_CMD_RE = re.compile(r"(<(?:mi|mtext|mo)[^>]*>)([^<]*\\[^<]*)(</(?:mi|mtext|mo)>)", flags=re.I)

PROTECTED_TAG_RE = re.compile(
    r"(<svg[\s\S]*?</svg>|<img\b[^>]*>|<math[\s\S]*?</math>)",
    flags=re.I,
)

HTML_TAG_RE = re.compile(r"(<[^>]+>)")


def _preclean_nonstandard_latex(s: str) -> str:
    if "\\" not in s:
        return s
    # Literal unescaped \n before capitalized word/digit in OCR dataset text
    s = re.sub(r"\\n(?=[A-Z0-9])", " ", s)
    # Fill-in-the-blank \rule{...}{...}
    s = re.sub(r"\\rule(?:\[[^\]]*\])?\s*\{[^{}]*\}\s*\{[^{}]*\}", "____", s)
    # Pifont \ding{...}
    s = re.sub(
        r"\\ding\s*\{\s*(\d+)\s*\}",
        lambda m: "✓" if m.group(1) in ("51", "52") else ("✗" if m.group(1) in ("55", "56") else "•"),
        s,
    )
    # Formatting noise macros
    s = re.sub(r"\\(?:inline|noindent|displaystyle|textstyle|scriptstyle)\b\s*", "", s)
    s = TEXT_GREEK_RE.sub(r"\\\1", s)
    s = GLUED_MACRO_RE.sub(r"\\\1 \2", s)
    s = GLUED_UNIT_GREEK_RE.sub(r"\\\1 \\mathrm{\2}", s)
    for k in (
        r"\AAngstrom", r"\AA", r"\textbullet", r"\bullets", r"\textcent",
        r"\textsterling", r"\texteuro", r"\textyen", r"\textdegree",
        r"\textquotedblright", r"\textquotedblleft", r"\textquoteright",
        r"\textquoteleft", r"\textasteriskcentered", r"\textendash", r"\textemdash",
        r"\textminus", r"\textpm", r"\texttimes", r"\textdiv",
    ):
        if k in s:
            s = s.replace(k, UNICODE_FALLBACK_MAP[k])
    return s


def _strip_unknown_cmd_text(txt: str) -> str:
    cleaned = html.unescape(txt)
    for k, v in sorted(UNICODE_FALLBACK_MAP.items(), key=lambda kv: -len(kv[0])):
        if k in cleaned:
            cleaned = cleaned.replace(k, v)
    cleaned = re.sub(r"\\(?:mathrm|text|textbf|textit|mathbf|fn|cyrchar|Elzbar)\s*\{([^{}]*)\}", r"\1", cleaned)
    cleaned = re.sub(r"\\(?:left|right)\b\.?", "", cleaned)
    cleaned = re.sub(r"\\([a-zA-Z]+)", r"\1", cleaned)
    cleaned = cleaned.replace("\\", "")
    return html.escape(cleaned, quote=False)


def convert_latex_expr_to_mathml(expr: str, display: str = "inline") -> str:
    raw = html.unescape(str(expr or "")).strip()
    if not raw:
        return ""
    norm = _preclean_nonstandard_latex(raw)
    norm = norm.replace(r"\degree", r"^\circ").replace(r"\tfrac", r"\frac").replace(r"\dfrac", r"\frac")
    norm = re.sub(r"\\rm\s*\{([^{}]*)\}", r"\\mathrm{\1}", norm)
    norm = re.sub(r"\\bf\s*\{([^{}]*)\}", r"\\mathbf{\1}", norm)
    try:
        mml = l2m.convert(norm, display=display)
        if mml and "<math" in mml:
            if "\\" in mml:
                mml = LEFTOVER_TAG_CMD_RE.sub(
                    lambda m: f"{m.group(1)}{_strip_unknown_cmd_text(m.group(2))}{m.group(3)}",
                    mml,
                )
            if "\\" not in mml:
                return mml
    except Exception:
        pass
    # Graceful clean MathML fallback with guaranteed zero raw LaTeX backslashes
    cleaned = norm
    cleaned = re.sub(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"(\1)/(\2)", cleaned)
    cleaned = re.sub(r"\\sqrt\s*\{([^{}]*)\}", r"√(\1)", cleaned)
    cleaned = cleaned.replace("{", "").replace("}", "")
    safe_inner = _strip_unknown_cmd_text(cleaned)
    return f'<math xmlns="http://www.w3.org/1998/Math/MathML" display="{display}"><mrow><mtext>{safe_inner}</mtext></mrow></math>'


def _fix_broken_mi_block(match: re.Match) -> str:
    inner = html.unescape(match.group(1)).strip()
    # Single clean variable like <mi>x</mi> or <mi>V</mi> is already valid MathML
    if len(inner) <= 2 and inner.isalpha() and "\\" not in inner:
        return match.group(0)
    if any(ch in inner for ch in ("\\", "^", "_", "{", "}", "=", "+", "-", "/", "*")) or re.search(r"\d", inner) or " " in inner:
        return convert_latex_expr_to_mathml(inner, display="inline")
    return match.group(0)


def _is_currency_pair(inner: str) -> bool:
    s = inner.strip()
    if not s:
        return True
    if "\\" in s or any(ch in s for ch in ("^", "_", "{", "}", "=")):
        return False
    # e.g. "$50 and lunch costs $20" -> inner is "50 and lunch costs "
    if s[0].isdigit() and re.search(r"[a-zA-Z]{3,}\s+[a-zA-Z]{3,}", s):
        return True
    return False


def _match_bare_math_prefix(text: str, pos: int) -> int:
    """
    If `text[pos:]` starts with a short math base/coefficient immediately attached to
    a LaTeX command, superscript (`^`), or math subscript (`_{...}`, `_\\cmd`, or `x_1`),
    returns the index right after the base/coefficient; otherwise returns -1.
    Never matches normal snake_case identifiers like `option_a` or `passage_id`.
    """
    n = len(text)
    if pos >= n or not text[pos].isalnum():
        return -1
    # Don't start mid-word
    if pos > 0 and (text[pos - 1].isalnum() or text[pos - 1] == "_"):
        return -1
    m = re.match(r"^[A-Za-z0-9]+(?:\.[0-9]+)?", text[pos:])
    if not m:
        return -1
    base = m.group(0)
    end = pos + len(base)
    if end >= n:
        return -1
    ch = text[end]
    # e.g. 2\pi, 3\sqrt{2}
    if ch == "\\" and end + 1 < n and text[end + 1].isalpha() and base.replace(".", "", 1).isdigit():
        return end
    # e.g. 98^\circ, 45^{\circ}, x^2, 10^{-6}, x^{\frac{1}{2}}
    if ch == "^" and end + 1 < n and (text[end + 1] in ("{", "\\", "+", "-") or text[end + 1].isalnum()):
        return end
    # e.g. x_{1}, a_{\max}, x_1, v_0 (avoid snake_case words like option_a)
    if ch == "_" and end + 1 < n:
        nxt = text[end + 1]
        if nxt in ("{", "\\"):
            if len(base) <= 3:
                return end
        elif len(base) == 1 and base.isalpha():
            # Single-letter variable with short subscript like x_1, v_0, a_n (not followed by more word chars)
            m_sub = re.match(r"^_([0-9]{1,3}|[a-zA-Z])(?![A-Za-z0-9_])", text[end:])
            if m_sub:
                return end
    return -1


def _consume_balanced_group(text: str, pos: int, open_ch: str, close_ch: str) -> int:
    n = len(text)
    if pos >= n or text[pos] != open_ch:
        return pos
    depth = 1
    k = pos + 1
    while k < n and depth > 0:
        if text[k] == open_ch:
            depth += 1
        elif text[k] == close_ch:
            depth -= 1
        k += 1
    return k


def _consume_sup_or_sub(text: str, pos: int) -> int:
    """Consumes `^...` or `_...` starting at `pos` (including `^{\\circ}`, `^\\circ`, `^{-6}`, `^2`)."""
    n = len(text)
    if pos >= n or text[pos] not in ("^", "_"):
        return pos
    k = pos + 1
    while k < n and text[k] == " ":
        k += 1
    if k >= n:
        return pos
    if text[k] == "{":
        return _consume_balanced_group(text, k, "{", "}")
    if text[k] == "\\" and k + 1 < n and text[k + 1].isalpha():
        k += 1
        while k < n and text[k].isalpha():
            k += 1
        if k < n and text[k] == "{":
            k = _consume_balanced_group(text, k, "{", "}")
        return k
    if text[k] in ("+", "-") and k + 1 < n and text[k + 1].isalnum():
        k += 1
    while k < n and text[k].isalnum():
        k += 1
    return k


def _convert_bare_latex_in_plain_segment(seg: str) -> str:
    """
    Scans a plain HTML-escaped text segment (no HTML tags, no <math> blocks) for:
      - Bare brace-balanced LaTeX runs (`\\frac{\\sqrt{3}}{2}\\pi`, `3\\sqrt{2}`, `98^\\circ`, `45^{\\circ}`)
      - Bare `x^{2}`, `10^{-6}`, `x_{1}` tokens
      - Escaped literal punctuation (`\\%` -> `%`, `\\&` -> `&amp;`)
    """
    if "\\" not in seg and "^" not in seg and "_" not in seg:
        return seg

    text = html.unescape(seg)
    text = text.replace(r"\%", "%").replace(r"\&", "&")
    text = _preclean_nonstandard_latex(text)
    if "\\" not in text and "^" not in text and "_" not in text:
        return html.escape(text, quote=False)

    n = len(text)
    out = []
    i = 0

    while i < n:
        pref_end = _match_bare_math_prefix(text, i)
        is_cmd = text[i] == "\\" and i + 1 < n and text[i + 1].isalpha()

        if is_cmd or pref_end > i:
            start = i
            j = pref_end if pref_end > i else i
            while j < n:
                if text[j] in ("^", "_"):
                    nxt_j = _consume_sup_or_sub(text, j)
                    if nxt_j > j:
                        j = nxt_j
                        continue
                if text[j] == "\\" and j + 1 < n and text[j + 1].isalpha():
                    j += 1
                    while j < n and text[j].isalpha():
                        j += 1
                    # Consume optional whitespace + balanced [...], {...}, or ^/_ arguments
                    while j < n:
                        k = j
                        while k < n and text[k] == " ":
                            k += 1
                        if k < n and text[k] in ("{", "["):
                            close_ch = "}" if text[k] == "{" else "]"
                            j = _consume_balanced_group(text, k, text[k], close_ch)
                        elif k < n and text[k] in ("^", "_"):
                            j = _consume_sup_or_sub(text, k)
                        else:
                            break
                # Continue math run if immediately followed by another \cmd, ^/_, or math operator glue
                k = j
                while k < n and text[k] == " ":
                    k += 1
                if k < n and text[k] == "\\" and k + 1 < n and text[k + 1].isalpha():
                    j = k
                    continue
                if k == j and k < n and text[k] in ("^", "_"):
                    j = _consume_sup_or_sub(text, k)
                    continue
                if k < n and text[k] in ("=", "+", "-", "*", "/"):
                    k += 1
                    while k < n and text[k] == " ":
                        k += 1
                    if k < n and (
                        (text[k] == "\\" and k + 1 < n and text[k + 1].isalpha())
                        or text[k].isdigit()
                        or (text[k].isalpha() and (k + 1 == n or not text[k + 1].isalpha()))
                    ):
                        j = k
                        if text[j] != "\\":
                            while j < n and (
                                text[j].isdigit()
                                or text[j] == "."
                                or (text[j].isalpha() and (j + 1 == n or not text[j + 1].isalpha()))
                            ):
                                j += 1
                            if j < n and text[j] in ("^", "_"):
                                j = _consume_sup_or_sub(text, j)
                        continue
                # Consume trailing uppercase geometry labels or numbers like `\triangle ABC` or `\angle 14`
                if k < n and k > j and is_cmd:
                    m_lbl = re.match(r"^([A-Z]{1,4}\b|\d{1,4}\b)(?!\s+[a-z]{3,})", text[k:])
                    if m_lbl:
                        j = k + len(m_lbl.group(1))
                        continue
                break

            expr = text[start:j].strip()
            out.append(convert_latex_expr_to_mathml(expr, display="inline"))
            if j > start and j <= n and text[j - 1] == " ":
                out.append(" ")
            i = j
            continue

        out.append(html.escape(text[i], quote=False))
        i += 1

    return "".join(out)


def ensure_clean_mathml_html(raw_html: str) -> str:
    """
    Idempotent, fast HTML + LaTeX -> Clean W3C MathML converter.
    Safe to run on plain text OR existing HTML containing `<p>`, `<svg>`, `<img>`, and `<math>`.
    """
    if not raw_html:
        return ""
    s = str(raw_html)

    # Fast path: if no backslash, no $, no ^, and no _ -> return as-is
    if "\\" not in s and "$" not in s and "^" not in s and "_" not in s:
        return s

    # Step 1: Repair previously mis-wrapped <math><mrow><mi>\frac...</mi></mrow></math> blocks
    if "<mi" in s or "<mtext" in s:
        s = BROKEN_MI_RE.sub(_fix_broken_mi_block, s)
        if "\\" in s:
            s = LEFTOVER_TAG_CMD_RE.sub(
                lambda m: f"{m.group(1)}{_strip_unknown_cmd_text(m.group(2))}{m.group(3)}",
                s,
            )

    # Step 2: Mask existing clean <svg>, <img>, and <math> blocks so we never corrupt them
    stash: list[str] = []

    def _stash_block(m: re.Match) -> str:
        idx = len(stash)
        stash.append(m.group(0))
        return f"@@MMLSTASH_{idx}@@"

    s = PROTECTED_TAG_RE.sub(_stash_block, s)

    # Protect escaped literal dollar signs (\$50 -> &#36;50) before $...$ math delimiter scanning
    if r"\$" in s:
        s = s.replace(r"\$", "&#36;")

    # Step 3: Convert delimited LaTeX: $$...$$, \[...\], \(...\), and $...$
    if "$$" in s:
        s = re.sub(
            r"\$\$([\s\S]{1,600}?)\$\$",
            lambda m: _stash_block_str(convert_latex_expr_to_mathml(m.group(1), display="block"), stash),
            s,
        )
    if r"\[" in s:
        s = re.sub(
            r"\\\[([\s\S]{1,600}?)\\\]",
            lambda m: _stash_block_str(convert_latex_expr_to_mathml(m.group(1), display="block"), stash),
            s,
        )
    if r"\(" in s:
        s = re.sub(
            r"\\\(([\s\S]{1,500}?)\\\)",
            lambda m: _stash_block_str(convert_latex_expr_to_mathml(m.group(1), display="inline"), stash),
            s,
        )
    if "$" in s:
        def _dollar_repl(m: re.Match) -> str:
            inner = m.group(1)
            if _is_currency_pair(inner):
                return m.group(0)
            return _stash_block_str(convert_latex_expr_to_mathml(inner, display="inline"), stash)

        s = re.sub(r"\$([^$\n]{1,320}?)\$", _dollar_repl, s)

    # Step 4: Convert bare/undelimited LaTeX (\frac{...}{...}, \triangle ABC, 98^\circ, x^{2}) outside HTML tags
    if "\\" in s or "^" in s or "_" in s:
        tokens = HTML_TAG_RE.split(s)
        for t_idx in range(0, len(tokens), 2):
            seg = tokens[t_idx]
            if not seg:
                continue
            # Preserve @@MMLSTASH_k@@ tokens while scanning plain text around them
            sub_parts = re.split(r"(@@MMLSTASH_\d+@@)", seg)
            for sp_i in range(0, len(sub_parts), 2):
                if sub_parts[sp_i]:
                    sub_parts[sp_i] = _convert_bare_latex_in_plain_segment(sub_parts[sp_i])
            tokens[t_idx] = "".join(sub_parts)
        s = "".join(tokens)

    # Step 5: Restore all stashed <math>, <svg>, and <img> blocks
    for idx in range(len(stash) - 1, -1, -1):
        s = s.replace(f"@@MMLSTASH_{idx}@@", stash[idx])

    return s


def _stash_block_str(val: str, stash: list[str]) -> str:
    idx = len(stash)
    stash.append(val)
    return f"@@MMLSTASH_{idx}@@"


def sanitize_plain_text_to_clean_mathml_html(raw_text: str) -> str:
    """
    Entry point for raw unescaped dataset strings (replaces old broken `sanitize_to_mathml_html`).
    Escapes HTML text safely AFTER extracting/converting LaTeX math into clean W3C MathML!
    """
    if not raw_text:
        return ""
    escaped = html.escape(str(raw_text).strip(), quote=False)
    return ensure_clean_mathml_html(escaped)


def retroactive_convert_db_latex_to_mathml(db_path: Path) -> int:
    """
    Scans `questions` and `passages` in `db_path` for any rows containing `\\`, `$`, `^`, or `_{`
    and converts all LaTeX to clean W3C MathML in-place!
    """
    if not db_path.exists():
        return 0
    conn = sqlite3.connect(db_path, timeout=120.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=120000;")

    updated_rows = 0
    cand_ids = [
        r[0]
        for r in conn.execute(
            """
            SELECT question_id
            FROM questions
            WHERE question_html LIKE '%\\%' OR question_html LIKE '%$%' OR question_html LIKE '%^%' OR question_html LIKE '%_{%'
               OR option_a LIKE '%\\%' OR option_a LIKE '%$%' OR option_a LIKE '%^%' OR option_a LIKE '%_{%'
               OR option_b LIKE '%\\%' OR option_b LIKE '%$%' OR option_b LIKE '%^%' OR option_b LIKE '%_{%'
               OR option_c LIKE '%\\%' OR option_c LIKE '%$%' OR option_c LIKE '%^%' OR option_c LIKE '%_{%'
               OR option_d LIKE '%\\%' OR option_d LIKE '%$%' OR option_d LIKE '%^%' OR option_d LIKE '%_{%'
               OR explanation_html LIKE '%\\%' OR explanation_html LIKE '%$%' OR explanation_html LIKE '%^%' OR explanation_html LIKE '%_{%'
            """
        ).fetchall()
    ]

    chunk_size = 800
    for start_idx in range(0, len(cand_ids), chunk_size):
        chunk = cand_ids[start_idx : start_idx + chunk_size]
        placeholders = ",".join("?" for _ in chunk)
        rows = conn.execute(
            f"""
            SELECT question_id, question_html, option_a, option_b, option_c, option_d, explanation_html
            FROM questions
            WHERE question_id IN ({placeholders})
            """,
            chunk,
        ).fetchall()
        batch_updates = []
        for qid, qh, oa, ob, oc, od, eh in rows:
            nqh = ensure_clean_mathml_html(qh or "")
            noa = ensure_clean_mathml_html(oa or "")
            nob = ensure_clean_mathml_html(ob or "")
            noc = ensure_clean_mathml_html(oc or "")
            nod = ensure_clean_mathml_html(od or "")
            neh = ensure_clean_mathml_html(eh or "")
            if (nqh, noa, nob, noc, nod, neh) != (qh or "", oa or "", ob or "", oc or "", od or "", eh or ""):
                batch_updates.append((nqh, noa, nob, noc, nod, neh, qid))
                updated_rows += 1
        if batch_updates:
            conn.executemany(
                """
                UPDATE questions
                SET question_html = ?, option_a = ?, option_b = ?, option_c = ?, option_d = ?, explanation_html = ?
                WHERE question_id = ?
                """,
                batch_updates,
            )
            conn.commit()

    # Also clean `passages` table if present
    try:
        p_rows = conn.execute(
            "SELECT passage_id, passage_html FROM passages WHERE passage_html LIKE '%\\%' OR passage_html LIKE '%$%' OR passage_html LIKE '%^%'"
        ).fetchall()
        p_upd = []
        for pid, ph in p_rows:
            nph = ensure_clean_mathml_html(ph or "")
            if nph != (ph or ""):
                p_upd.append((nph, pid))
        if p_upd:
            conn.executemany("UPDATE passages SET passage_html = ? WHERE passage_id = ?", p_upd)
            conn.commit()
    except Exception:
        pass

    conn.close()
    return updated_rows
