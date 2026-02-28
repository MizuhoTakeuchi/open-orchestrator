"""File operation tools: read_file, write_file, edit_file."""

from __future__ import annotations

from pathlib import Path

from open_orchestrator.tools import Tool, register_tool


def read_file(path: str, offset: int = 1, limit: int | None = None) -> str:
    """Read a file and return its contents with line numbers."""
    file_path = Path(path)
    if not file_path.exists():
        return f"Error: File not found: {path}"
    if not file_path.is_file():
        return f"Error: Not a file: {path}"

    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:
        return f"Error reading file: {e}"

    # Apply offset and limit (1-indexed)
    start = max(0, offset - 1)
    end = len(lines) if limit is None else start + limit
    selected = lines[start:end]

    if not selected:
        return f"(File is empty or offset {offset} is beyond end of file)"

    result_lines = []
    for i, line in enumerate(selected, start=start + 1):
        result_lines.append(f"{i:6d}\t{line}")

    total = len(lines)
    header = f"File: {path} ({total} lines total)"
    if start > 0 or end < total:
        header += f" [showing lines {start+1}-{min(end, total)}]"

    return header + "\n" + "\n".join(result_lines)


def write_file(path: str, content: str) -> str:
    """Create or overwrite a file with the given content."""
    file_path = Path(path)
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        return f"Successfully wrote {lines} lines to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def edit_file(path: str, old_string: str, new_string: str) -> str:
    """Edit a file by replacing old_string with new_string (must be unique)."""
    file_path = Path(path)
    if not file_path.exists():
        return f"Error: File not found: {path}"

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Error reading file: {e}"

    count = content.count(old_string)
    if count == 0:
        return f"Error: String not found in {path}"
    if count > 1:
        return (
            f"Error: String found {count} times in {path}. "
            "Provide more context to make it unique."
        )

    new_content = content.replace(old_string, new_string, 1)
    try:
        file_path.write_text(new_content, encoding="utf-8")
        return f"Successfully edited {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def register_file_tools() -> None:
    """Register all file tools into the global registry."""
    register_tool(Tool(
        name="read_file",
        description=(
            "Read a file and return its contents with line numbers. "
            "Use offset and limit to read specific sections of large files."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-indexed, default: 1)",
                    "default": 1,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (default: all)",
                },
            },
            "required": ["path"],
        },
        handler=read_file,
        requires_permission=False,
    ))

    register_tool(Tool(
        name="write_file",
        description="Create or overwrite a file with the given content.",
        parameters_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
        handler=write_file,
        requires_permission=True,
    ))

    register_tool(Tool(
        name="edit_file",
        description=(
            "Edit a file by replacing a unique string with a new string. "
            "The old_string must appear exactly once in the file. "
            "Include sufficient surrounding context to make it unique."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to edit",
                },
                "old_string": {
                    "type": "string",
                    "description": "The unique string to find and replace",
                },
                "new_string": {
                    "type": "string",
                    "description": "The string to replace it with",
                },
            },
            "required": ["path", "old_string", "new_string"],
        },
        handler=edit_file,
        requires_permission=True,
    ))
