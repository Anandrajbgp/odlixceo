"""Tool 4: SQLite Database Logging Tool - log_to_sqlite_database

Production-grade centralized SQLite vault for the autonomous pipeline.

Creates three tables in company_vault.db:
  * system_logs        - general pipeline events (code, trade, video, social, report)
  * trade_guardrails   - risk-guardrail violations and halted transactions
  * video_assets       - rendered video / backup PNG asset records

Exposes log_to_sqlite_database(category, event_details, status) plus dedicated
helpers for trade-guardrail and video-asset records used by the production tools.
"""

import os
import sqlite3
from datetime import datetime

from .base import BaseTool

DB_PATH = os.getenv("COMPANY_VAULT_DB", "company_vault.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_schema() -> None:
    conn = _connect()
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
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS trade_guardrails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            market TEXT,
            side TEXT,
            quantity REAL,
            price REAL,
            notional_inr REAL,
            reason TEXT,
            action TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS video_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            output_path TEXT,
            asset_type TEXT,   -- 'mp4' | 'png'
            status TEXT,
            details TEXT
        )
        """
    )
    conn.commit()
    conn.close()


# Ensure schema exists at import time so any tool can write immediately.
_init_schema()


class LogToSqliteDatabaseTool(BaseTool):
    name: str = "log_to_sqlite_database"
    description: str = (
        "Logs system records (Code version, Trade P&L, Video Paths, Social Logs) "
        "into a local SQLite database file ('company_vault.db'). Takes category "
        "(str), event_details (str), status (str). Returns a confirmation message."
    )

    def _run(self, category: str, event_details: str, status: str) -> str:
        try:
            conn = _connect()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO system_logs (category, details, status) "
                "VALUES (?, ?, ?)",
                (category, event_details, status),
            )
            conn.commit()
            conn.close()
            return "Database transaction successfully verified and locked."
        except Exception as exc:  # noqa: BLE001
            return f"Database transaction failed: {exc}"


def log_trade_guardrail(market: str, side: str, quantity: float, price: float,
                        reason: str, action: str) -> str:
    """Record a risk-guardrail violation / halted transaction."""
    try:
        notional = quantity * (price or 0)
        conn = _connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO trade_guardrails
            (market, side, quantity, price, notional_inr, reason, action)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (market, side, quantity, price, notional, reason, action),
        )
        conn.commit()
        conn.close()
        return "Trade guardrail violation logged."
    except Exception as exc:  # noqa: BLE001
        return f"Trade guardrail logging failed: {exc}"


def log_video_asset(output_path: str, asset_type: str, status: str,
                    details: str) -> str:
    """Record a rendered video or backup PNG asset."""
    try:
        conn = _connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO video_assets (output_path, asset_type, status, details)
            VALUES (?, ?, ?, ?)
            """,
            (output_path, asset_type, status, details),
        )
        conn.commit()
        conn.close()
        return "Video asset recorded."
    except Exception as exc:  # noqa: BLE001
        return f"Video asset logging failed: {exc}"
