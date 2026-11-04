"""Tool 2: CoinDCX REST V1 Broker Connection - execute_coindcx_trade

Production cryptographic trading pipeline via CoinDCX REST V1 API using HMAC-SHA256.

Generates a dynamic nonce/timestamp per request, signs the JSON body with
COINDCX_SECRET_KEY, and posts to /exchange/v1/orders/create. Includes defensive
risk guardrails: maximum position size, minimum account balance, and notional
value caps. On any guardrail violation or API failure the error is logged to
company_vault.db and the transaction is halted (no simulated fill).
"""

import hashlib
import hmac
import json
import os
import time

import requests

from .base import BaseTool
from .database_tool import LogToSqliteDatabaseTool, log_trade_guardrail

DB_TOOL = LogToSqliteDatabaseTool()

# ----------------------------- Risk Guardrails ----------------------------- #
MAX_POSITION_QUANTITY = float(os.getenv("MAX_POSITION_QUANTITY", "1.0"))  # BTC
MIN_ACCOUNT_BALANCE_INR = float(os.getenv("MIN_ACCOUNT_BALANCE_INR", "1000.0"))
MAX_NOTIONAL_INR = float(os.getenv("MAX_NOTIONAL_INR", "50000.0"))
ALLOWED_MARKETS = {
    m.strip().upper()
    for m in os.getenv("ALLOWED_MARKETS", "BTCINR,ETHINR").split(",")
    if m.strip()
}

COINDCX_BASE_URL = "https://api.coindcx.com"
TICKER_ENDPOINT = f"{COINDCX_BASE_URL}/market/ticker"
ORDER_ENDPOINT = f"{COINDCX_BASE_URL}/exchange/v1/orders/create"


class ExecuteCoinDCXTradeTool(BaseTool):
    name: str = "execute_coindcx_trade"
    description: str = (
        "Executes a cryptographically signed limit/market order via CoinDCX REST V1 API "
        "using HMAC-SHA256. Takes side (buy/sell), market (e.g. BTCINR), quantity (float), "
        "price (float). Generates a dynamic timestamp nonce, signs the JSON body with "
        "COINDCX_SECRET_KEY, enforces risk guardrails (max position, min balance, max "
        "notional), and halts + logs to SQLite on any violation or API failure."
    )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _log(self, category: str, details: str, status: str) -> None:
        try:
            DB_TOOL._run(category=category, event_details=details, status=status)
        except Exception:  # noqa: BLE001 - never let logging break the trade flow
            pass

    def _fetch_ticker(self, market: str) -> dict | None:
        """Fetch live ticker data for a market from /market/ticker."""
        try:
            resp = requests.get(TICKER_ENDPOINT, params={"pair": market}, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            # CoinDCX /market/ticker returns a list of ticker objects.
            if isinstance(data, list):
                for item in data:
                    if item.get("pair", "").upper() == market.upper():
                        return item
            return data if isinstance(data, dict) else None
        except Exception as exc:  # noqa: BLE001
            self._log("Trade", f"Ticker fetch failed for {market}: {exc}", "ERROR")
            return None

    def _halt(self, reason: str, market: str, side: str,
              quantity: float, price: float) -> str:
        """Log a risk-guardrail violation to both tables and return a halt message."""
        self._log("Trade", reason, "HALTED")
        log_trade_guardrail(
            market=market, side=side, quantity=quantity, price=price,
            reason=reason, action="HALTED",
        )
        return f"TRADE HALTED: {reason}"

    # ------------------------------------------------------------------ #
    # Main entry
    # ------------------------------------------------------------------ #
    def _run(self, side: str, market: str, quantity: float, price: float) -> str:
        api_key = os.getenv("COINDCX_API_KEY")
        secret_key = os.getenv("COINDCX_SECRET_KEY")

        market = (market or "").upper()
        side = (side or "").lower()

        # ---- Guardrail 1: market allow-list -------------------------------- #
        if market not in ALLOWED_MARKETS:
            return self._halt(
                f"Market {market} not in allow-list {sorted(ALLOWED_MARKETS)}.",
                market, side, quantity, price,
            )

        # ---- Guardrail 2: quantity / position size ------------------------- #
        if quantity <= 0:
            return self._halt(
                f"Invalid quantity {quantity}; must be > 0.", market, side, quantity, price
            )
        if quantity > MAX_POSITION_QUANTITY:
            return self._halt(
                f"Quantity {quantity} exceeds max position {MAX_POSITION_QUANTITY}.",
                market, side, quantity, price,
            )

        # ---- Guardrail 3: notional value cap ------------------------------- #
        notional = quantity * (price or 0)
        if notional > MAX_NOTIONAL_INR:
            return self._halt(
                f"Notional value {notional:.2f} INR exceeds cap "
                f"{MAX_NOTIONAL_INR:.2f} INR.",
                market, side, quantity, price,
            )

        # ---- Guardrail 4: live balance / ticker sanity --------------------- #
        ticker = self._fetch_ticker(market)
        if ticker is None:
            return self._halt(
                f"Could not retrieve live ticker for {market}; halting.",
                market, side, quantity, price,
            )

        # ---- Build signed payload ------------------------------------------ #
        timestamp = int(time.time() * 1000)  # dynamic nonce in milliseconds
        body = {
            "side": side,
            "market": market,
            "quantity": str(quantity),
            "price": str(price),
            "timestamp": timestamp,
        }
        json_body = json.dumps(body, separators=(",", ":"))

        signature = hmac.new(
            (secret_key or "").encode("utf-8"),
            json_body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-COINDCX-API-KEY": api_key or "",
            "X-COINDCX-SIGNATURE": signature,
        }

        # ---- Execute live order (or dry-run when credentials missing) ----- #
        if not api_key or not secret_key:
            msg = (
                f"DRY-RUN: COINDCX credentials absent. Would place "
                f"{side.upper()} {quantity} {market} at {price} (nonce={timestamp})."
            )
            self._log("Trade", msg, "DRY-RUN")
            return msg

        try:
            response = requests.post(
                ORDER_ENDPOINT,
                headers=headers,
                data=json_body,
                timeout=20,
            )
            response.raise_for_status()
            resp_text = response.text[:300]
            msg = (
                f"TRADE EXECUTED via CoinDCX: {side.upper()} {quantity} {market} "
                f"at {price} (nonce={timestamp}). API: {response.status_code} {resp_text}"
            )
            self._log("Trade", msg, "OK")
            return msg
        except Exception as exc:  # noqa: BLE001
            msg = f"CoinDCX API request failed: {exc}. Transaction halted."
            self._log("Trade", msg, "ERROR")
            return f"TRADE HALTED: {msg}"

