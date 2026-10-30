# -*- coding: utf-8 -*-
r"""
Unlimited 24x7 Multi-Agent Public GitHub Cloud Runner (`public_cloud_runner.py`)
================================================================================
Runs 16 Concurrent Cloud Agents (100% Zero External API Keys):
  - 8 Parallel Cloud AI Staging Auditor Agents (`Pollinations` HTTP + isolated `g4f` subprocesses + `models.github.ai`).
  - 4 Parallel Cloud Parquet & Figure/Passage Harvester Agents (`Belebele` 122-lang + `INCLUDE-44` + `RACE` + `MathVista` + `MMMU`).
  - 4 Parallel Continuous Multi-Language Syllabus Web Scraper Agents (`21,109` granular syllabus subtopics).
  - Non-blocking Read-Only (`?mode=ro`) live status heartbeat pushed every 20 seconds + 60-second full paginated HTML refresh.
  - Background Read-Only MVCC `VACUUM INTO` hot checkpoints uploaded asynchronously without pausing live HTML counter ticks.
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
import traceback
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

_CHECKPOINT_LOCK = threading.Lock()


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] [16-AGENT-NONSTOP-CLOUD] {msg}", flush=True)


def verify_or_recover_sqlite_db(db_path: Path, is_staging: bool = False) -> None:
    """Verifies SQLite integrity; if torn WAL pages exist from an interrupted raw copy, runs sqlite3 `.recover`."""
    if not db_path.exists():
        return
    healthy = False
    try:
        conn = sqlite3.connect(db_path, timeout=60.0)
        res = conn.execute("PRAGMA quick_check(1);").fetchone()
        cnt = conn.execute("SELECT COUNT(*) FROM questions;").fetchone()[0]
        conn.close()
        if res and res[0] == "ok" and cnt >= 0:
            healthy = True
    except Exception as exc:
        log(f"[SQLITE-HEAL] {db_path.name} failed quick_check ({exc}); launching automatic recovery...")

    if healthy:
        return

    rec_path = db_path.with_suffix(".recovered.sqlite")
    rec_path.unlink(missing_ok=True)
    if shutil.which("sqlite3"):
        cmd = f'sqlite3 "{db_path}" ".recover" | sqlite3 "{rec_path}"'
        subprocess.run(["bash", "-c", cmd], check=False, timeout=180)

    salvaged = 0
    if rec_path.exists() and rec_path.stat().st_size > 32768:
        try:
            rc = sqlite3.connect(rec_path, timeout=60.0)
            salvaged = rc.execute("SELECT COUNT(*) FROM questions;").fetchone()[0]
            rc.close()
        except Exception:
            salvaged = 0

    if salvaged > 0:
        log(f"[SQLITE-HEAL] Recovered {salvaged:,} intact rows in {db_path.name} via sqlite3 .recover!")
        db_path.unlink(missing_ok=True)
        shutil.move(str(rec_path), str(db_path))
    else:
        rec_path.unlink(missing_ok=True)
        log(f"[SQLITE-HEAL] Reinitializing fresh schema for corrupted {db_path.name}...")
        db_path.unlink(missing_ok=True)

    import pipeline
    import staging_and_passage_manager as spm
    c = sqlite3.connect(db_path, timeout=60.0)
    if is_staging:
        spm.ensure_staging_schema(c)
    else:
        pipeline.ensure_db_schema(c)
    c.close()


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
        timeout=60,
    )
    subprocess.run(
        ["gh", "release", "download", RELEASE_TAG, "--dir", str(WORK_DIR), "--clobber"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=240,
    )

    for gz_file in sorted(WORK_DIR.glob("*.gz")):
        out_name = gz_file.name[:-3]
        out_path = WORK_DIR / out_name
        log(f"Decompressing checkpoint {gz_file.name} -> {out_name} ...")
        try:
            with gzip.open(gz_file, "rb") as f_in, open(out_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        except Exception as gz_err:
            log(f"[GZIP-WARN] Truncated archive {gz_file.name} ({gz_err}); keeping partial/fresh file.")
        finally:
            gz_file.unlink(missing_ok=True)

    verify_or_recover_sqlite_db(WORK_DIR / "db1_scraped_mcqs.sqlite", is_staging=False)
    verify_or_recover_sqlite_db(WORK_DIR / "db2_pyq_mcqs.sqlite", is_staging=False)
    verify_or_recover_sqlite_db(WORK_DIR / "db_staging_queue.sqlite", is_staging=True)

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
        verify_or_recover_sqlite_db(m_path, is_staging=False)
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


def _safe_git_sync_and_push(commit_msg: str) -> None:
    """Commits and pushes `mcq_live/` with hard timeouts and automatic rebase recovery."""
    pull_res = subprocess.run(
        ["git", "pull", "--rebase", "--autostash", "-X", "theirs", "origin", "main"],
        cwd=str(REPO_ROOT),
        check=False,
        timeout=45,
    )
    if pull_res.returncode != 0:
        subprocess.run(["git", "rebase", "--abort"], cwd=str(REPO_ROOT), check=False, timeout=15)
        subprocess.run(["git", "fetch", "origin", "main"], cwd=str(REPO_ROOT), check=False, timeout=30)
        subprocess.run(["git", "reset", "--mixed", "origin/main"], cwd=str(REPO_ROOT), check=False, timeout=15)

    subprocess.run(["git", "add", "-A", "mcq_live/"], cwd=str(REPO_ROOT), check=False, timeout=25)
    diff = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=str(REPO_ROOT), timeout=15)
    if diff.returncode != 0:
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(REPO_ROOT), check=False, timeout=25)
        push_res = subprocess.run(["git", "push", "origin", "main"], cwd=str(REPO_ROOT), check=False, timeout=45)
        if push_res.returncode != 0:
            subprocess.run(["git", "pull", "--rebase", "-X", "theirs", "origin", "main"], cwd=str(REPO_ROOT), check=False, timeout=45)
            subprocess.run(["git", "push", "origin", "main"], cwd=str(REPO_ROOT), check=False, timeout=45)


def build_and_push_live_pages(extra_note: str = "", rebuild_full_pages: bool = True) -> dict:
    sys.path.insert(0, str(WORK_DIR))
    import build_db1_viewer
    import multi_db_manager
    import staging_and_passage_manager as spm

    if rebuild_full_pages:
        try:
            build_db1_viewer.generate_db1_html()
        except Exception as viewer_err:
            log(f"[VIEWER-WARN] Full HTML regen skipped this tick ({viewer_err}); pushing fast counters.")

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

    target_live = REPO_ROOT / "mcq_live"
    target_live.mkdir(parents=True, exist_ok=True)
    (target_live / "CNAME").unlink(missing_ok=True)
    if rebuild_full_pages:
        for item in docs_dir.glob("*"):
            if item.is_file() and item.name != "CNAME":
                shutil.copyfile(item, target_live / item.name)
    else:
        shutil.copyfile(docs_dir / "cloud_live_status.json", target_live / "cloud_live_status.json")

    m_cnt = counts.get("mcq_bank.sqlite (Master)", 0)
    s_cnt = counts.get("staging_pending_count", 0)
    prom_cnt = counts.get("staging_promoted_count", 0)
    p_cnt = counts.get("passage_mcqs_count", 0)
    commit_msg = f"chore(mcq-live): {m_cnt:,} Verified (+{prom_cnt:,} AI-Promoted) | {s_cnt:,} Staging | {p_cnt:,} Passage Qs [Clean MathML]"
    _safe_git_sync_and_push(commit_msg)

    return status_obj


def upload_release_checkpoints() -> None:
    """
    Uses Read-Only MVCC `VACUUM INTO` (`?mode=ro`) so hot snapshots NEVER block active writers,
    NEVER livelock-restart on concurrent commits, and NEVER tear WAL pages.
    """
    if not _CHECKPOINT_LOCK.acquire(blocking=False):
        return
    try:
        upload_files = []
        for fname in ("db1_scraped_mcqs.sqlite", "db2_pyq_mcqs.sqlite", "db_staging_queue.sqlite", "turbo_parquet_state.json", "cloud_subtopic_scraper_state.json"):
            fp = WORK_DIR / fname
            if not fp.exists():
                continue
            gz_path = WORK_DIR / f"{fname}.gz"
            try:
                if fname.endswith(".sqlite"):
                    snap_path = WORK_DIR / f"{fname}.snap"
                    snap_path.unlink(missing_ok=True)
                    ro_c = sqlite3.connect(f"file:{fp.as_posix()}?mode=ro", uri=True, timeout=60.0)
                    ro_c.execute("VACUUM INTO ?", (str(snap_path),))
                    ro_c.close()
                    with open(snap_path, "rb") as f_in, gzip.open(gz_path, "wb", 4) as f_out:
                        shutil.copyfileobj(f_in, f_out)
                    snap_path.unlink(missing_ok=True)
                else:
                    with open(fp, "rb") as f_in, gzip.open(gz_path, "wb", 5) as f_out:
                        shutil.copyfileobj(f_in, f_out)
                upload_files.append(str(gz_path))
            except Exception as exc:
                log(f"[CHECKPOINT-WARN] Skipping {fname}: {exc}")

        if upload_files:
            subprocess.run(
                ["gh", "release", "upload", RELEASE_TAG, *upload_files, "--clobber"],
                cwd=str(REPO_ROOT),
                check=False,
                timeout=300,
            )
            for uf in upload_files:
                Path(uf).unlink(missing_ok=True)
    finally:
        _CHECKPOINT_LOCK.release()


def trigger_async_checkpoint() -> None:
    t = threading.Thread(target=upload_release_checkpoints, daemon=True)
    t.start()


def main() -> None:
    log("Booting 16-Agent Nonstop Cloud Swarm (20s Fast Live Counter Stream + Read-Only MVCC SQLite + Zero API Keys)...")
    subprocess.run(["git", "config", "user.name", "Cloud MCQ Live Bot"], cwd=str(REPO_ROOT), check=False)
    subprocess.run(["git", "config", "user.email", "ktraghuram2@gmail.com"], cwd=str(REPO_ROOT), check=False)

    prepare_workdir()

    import staging_and_passage_manager as spm

    sweep = spm.audit_existing_dbs_and_move_short_to_staging()
    log(
        f"[AUDIT-GATE] Moved {sweep['moved_to_staging']:,} short -> Staging | "
        f"Verified: {sweep['kept_verified']:,} | Staging Pending: {sweep['staging_pending']:,}"
    )

    build_and_push_live_pages(
        extra_note="[BOOT-OK] 16 Nonstop Cloud Agents Online (20s Live HTML Counter Link Active)!",
        rebuild_full_pages=True,
    )

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
                    time.sleep(3.0)
                else:
                    time.sleep(0.4)
            except Exception as exc:
                swarm_state["last_note"] = f"Swarm retry: {type(exc).__name__}"
                time.sleep(3.0)

    swarm_thread = threading.Thread(target=continuous_8_agent_ai_swarm, daemon=True)
    swarm_thread.start()

    try:
        # 900 ticks * 20s = 300 minutes per chained 24x7 run
        for cycle in range(1, 901):
            time.sleep(20)
            try:
                note = (
                    f"[8-AI-AGENT-SWARM] Wave {swarm_state['waves']}: +{swarm_state['promoted_run']:,} AI-Verified & Promoted this run "
                    f"(Rejected low-quality: {swarm_state['rejected_run']:,}) | {swarm_state['last_note']}"
                )
                rebuild_full = (cycle % 3 == 0)
                status_obj = build_and_push_live_pages(extra_note=note, rebuild_full_pages=rebuild_full)
                m_cnt = status_obj["counts"].get("mcq_bank.sqlite (Master)", 0)
                s_cnt = status_obj["counts"].get("staging_pending_count", 0)
                prom_cnt = status_obj["counts"].get("staging_promoted_count", 0)
                p_cnt = status_obj["counts"].get("passage_mcqs_count", 0)
                log(
                    f"Tick {cycle} ({'FULL' if rebuild_full else 'FAST-20S'}): Verified={m_cnt:,} (+{prom_cnt:,} AI-Promoted) | "
                    f"Staging={s_cnt:,} | Passage Qs={p_cnt:,} | {swarm_state['last_note']}"
                )
            except Exception as tick_err:
                log(f"[TICK-RECOVER] Tick {cycle} push warning: {tick_err}")

            if cycle % 9 == 0:
                trigger_async_checkpoint()

            if web_scraper_proc.poll() is not None:
                web_scraper_proc = subprocess.Popen(
                    [sys.executable, "-u", str(WORK_DIR / "continuous_cloud_web_scraper.py")],
                    cwd=str(WORK_DIR),
                )
    finally:
        stop_swarm.set()
        for proc in (harvester_proc, web_scraper_proc):
            if proc.poll() is None:
                proc.terminate()
        upload_release_checkpoints()

    log("Uploading complete! Self-chaining next 24x7 nonstop cloud run immediately...")
    subprocess.run(["gh", "workflow", "run", "mcq_unlimited_cloud.yml"], cwd=str(REPO_ROOT), check=False)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        tb = traceback.format_exc()
        log(f"[FATAL-RECOVER] {tb}")
        err_file = REPO_ROOT / "mcq_live" / "cloud_last_diag.txt"
        err_file.parent.mkdir(parents=True, exist_ok=True)
        err_file.write_text(tb, encoding="utf-8")
        subprocess.run(["git", "pull", "--rebase", "--autostash", "-X", "theirs", "origin", "main"], cwd=str(REPO_ROOT), check=False)
        subprocess.run(["git", "add", "mcq_live/cloud_last_diag.txt"], cwd=str(REPO_ROOT), check=False)
        subprocess.run(["git", "commit", "-m", "diag(cloud): capture runner exception"], cwd=str(REPO_ROOT), check=False)
        subprocess.run(["git", "push", "origin", "main"], cwd=str(REPO_ROOT), check=False)
        raise
