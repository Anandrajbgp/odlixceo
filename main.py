#!/usr/bin/env python3
"""
Autonomous Multi-Agent AI Business Pipeline
TRD v2.0 - Project "odlixceo"

A virtual digital company orchestrated by CrewAI. A human operator (CEO) supplies a
high-level goal and a team of specialized AI agents executes a sequential pipeline:

    Supervisor -> Dev Wizard -> Quant Trader -> Video & Creative Director ->
    Database & P&L Tracker -> Content Viralist -> Supervisor (final compliance report)

Custom CrewAI tools:
    write_code_to_file | execute_coindcx_trade | programmatic_video_generator |
    log_to_sqlite_database | publish_to_instagram

Usage:
    python main.py
"""

import os
import sqlite3

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# CrewAI import (graceful degradation when the langchain/CrewAI stack cannot
# be imported in the current Python environment)
# ---------------------------------------------------------------------------
CREWAI_AVAILABLE = False
try:
    from crewai import Agent, Task, Crew, Process  # noqa: F401
    CREWAI_AVAILABLE = True
except Exception as exc:  # noqa: BLE001
    print(f"[info] CrewAI stack unavailable ({exc}); running direct-execution fallback.")

from tools.base import BaseTool, CREWAI_AVAILABLE as TOOLS_HAS_CREWAI  # noqa: F401
from tools.code_tool import WriteCodeToFileTool
from tools.trading_tool import ExecuteCoinDCXTradeTool
from tools.video_tool import ProgrammaticVideoGeneratorTool
from tools.database_tool import LogToSqliteDatabaseTool
from tools.instagram_tool import PublishToInstagramTool

DB_PATH = "company_vault.db"

TOOLS = {
    "code": WriteCodeToFileTool(),
    "trade": ExecuteCoinDCXTradeTool(),
    "video": ProgrammaticVideoGeneratorTool(),
    "db": LogToSqliteDatabaseTool(),
    "social": PublishToInstagramTool(),
}


def init_db():
    """Create the SQLite vault table if it does not exist yet."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            category TEXT,
            details TEXT,
            status TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def db_log(category: str, details: str, status: str = "OK") -> str:
    """Write one row into company_vault.db via the DB tool."""
    return TOOLS["db"]._run(category=category, event_details=details, status=status)


def build_llm():
    """Initialise the Google Gemini 1.5 Flash LLM if credentials are present."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash", google_api_key=api_key, temperature=0.7
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] Gemini LLM unavailable ({exc}); proceeding without LLM reasoning.")
        return None


def llm_text(llm, prompt: str, fallback: str) -> str:
    """Ask the LLM for text, falling back to a static string when unavailable."""
    if llm is None:
        return fallback
    try:
        message = llm.invoke(prompt)
        return getattr(message, "content", str(message))
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] LLM call failed ({exc}); using fallback text.")
        return fallback


