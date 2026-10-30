# -*- coding: utf-8 -*-
r"""
Google AI Ultra Subscription Multi-Agent Cloud Bridge (`ultra_cloud_multi_agent_bridge.py`)
===========================================================================================
Uses your signed-in Google AI Ultra subscription (`agy` CLI — ZERO API keys!) to run
6 to 8 concurrent Ultra AI Agents (`gemini-3.8-flash-high`, `gemini-3.8-flash-medium`,
`gemini-3.8-flash-low`, `gemini-4-argon-low`, `gpt-oss-120b-medium`, `claude-sonnet-5-5-low`)
against `db_staging_queue.sqlite` — either locally synced with GitHub Cloud Release
`v1.0-mcq-live-db` OR automatically when this machine is registered as a GitHub Actions
`self-hosted` cloud runner!
"""

import staging_and_passage_manager as spm


def main() -> None:
    print("[ULTRA-MULTI-AGENT-SWARM] Launching 6 Parallel Google AI Ultra Agents (Zero API Keys)...")
    res = spm.run_ai_staging_enrichment_batch(
        batch_size=4,
        max_batches=25,
        num_agents=6,
        prefer_ultra_agy=True,
    )
    print(f"[ULTRA-MULTI-AGENT-SWARM] Completed: +{res['promoted']} Promoted | {res['rejected']} Rejected | {res['note']}")


if __name__ == "__main__":
    main()
