#!/usr/bin/env python3
"""
wrapper.py - odlixceo continuous runner for Railway (worker-style deployment).

Runs ops_scheduler.py once immediately, then repeats every PIPELINE_INTERVAL_SECONDS
(default 24 hours = 86400s). Keeps the process alive so Railway doesn't kill the
container after a single run.

Environment variables:
  PIPELINE_INTERVAL_SECONDS  - seconds between runs (default: 86400)
  PIPELINE_GOAL              - CEO high-level goal for the pipeline
  GEMINI_API_KEY, COINDCX_API_KEY, COINDCX_SECRET_KEY,
  META_ACCESS_TOKEN, META_PAGE_ID, etc. (set these in Railway Variables)
"""

import os
import sys
import time
import subprocess
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

INTERVAL_SECONDS = int(os.getenv("PIPELINE_INTERVAL_SECONDS", "86400"))  # 24 hours


def run_pipeline() -> int:
    """Run ops_scheduler.py once and return its exit code."""
    print(f"\n[{datetime.now().isoformat()}] Starting pipeline run...")
    print(f"[{datetime.now().isoformat()}] Working directory: {PROJECT_ROOT}")
    result = subprocess.run([sys.executable, "ops_scheduler.py"], cwd=PROJECT_ROOT)
    print(f"[{datetime.now().isoformat()}] Pipeline finished with exit code {result.returncode}\n")
    return result.returncode


def main() -> None:
    print("[wrapper] odlixceo continuous runner started.")
    print(f"[wrapper] Interval: {INTERVAL_SECONDS} seconds ({INTERVAL_SECONDS / 3600:.1f} hours)")

    # Run once immediately on startup
    run_pipeline()

    # Then loop forever
    while True:
        print(f"[wrapper] Sleeping for {INTERVAL_SECONDS} seconds until next run...")
        time.sleep(INTERVAL_SECONDS)
        run_pipeline()


if __name__ == "__main__":
    main()