# ===========================================================================
# CrewAI sequential pipeline (Process.sequential)
# ===========================================================================
def run_crewai_pipeline(goal: str, llm):
    code_tool = TOOLS["code"]
    trade_tool = TOOLS["trade"]
    video_tool = TOOLS["video"]
    db_tool = TOOLS["db"]
    social_tool = TOOLS["social"]

    supervisor = Agent(
        role="Supervisor / Orchestrator",
        goal=(
            "Break down the CEO's high-level goal into actionable sequential tasks, "
            "assign them to specialised agents, review outputs and compile the final "
            "Business Compliance Report."
        ),
        backstory="Experienced program manager who coordinates a virtual AI company.",
        llm=llm,
        verbose=True,
    )
    dev = Agent(
        role="Dev Wizard - Senior Full-Stack & Bot Developer",
        goal="Write clean, production-ready, bug-free Python code based on the assignment.",
        backstory="Expert software engineer who ships complete source files with no placeholders.",
        tools=[code_tool],
        llm=llm,
        verbose=True,
    )
    trader = Agent(
        role="Quant Trader - Crypto Trading Specialist",
        goal="Connect to exchange APIs, analyse trends and execute automated buy/sell orders.",
        backstory="Crypto trading specialist connected to CoinDCX via HMAC-SHA256 signed REST calls.",
        tools=[trade_tool],
        llm=llm,
        verbose=True,
    )
    video = Agent(
        role="Video & Creative Director",
        goal=(
            "Compile programmatic media clips, overlay automated captions and output "
            "finished short-form MP4 videos for social media distribution."
        ),
        backstory="Automated video editor and producer for social media reels/shorts.",
        tools=[video_tool],
        llm=llm,
        verbose=True,
    )
    dba = Agent(
        role="Database & P&L Tracker",
        goal=(
            "Maintain the centralized SQLite database logging code deployments, live trade "
            "activities, financial P&L metrics and social media posting timestamps."
        ),
        backstory="Data administrator and financial compliance officer.",
        tools=[db_tool],
        llm=llm,
        verbose=True,
    )
    marketer = Agent(
        role="Content Viralist - Social Media Growth Expert",
        goal=(
            "Track trending topics, write viral copy with optimised hashtags, consume the "
            "video asset from the Video agent and publish marketing posts to Instagram."
        ),
        backstory="Social media growth expert who maximises reach and engagement.",
        tools=[social_tool],
        llm=llm,
        verbose=True,
    )

    t_plan = Task(
        description=f"Break down this CEO goal into sequential steps: {goal}",
        agent=supervisor,
        expected_output="A numbered execution plan assigning work to each specialised agent.",
    )
    t_dev = Task(
        description=(
            f"Write the backend code logic for: {goal}. Save the full source file using "
            "write_code_to_file. Output complete source code without placeholders."
        ),
        agent=dev,
        context=[t_plan],
        expected_output="A saved Python source file with complete, production-ready code.",
    )
    t_trade = Task(
        description=(
            f"Scan token asset metrics and generate P&L projections for: {goal}. "
            "Use execute_coindcx_trade to place the order."
        ),
        agent=trader,
        context=[t_dev],
        expected_output="A trade summary with executed order and P&L projection.",
    )
    t_video = Task(
        description=(
            f"Consume the trading report and compile a captioned MP4 short video for: {goal}. "
            "Use programmatic_video_generator."
        ),
        agent=video,
        context=[t_trade],
        expected_output="A rendered MP4 video file path.",
    )
    t_db = Task(
        description=(
            "Log every code deployment, trade metric, video path and timestamp into "
            "company_vault.db using log_to_sqlite_database."
        ),
        agent=dba,
        context=[t_dev, t_trade, t_video],
        expected_output="Database rows inserted into system_logs.",
    )
    t_social = Task(
        description=(
            f"Publish the MP4 video to Instagram as a reel with a viral caption and "
            f"hashtags for: {goal}. Use publish_to_instagram."
        ),
        agent=marketer,
        context=[t_video],
        expected_output="Instagram publish confirmation.",
    )
    t_report = Task(
        description=(
            "Compile the final Business Compliance Report from the database state and "
            "total execution metrics. Print it to the operator."
        ),
        agent=supervisor,
        context=[t_db, t_social],
        expected_output="Final Business Compliance Report printed to the operator.",
    )

    crew = Crew(
        agents=[supervisor, dev, trader, video, dba, marketer],
        tasks=[t_plan, t_dev, t_trade, t_video, t_db, t_social, t_report],
        process=Process.sequential,
        manager_llm=llm,
        verbose=True,
    )
    return crew.kickoff(inputs={"goal": goal})


# ===========================================================================
# Direct-execution fallback pipeline (always works; exercises every tool)
# ===========================================================================
FALLBACK_SOURCE_CODE = '''#!/usr/bin/env python3
"""
Automated BTC Trend Analysis App
Generated by the Dev Wizard (Autonomous Multi-Agent AI Business Pipeline, TRD v2.0).
"""
import json
import time


def fetch_btc_price() -> float:
    """Fetch the latest BTC price from the exchange (placeholder for live API)."""
    # In production, call the CoinDCX public ticker endpoint here.
    return 65420.50


def compute_trend(prices: list) -> str:
    """Compute a simple trend from a list of historical prices."""
    if len(prices) < 2:
        return "NEUTRAL"
    return "UPTREND" if prices[-1] > prices[0] else "DOWNTREND"


def generate_signal(trend: str) -> str:
    """Map a trend to a trading signal."""
    return {"UPTREND": "BUY", "DOWNTREND": "SELL"}.get(trend, "HOLD")


def main() -> None:
    price = fetch_btc_price()
    history = [64000.0, 64800.0, price]
    trend = compute_trend(history)
    signal = generate_signal(trend)
    print(json.dumps({"btc_price": price, "trend": trend, "signal": signal}, indent=2))


if __name__ == "__main__":
    main()
'''


