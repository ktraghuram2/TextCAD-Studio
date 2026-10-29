# -*- coding: utf-8 -*-
r"""
Unlimited 24x7 Public GitHub Cloud Runner (`public_cloud_runner.py`)
====================================================================
1. Restores compressed SQLite checkpoints (`db1`, `db2`, `db_staging_queue`) into `/tmp/mcq_work`.
2. Runs `staging_and_passage_manager.audit_existing_dbs_and_move_short_to_staging()` so 100% of
   short/low/no-explanation items move OUT of `DB1`/`DB2` into `db_staging_queue.sqlite`!
3. Runs `turbo_parquet_and_figure_harvester.py` (Shared Passages `1 Para -> Multi Qs` + Figures +
   Strict Explanation Gate) AND `run_ai_staging_enrichment_batch()` (AI quality check + rich
   explanation generation before promoting from Staging Queue to Verified DBs).
4. Publishes live stats & paginated views (`ALL`, `FIGURES`, `PASSAGES`, `DB1`, `DB2`, `STAGING`)
   directly to `https://ktraghuram2.github.io/TextCAD-Studio/mcq_live/` every 60 seconds!
"""

import gzip
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ENGINE_SRC = Path(__file__).resolve().parent
REPO_ROOT = ENGINE_SRC.parent
WORK_DIR = Path(os.environ.get("MCQ_WORK_DIR", "/tmp/mcq_work"))
RELEASE_TAG = "v1.0-mcq-live-db"


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] [UNLIMITED-CLOUD] {msg}", flush=True)


