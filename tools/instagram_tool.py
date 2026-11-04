"""Tool 5: Meta Graph API Publishing Tool - publish_to_instagram

Production asynchronous video/reel publisher for the Meta Graph API.

Implements the three-step Instagram Reels publishing flow:
  Step A: POST /{page_id}/media with media_type=REELS -> creation_id
  Step B: Poll /{creation_id}?fields=status_code until FINISHED (or ERROR)
  Step C: POST /{page_id}/media_publish with the verified creation_id

Falls back to a simulated confirmation when META_ACCESS_TOKEN / META_PAGE_ID
are absent (development / offline mode).
"""

import os
import time

import requests

from .base import BaseTool
from .database_tool import LogToSqliteDatabaseTool

DB_TOOL = LogToSqliteDatabaseTool()

GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v18.0")
POLL_INTERVAL_SEC = int(os.getenv("META_POLL_INTERVAL_SEC", "5"))
POLL_MAX_ATTEMPTS = int(os.getenv("META_POLL_MAX_ATTEMPTS", "24"))  # ~2 minutes


class PublishToInstagramTool(BaseTool):
    name: str = "publish_to_instagram"
    description: str = (
        "Publishes completed video assets as Instagram Reels via the Meta Graph API "
        "using an asynchronous create -> poll -> publish flow. Takes video_path (str) "
        "and caption (str). Returns a live broadcast confirmation (simulated when META "
        "credentials are absent)."
    )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _log(self, category: str, details: str, status: str) -> None:
        try:
            DB_TOOL._run(category=category, event_details=details, status=status)
        except Exception:  # noqa: BLE001
            pass

    def _graph_url(self, path: str) -> str:
        return f"https://graph.facebook.com/{GRAPH_VERSION}/{path}"

    # ------------------------------------------------------------------ #
    # Main entry
    # ------------------------------------------------------------------ #
    def _run(self, video_path: str, caption: str) -> str:
        access_token = os.getenv("META_ACCESS_TOKEN")
        page_id = os.getenv("META_PAGE_ID")

        if not access_token or not page_id:
            msg = (
                f"DRY-RUN: META credentials absent. Simulated Reel publish: "
                f"{video_path} | Caption: {(caption or '')[:80]}..."
            )
            self._log("Social", msg, "DRY-RUN")
            return msg

        caption = caption or ""

        try:
            # ---- Step A: Create media container (media_type=REELS) --------- #
            container_url = self._graph_url(f"{page_id}/media")
            container_payload = {
                "video_url": video_path,
                "media_type": "REELS",
                "caption": caption,
                "access_token": access_token,
            }
            container_resp = requests.post(
                container_url, data=container_payload, timeout=30
            )
            container_resp.raise_for_status()
            container_data = container_resp.json()
            creation_id = container_data.get("id")
            if not creation_id:
                msg = f"Container creation returned no id: {container_data}"
                self._log("Social", msg, "ERROR")
                return f"PUBLISH FAILED: {msg}"

            self._log("Social", f"Reel container created: {creation_id}", "OK")

            # ---- Step B: Poll status until FINISHED ----------------------- #
            status_url = self._graph_url(creation_id)
            final_status = None
            for attempt in range(1, POLL_MAX_ATTEMPTS + 1):
                time.sleep(POLL_INTERVAL_SEC)
                status_resp = requests.get(
                    status_url,
                    params={"fields": "status_code", "access_token": access_token},
                    timeout=20,
                )
                status_resp.raise_for_status()
                status_data = status_resp.json()
                final_status = status_data.get("status_code")
                if final_status == "FINISHED":
                    break
                if final_status in ("ERROR", "EXPIRED", "DELETED"):
                    msg = f"Container {creation_id} reached terminal status: {final_status}"
                    self._log("Social", msg, "ERROR")
                    return f"PUBLISH FAILED: {msg}"
                # still IN_PROGRESS -> continue polling

            if final_status != "FINISHED":
                msg = (
                    f"Container {creation_id} did not finish within "
                    f"{POLL_MAX_ATTEMPTS} polls (last status: {final_status})."
                )
                self._log("Social", msg, "ERROR")
                return f"PUBLISH FAILED: {msg}"

            # ---- Step C: Publish the verified container ------------------- #
            publish_url = self._graph_url(f"{page_id}/media_publish")
            publish_payload = {
                "creation_id": creation_id,
                "access_token": access_token,
            }
            publish_resp = requests.post(
                publish_url, data=publish_payload, timeout=30
            )
            publish_resp.raise_for_status()
            publish_data = publish_resp.json()

            msg = (
                f"REEL PUBLISHED LIVE: {video_path} | creation_id={creation_id} "
                f"| Meta: {publish_data}"
            )
            self._log("Social", msg, "OK")
            return msg

        except Exception as exc:  # noqa: BLE001
            msg = f"Meta Graph API publish failed: {exc}."
            self._log("Social", msg, "ERROR")
            return f"PUBLISH FAILED: {msg}"
