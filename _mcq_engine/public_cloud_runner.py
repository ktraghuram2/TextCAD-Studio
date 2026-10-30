# -*- coding: utf-8 -*-
r"""
Unlimited 24x7 Multi-Agent Public GitHub Cloud Runner (`public_cloud_runner.py`)
================================================================================
Runs 16 Concurrent Cloud Agents (100% Zero External API Keys):
  - 8 Parallel Cloud AI Staging Auditor Agents (`ThreadPoolExecutor(max_workers=8)`)
    continuously auditing `db_staging_queue.sqlite`, verifying answers, writing >= 260-char
    step-by-step explanations in clean W3C MathML across 8 separate `models.github.ai`
    model pools + `g4f[slim]` keyless cloud providers (and Google AI Ultra `agy` swarm on self-hosted).
  - 4 Parallel Cloud Parquet & Figure/Passage Harvester Agents (`ThreadPoolExecutor(max_workers=4)`).
  - 4 Parallel Continuous Multi-Language Syllabus Web Scraper Agents (`continuous_cloud_web_scraper.py`).
  - Sweeps all existing SQLite rows on boot via `mathml_sanitizer.retroactive_convert_db_latex_to_mathml()`
    so 100% of existing & new questions render clean semantic W3C MathML (zero raw LaTeX!).
  - Publishes live progress every 45s to `https://ktraghuram2.github.io/TextCAD-Studio/mcq_live/`.
"""

import gzip
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ENGINE_SRC = Path(__file__).resolve().parent
REPO_ROOT = ENGINE_SRC.parent
WORK_DIR = Path(os.environ.get("MCQ_WORK_DIR", "/tmp/mcq_work"))
RELEASE_TAG = "v1.0-mcq-live-db"

