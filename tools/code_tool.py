"""Tool 1: Code Exposer Tool - write_code_to_file

Writes generated source code into a physical file inside the project directory.
"""

from .base import BaseTool


class WriteCodeToFileTool(BaseTool):
    name: str = "write_code_to_file"
    description: str = (
        "Writes the generated source code into a physical file inside the project directory. "
        "Takes filename (str) and full source code content (str). Returns a confirmation message. "
        "Must output full source code without placeholders."
    )

    def _run(self, filename: str, content: str) -> str:
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully saved {filename} to disk."
        except Exception as exc:  # noqa: BLE001
            return f"Failed to save {filename}: {exc}"
