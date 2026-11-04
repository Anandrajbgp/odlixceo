"""Safe BaseTool import.

Prefers CrewAI's BaseTool when the langchain/CrewAI stack is importable.
Otherwise provides a minimal standalone fallback so the tools can still be
instantiated and executed directly (used by main.py's fallback pipeline).
"""

try:
    from crewai.tools import BaseTool as _CrewBaseTool  # type: ignore

    class BaseTool(_CrewBaseTool):
        """CrewAI-compatible tool base."""

    HAS_CREWAI = True
except Exception:  # noqa: BLE001 - langchain/CrewAI not installable in this env

    class BaseTool:
        """Minimal standalone stand-in for CrewAI's BaseTool."""

        name: str = ""
        description: str = ""

        def _run(self, *args, **kwargs):  # noqa: D401
            raise NotImplementedError("CrewAI is not available in this environment")

    HAS_CREWAI = False

# Alias imported by ops_scheduler.py for the production scheduler branch.
CREWAI_AVAILABLE = HAS_CREWAI


__all__ = ["BaseTool", "HAS_CREWAI", "CREWAI_AVAILABLE"]