def run_direct_pipeline(goal: str, llm):
    print("\n=== Running direct-execution pipeline (tool-level fallback) ===\n")

    # 1. Supervisor / Orchestrator - plan
    plan = llm_text(
        llm,
        (
            f"Break down this CEO goal into sequential steps assigned to Dev, Trader, "
            f"Video, DB and Marketer agents: {goal}"
        ),
        (
            f"PLAN for '{goal}':\n"
            "1. Dev Wizard writes backend code and saves a .py file.\n"
            "2. Quant Trader scans BTC metrics and executes a simulated trade.\n"
            "3. Video Director compiles a captioned MP4 short.\n"
            "4. DB Tracker logs code, trade, video and social events to SQLite.\n"
            "5. Content Viralist publishes the reel to Instagram.\n"
            "6. Supervisor compiles the Business Compliance Report."
        ),
    )
    print(f"[Supervisor] Plan:\n{plan}\n")
    db_log("Supervisor", f"Plan created for goal: {goal}", "OK")

    # 2. Dev Wizard - write code
    source_code = llm_text(
        llm,
        (
            "Write a complete, production-ready Python script for an automated BTC trend "
            "analysis app (fetch price, compute trend, emit buy/sell signal). Output ONLY "
            "the full source code, no placeholders, no markdown fences."
        ),
        FALLBACK_SOURCE_CODE,
    )
    code_result = TOOLS["code"]._run(filename="btc_trend_analysis_app.py", content=source_code)
    print(f"[Dev] {code_result}\n")
    db_log("Code", "btc_trend_analysis_app.py saved", code_result)

    # 3. Quant Trader - execute trade
    trade_result = TOOLS["trade"]._run(side="buy", market="BTCINR", quantity=0.001, price=65420.50)
    print(f"[Trader] {trade_result}\n")
    db_log("Trade", trade_result, "OK")

    # 4. Video & Creative Director - render MP4
    script = (
        f"BTC Trend Summary. Goal: {goal}. Trading desk output: {trade_result}. "
        "Automated short-form video for social distribution."
    )
    video_result = TOOLS["video"]._run(script_text=script, output_video_name="btc_trend_summary_shorts.mp4")
    print(f"[Video] {video_result}\n")
    db_log("Video", video_result, "OK")

    # 5. Content Viralist - publish to Instagram
    caption = (
        f"BTC trend update! {goal}. Automated by our multi-agent AI pipeline. "
        "#Bitcoin #Crypto #Trading #AI #Automation #FinTech"
    )
    social_result = TOOLS["social"]._run(video_path="btc_trend_summary_shorts.mp4", caption=caption)
    print(f"[Marketer] {social_result}\n")
    db_log("Social", social_result, "OK")

    # 6. Supervisor - compliance report + database state
    print_database_state()
    report = (
        "=== FINAL BUSINESS COMPLIANCE REPORT ===\n"
        f"Goal: {goal}\n"
        "Execution mode: direct-execution fallback\n"
        "Artifacts: btc_trend_analysis_app.py, btc_trend_summary_shorts.mp4\n"
        "All events logged to company_vault.db.\n"
        "=== END OF REPORT ==="
    )
    print(f"\n{report}\n")
    db_log("Report", "Business Compliance Report compiled", "OK")
    return report


def print_database_state():
    """Print the current contents of company_vault.db (reporting step)."""
    print("\n=== Database State (company_vault.db) ===")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM system_logs")
    count = cursor.fetchone()[0]
    cursor.execute(
        "SELECT id, timestamp, category, details, status "
        "FROM system_logs ORDER BY id"
    )
    rows = cursor.fetchall()
    conn.close()
    print(f"Total log entries: {count}")
    for row_id, ts, category, details, status in rows:
        print(f"  [{row_id}] {ts} | {category:10} | {status:4} | {details[:90]}")
    print("========================================\n")


def main():
    init_db()
    llm = build_llm()

    default_goal = (
        "Build an automated BTC trend analysis app, run a quick backtest, "
        "record a summary shorts video, log everything, and push to Instagram."
    )
    env_goal = os.getenv("PIPELINE_GOAL", "").strip()
    if env_goal:
        # Headless / scheduled mode: never block on interactive input().
        goal = env_goal
    else:
        goal = input("Enter CEO high-level goal: ").strip() or default_goal
    print(f"\nCEO Goal: {goal}\n")

    result = None
    if CREWAI_AVAILABLE and llm is not None:
        try:
            result = run_crewai_pipeline(goal, llm)
        except Exception as exc:  # noqa: BLE001
            print(f"[info] CrewAI pipeline raised ({exc}); falling back to direct execution.")
            result = run_direct_pipeline(goal, llm)
    else:
        result = run_direct_pipeline(goal, llm)

    if result is None:
        result = "(no result returned)"
    print("\n=== PIPELINE COMPLETE ===")
    print(result)


if __name__ == "__main__":
    main()