def prepare_workdir() -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    for item in ENGINE_SRC.glob("*"):
        if item.is_file():
            shutil.copyfile(item, WORK_DIR / item.name)

    os.chdir(WORK_DIR)
    sys.path.insert(0, str(WORK_DIR))

    subprocess.run(
        ["gh", "release", "create", RELEASE_TAG, "--title", "Live Cloud MCQ, Passage & Staging SQLite Checkpoints", "--notes", "Auto-updated 24x7 SQLite checkpoints"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["gh", "release", "download", RELEASE_TAG, "--dir", str(WORK_DIR), "--clobber"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for gz_file in sorted(WORK_DIR.glob("*.gz")):
        out_name = gz_file.name[:-3]
        out_path = WORK_DIR / out_name
        log(f"Decompressing checkpoint {gz_file.name} -> {out_name} ...")
        with gzip.open(gz_file, "rb") as f_in, open(out_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    import pipeline
    m_path = WORK_DIR / "mcq_bank.sqlite"
    db1_path = WORK_DIR / "db1_scraped_mcqs.sqlite"
    db2_path = WORK_DIR / "db2_pyq_mcqs.sqlite"
    if not m_path.exists() and db1_path.exists():
        log("Reconstructing Master mcq_bank.sqlite from db1 + db2...")
        shutil.copyfile(db1_path, m_path)
        c = sqlite3.connect(m_path, timeout=60.0)
        pipeline.ensure_db_schema(c)
        if db2_path.exists():
            c2 = sqlite3.connect(db2_path, timeout=60.0)
            pipeline.ensure_db_schema(c2)
            c2.close()
            c.execute("ATTACH DATABASE 'db2_pyq_mcqs.sqlite' AS db2")
            q_cols = ", ".join(r[1] for r in c.execute("PRAGMA table_info(questions)").fetchall())
            p_cols = ", ".join(r[1] for r in c.execute("PRAGMA table_info(passages)").fetchall())
            c.execute(f"INSERT OR IGNORE INTO main.questions ({q_cols}) SELECT {q_cols} FROM db2.questions")
            c.execute(f"INSERT OR IGNORE INTO main.passages ({p_cols}) SELECT {p_cols} FROM db2.passages")
            c.commit()
        c.close()


def build_and_push_live_pages(extra_note: str = "") -> dict:
    sys.path.insert(0, str(WORK_DIR))
    import build_db1_viewer
    import multi_db_manager

    build_db1_viewer.generate_db1_html()
    counts = multi_db_manager.get_db_counts()
    raw_stats = build_db1_viewer.get_raw_scrape_stats()
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    log_lines = []
    lp = WORK_DIR / "turbo_parquet_and_figure_harvester.log"
    if lp.exists():
        try:
            log_lines = lp.read_text(encoding="utf-8", errors="ignore").strip().splitlines()[-4:]
        except Exception:
            pass
    if extra_note:
        log_lines.append(extra_note)
    log_tail = "\n".join(log_lines) if log_lines else "Strict Explanation Gate + Shared Passages + AI Staging Auditor Active..."

    status_obj = {
        "status": "RUNNING_IN_GITHUB_CLOUD",
        "timestamp": f"{now_utc} · 🟢 LIVE 24x7 CLOUD (VERIFIED + STAGING QUEUE + PASSAGES)",
        "last_updated_utc": now_utc,
        "worldwide_exams_count": 19060,
        "countries_covered": 31,
        "counts": counts,
        "raw_stats": raw_stats,
        "log_tail": f"[🟢 STRICT EXPLANATION GATE + STAGING QUEUE + SHARED PASSAGES]\n{log_tail}",
        "recent_logs": log_tail,
    }

    docs_dir = WORK_DIR / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "cloud_live_status.json").write_text(json.dumps(status_obj, indent=2), encoding="utf-8")

    idx_path = docs_dir / "index.html"
    if idx_path.exists():
        html_txt = idx_path.read_text(encoding="utf-8", errors="ignore")
        html_txt = html_txt.replace(
            "fetch('./cloud_live_status.json?t=' + Date.now())",
            "fetch('https://raw.githubusercontent.com/ktraghuram2/TextCAD-Studio/main/mcq_live/cloud_live_status.json?t=' + Date.now())",
        )
        html_txt = html_txt.replace(
            "fetch(`./page_${dbKey}_${staticPage}.json?t=${Date.now()}`)",
            "fetch(`https://raw.githubusercontent.com/ktraghuram2/TextCAD-Studio/main/mcq_live/page_${dbKey}_${staticPage}.json?t=${Date.now()}`)",
        )
        idx_path.write_text(html_txt, encoding="utf-8")

    target_live = REPO_ROOT / "mcq_live"
    target_live.mkdir(parents=True, exist_ok=True)
    (target_live / "CNAME").unlink(missing_ok=True)
    for item in docs_dir.glob("*"):
        if item.is_file() and item.name != "CNAME":
            shutil.copyfile(item, target_live / item.name)

    subprocess.run(["git", "pull", "--rebase", "--autostash", "-X", "theirs", "origin", "main"], cwd=str(REPO_ROOT), check=False)
    subprocess.run(["git", "add", "-A", "mcq_live/"], cwd=str(REPO_ROOT), check=False)
    diff = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=str(REPO_ROOT))
    if diff.returncode != 0:
        m_cnt = counts.get("mcq_bank.sqlite (Master)", 0)
        s_cnt = counts.get("staging_pending_count", 0)
        p_cnt = counts.get("passage_mcqs_count", 0)
        f_cnt = counts.get("figure_mcqs_count", 0)
        subprocess.run(
            ["git", "commit", "-m", f"chore(mcq-live): {m_cnt:,} Verified | {s_cnt:,} Staging | {p_cnt:,} Passage Qs | {f_cnt:,} Figures"],
            cwd=str(REPO_ROOT),
            check=False,
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=str(REPO_ROOT), check=False)

    return status_obj


def upload_release_checkpoints() -> None:
    upload_files = []
    for fname in ("db1_scraped_mcqs.sqlite", "db2_pyq_mcqs.sqlite", "db_staging_queue.sqlite", "turbo_parquet_state.json"):
        fp = WORK_DIR / fname
        if fp.exists():
            gz_path = WORK_DIR / f"{fname}.gz"
            with open(fp, "rb") as f_in, gzip.open(gz_path, "wb", 5) as f_out:
                shutil.copyfileobj(f_in, f_out)
            upload_files.append(str(gz_path))
    if upload_files:
        subprocess.run(
            ["gh", "release", "upload", RELEASE_TAG, *upload_files, "--clobber"],
            cwd=str(REPO_ROOT),
            check=False,
        )


def main() -> None:
    log("Initializing Strict Explanation Gate + Shared-Passage + AI Staging Cloud Engine...")
    prepare_workdir()

    subprocess.run(["git", "config", "user.name", "Cloud MCQ Live Bot"], cwd=str(REPO_ROOT), check=False)
    subprocess.run(["git", "config", "user.email", "ktraghuram2@gmail.com"], cwd=str(REPO_ROOT), check=False)

    import staging_and_passage_manager as spm

    log("Running retroactive audit: moving all short/low/no-explanation rows to Staging Queue...")
    sweep = spm.audit_existing_dbs_and_move_short_to_staging()
    sweep_msg = (
        f"[STAGING-AUDIT-SWEEP] Moved {sweep['moved_to_staging']:,} short/low/no-explanation items -> Staging Queue | "
        f"Kept {sweep['kept_verified']:,} Full-Explanation Verified MCQs | Staging Pending: {sweep['staging_pending']:,}"
    )
    log(sweep_msg)
    build_and_push_live_pages(extra_note=sweep_msg)
    upload_release_checkpoints()

    harvester_proc = subprocess.Popen(
        [sys.executable, "-u", str(WORK_DIR / "turbo_parquet_and_figure_harvester.py")],
        cwd=str(WORK_DIR),
    )

    total_ai_promoted = 0
    for cycle in range(1, 201):
        time.sleep(45)
        ai_res = {"promoted": 0, "rejected": 0}
        # Once initial Parquet pass settles or concurrently in small batches, run AI Staging Auditor!
        if harvester_proc.poll() is not None or cycle % 2 == 0:
            ai_res = spm.run_ai_staging_enrichment_batch(batch_size=8, max_batches=3)
            total_ai_promoted += ai_res["promoted"]

        note = (
            f"[AI-STAGING-AUDITOR] Cycle {cycle}: +{ai_res['promoted']} AI-Verified & Promoted "
            f"(Total AI-Promoted this run: {total_ai_promoted:,}, Rejected low-quality: {ai_res['rejected']})"
        )
        status_obj = build_and_push_live_pages(extra_note=note)
        m_cnt = status_obj["counts"].get("mcq_bank.sqlite (Master)", 0)
        s_cnt = status_obj["counts"].get("staging_pending_count", 0)
        p_cnt = status_obj["counts"].get("passage_mcqs_count", 0)
        log(f"Cycle {cycle}/200: Verified = {m_cnt:,} | Staging = {s_cnt:,} | Passage Qs = {p_cnt:,} | +{ai_res['promoted']} AI-Promoted")

        if cycle % 4 == 0:
            upload_release_checkpoints()

        # Keep running AI Staging Auditor continuously while staging_pending_count > 0!
        if harvester_proc.poll() is not None and s_cnt == 0:
            upload_release_checkpoints()
            break

    if harvester_proc.poll() is None:
        harvester_proc.terminate()
    upload_release_checkpoints()


if __name__ == "__main__":
    main()
