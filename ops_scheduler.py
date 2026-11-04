#!/usr/bin/env python3
"""
ops_scheduler.py - Headless Autonomous Scheduler (TRD v2.0 Production)

Entry point for unattended / scheduled execution of the multi-agent business
pipeline. Designed to be invoked by:
  * Windows Task Scheduler (via schedule_runner.bat) at 09:30 AM daily
  * Unix cron (see cron_schedule.txt) at 09:30 AM daily

It is completely headless: no interactive input(), no blocking prompts. The
CEO goal is read from the PIPELINE_GOAL environment variable (or a sensible
default) and all operational metrics are locked silently into company_vault.db.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Resolve the project root so the scheduler works regardless of CWD.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import init_db, run_direct_pipeline, run_crewai_pipeline, build_llm  # noqa: E402
from tools.base import CREWAI_AVAILABLE  # noqa: E402

DEFAULT_GOAL = (
    "Build an automated BTC trend analysis app, run a quick backtest, "
    "record a summary shorts video, log everything, and push to Instagram."
)


def main() -> int:
    goal = os.getenv("PIPELINE_GOAL", DEFAULT_GOAL).strip()
    print(f"[ops_scheduler] Headless run started. Goal: {goal}")

    init_db()
    llm = build_llm()

    result = None
    # Prefer native CrewAI Process.sequential when the stack + credentials exist;
    # otherwise fall back to the tool-level direct pipeline (still production-grade).
    if CREWAI_AVAILABLE and llm is not None:
        try:
            result = run_crewai_pipeline(goal, llm)
        except Exception as exc:  # noqa: BLE001
            print(f"[ops_scheduler] CrewAI pipeline raised ({exc}); using direct pipeline.")
            result = run_direct_pipeline(goal, llm)
    else:
        result = run_direct_pipeline(goal, llm)

    print(result if result else "(no result returned)")
    print("[ops_scheduler] Headless run complete. Metrics locked in company_vault.db.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