MATHML_RETRO_STATS = {
    "db1_converted": 0,
    "db2_converted": 0,
    "staging_converted": 0,
    "total_unique_converted": 0,
    "clean_mathml_enforced": True,
}


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] [16-AGENT-NONSTOP-CLOUD] {msg}", flush=True)


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

    # Sweep DB1, DB2, and Staging Queue BEFORE reconstructing Master so Master inherits 100% Clean W3C MathML
    import mathml_sanitizer as ms
    c_db1 = ms.retroactive_convert_db_latex_to_mathml(WORK_DIR / "db1_scraped_mcqs.sqlite")
    c_db2 = ms.retroactive_convert_db_latex_to_mathml(WORK_DIR / "db2_pyq_mcqs.sqlite")
    c_stg = ms.retroactive_convert_db_latex_to_mathml(WORK_DIR / "db_staging_queue.sqlite")
    MATHML_RETRO_STATS["db1_converted"] = c_db1
    MATHML_RETRO_STATS["db2_converted"] = c_db2
    MATHML_RETRO_STATS["staging_converted"] = c_stg
    MATHML_RETRO_STATS["total_unique_converted"] = c_db1 + c_db2 + c_stg
    log(
        f"[CLEAN-MATHML-SWEEP] Converted raw LaTeX -> W3C MathML: "
        f"DB1={c_db1:,} | DB2={c_db2:,} | Staging={c_stg:,} | Total={c_db1 + c_db2 + c_stg:,}"
    )

    import pipeline
    m_path = WORK_DIR / "mcq_bank.sqlite"
    db1_path = WORK_DIR / "db1_scraped_mcqs.sqlite"
    db2_path = WORK_DIR / "db2_pyq_mcqs.sqlite"
    if m_path.exists():
        ms.retroactive_convert_db_latex_to_mathml(m_path)
    elif db1_path.exists():
        log("Reconstructing Master mcq_bank.sqlite from Clean-MathML db1 + db2...")
        shutil.copyfile(db1_path, m_path)
        c = sqlite3.connect(m_path, timeout=90.0)
        pipeline.ensure_db_schema(c)
        if db2_path.exists():
            c2 = sqlite3.connect(db2_path, timeout=90.0)
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
    import staging_and_passage_manager as spm

    build_db1_viewer.generate_db1_html()
    counts = multi_db_manager.get_db_counts()
    raw_stats = build_db1_viewer.get_raw_scrape_stats()
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    log_lines = []
    lp = WORK_DIR / "turbo_parquet_and_figure_harvester.log"
    if lp.exists():
        try:
            log_lines = lp.read_text(encoding="utf-8", errors="ignore").strip().splitlines()[-3:]
        except Exception:
            pass
    if extra_note:
        log_lines.append(extra_note)
    log_tail = "\n".join(log_lines) if log_lines else "16-Agent Cloud Swarm Active (Clean W3C MathML)..."

    status_obj = {
        "status": "RUNNING_IN_GITHUB_CLOUD",
        "timestamp": f"{now_utc} · 🟢 LIVE 24x7 CLOUD (16 NONSTOP AGENTS · 100% CLEAN W3C MATHML)",
        "last_updated_utc": now_utc,
        "worldwide_exams_count": 19060,
        "countries_covered": 31,
        "mathml_status": MATHML_RETRO_STATS,
        "active_cloud_agents": {
            "ai_staging_agents": 8,
            "parquet_harvester_agents": 4,
            "web_subtopic_scraper_agents": 4,
            "total_parallel_agents": 16,
            "telemetry": spm.SWARM_TELEMETRY,
        },
        "counts": counts,
        "raw_stats": raw_stats,
        "log_tail": f"[🤖 16 NONSTOP CLOUD AGENTS · 100% CLEAN W3C MATHML]\n{log_tail}",
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
        prom_cnt = counts.get("staging_promoted_count", 0)
        p_cnt = counts.get("passage_mcqs_count", 0)
        subprocess.run(
            ["git", "commit", "-m", f"chore(mcq-live): {m_cnt:,} Verified (+{prom_cnt:,} AI-Promoted) | {s_cnt:,} Staging | {p_cnt:,} Passage Qs [Clean MathML]"],
            cwd=str(REPO_ROOT),
            check=False,
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=str(REPO_ROOT), check=False)

    return status_obj


def upload_release_checkpoints() -> None:
    upload_files = []
    for fname in ("db1_scraped_mcqs.sqlite", "db2_pyq_mcqs.sqlite", "db_staging_queue.sqlite", "turbo_parquet_state.json", "cloud_subtopic_scraper_state.json"):
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
    log("Booting 16-Agent Nonstop Cloud Swarm (8 AI Staging + 4 Parquet + 4 Web Scrapers, Clean W3C MathML, Zero API Keys)...")
    prepare_workdir()

    subprocess.run(["git", "config", "user.name", "Cloud MCQ Live Bot"], cwd=str(REPO_ROOT), check=False)
    subprocess.run(["git", "config", "user.email", "ktraghuram2@gmail.com"], cwd=str(REPO_ROOT), check=False)

    import staging_and_passage_manager as spm

    sweep = spm.audit_existing_dbs_and_move_short_to_staging()
    log(
        f"[AUDIT-GATE] Moved {sweep['moved_to_staging']:,} short -> Staging | "
        f"Verified: {sweep['kept_verified']:,} | Staging Pending: {sweep['staging_pending']:,}"
    )

    tot_mml = MATHML_RETRO_STATS["total_unique_converted"]
    build_and_push_live_pages(
        extra_note=(
            f"[CLEAN-MATHML-SWEEP] Converted {tot_mml:,} existing DB rows (DB1={MATHML_RETRO_STATS['db1_converted']:,}, "
            f"DB2={MATHML_RETRO_STATS['db2_converted']:,}, Staging={MATHML_RETRO_STATS['staging_converted']:,}) -> 100% pure W3C MathML!"
        )
    )
    if tot_mml > 0:
        upload_release_checkpoints()

    harvester_proc = subprocess.Popen(
        [sys.executable, "-u", str(WORK_DIR / "turbo_parquet_and_figure_harvester.py")],
        cwd=str(WORK_DIR),
    )
    web_scraper_proc = subprocess.Popen(
        [sys.executable, "-u", str(WORK_DIR / "continuous_cloud_web_scraper.py")],
        cwd=str(WORK_DIR),
    )

    stop_swarm = threading.Event()
    swarm_state = {"promoted_run": 0, "rejected_run": 0, "waves": 0, "last_note": "Starting 8 AI Agents..."}

    def continuous_8_agent_ai_swarm() -> None:
        while not stop_swarm.is_set():
            try:
                res = spm.run_ai_staging_enrichment_batch(batch_size=3, max_batches=2, num_agents=8)
                swarm_state["promoted_run"] += res.get("promoted", 0)
                swarm_state["rejected_run"] += res.get("rejected", 0)
                swarm_state["waves"] += 1
                swarm_state["last_note"] = res.get("note", "")
                if res.get("promoted", 0) == 0:
                    time.sleep(6.0)
                else:
                    time.sleep(0.5)
            except Exception as exc:
                swarm_state["last_note"] = f"Swarm retry: {type(exc).__name__}"
                time.sleep(5.0)

    swarm_thread = threading.Thread(target=continuous_8_agent_ai_swarm, daemon=True)
    swarm_thread.start()

    for cycle in range(1, 361):
        time.sleep(45)
        note = (
            f"[8-AI-AGENT-SWARM] Wave {swarm_state['waves']}: +{swarm_state['promoted_run']:,} AI-Verified & Promoted this run "
            f"(Rejected low-quality: {swarm_state['rejected_run']:,}) | {swarm_state['last_note']}"
        )
        status_obj = build_and_push_live_pages(extra_note=note)
        m_cnt = status_obj["counts"].get("mcq_bank.sqlite (Master)", 0)
        s_cnt = status_obj["counts"].get("staging_pending_count", 0)
        prom_cnt = status_obj["counts"].get("staging_promoted_count", 0)
        p_cnt = status_obj["counts"].get("passage_mcqs_count", 0)
        log(
            f"Cycle {cycle}: Verified={m_cnt:,} (+{prom_cnt:,} AI-Promoted) | "
            f"Staging={s_cnt:,} | Passage Qs={p_cnt:,} | {swarm_state['last_note']}"
        )

        if cycle % 4 == 0:
            upload_release_checkpoints()

        # Restart web scraper if it ever exits so internet scraping NEVER stops!
        if web_scraper_proc.poll() is not None:
            web_scraper_proc = subprocess.Popen(
                [sys.executable, "-u", str(WORK_DIR / "continuous_cloud_web_scraper.py")],
                cwd=str(WORK_DIR),
            )

    stop_swarm.set()
    for proc in (harvester_proc, web_scraper_proc):
        if proc.poll() is None:
            proc.terminate()
    upload_release_checkpoints()
    log("Uploading complete! Self-chaining next 24x7 nonstop cloud run immediately...")
    subprocess.run(["gh", "workflow", "run", "mcq_unlimited_cloud.yml"], cwd=str(REPO_ROOT), check=False)


if __name__ == "__main__":
    main()
