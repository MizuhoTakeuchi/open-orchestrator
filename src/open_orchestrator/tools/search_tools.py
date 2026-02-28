"""Search tools: glob and grep."""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path

from open_orchestrator.tools import Tool, register_tool


def glob(pattern: str, path: str = ".") -> str:
    """Find files matching a glob pattern."""
    base_path = Path(path).resolve()
    if not base_path.exists():
        return f"Error: Path does not exist: {path}"

    try:
        matches = sorted(
            str(p.relative_to(base_path))
            for p in base_path.rglob(pattern.lstrip("/"))
            if p.is_file()
        )
    except Exception as e:
        return f"Error during glob: {e}"

    if not matches:
        return f"No files matching '{pattern}' in {path}"

    return "\n".join(matches)


def grep(
    pattern: str,
    path: str = ".",
    file_pattern: str | None = None,
    case_sensitive: bool = True,
    context: int = 0,
) -> str:
    """Search for a pattern in files."""
    base_path = Path(path).resolve()
    if not base_path.exists():
        return f"Error: Path does not exist: {path}"

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        compiled = re.compile(pattern, flags)
    except re.error as e:
        return f"Error: Invalid regex pattern: {e}"

    results = []
    error_files = []

    if base_path.is_file():
        files_to_search = [base_path]
    else:
        files_to_search = [p for p in base_path.rglob("*") if p.is_file()]
        if file_pattern:
            files_to_search = [
                p for p in files_to_search
                if fnmatch.fnmatch(p.name, file_pattern)
            ]

    for file_path in sorted(files_to_search):
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            error_files.append(str(file_path))
            continue

        lines = text.splitlines()
        matching_lines = []

        for i, line in enumerate(lines, start=1):
            if compiled.search(line):
                start = max(0, i - 1 - context)
                end = min(len(lines), i + context)

                for j in range(start, end):
                    line_num = j + 1
                    prefix = ">" if line_num == i else " "
                    matching_lines.append(f"  {prefix} {line_num}: {lines[j]}")

                if context > 0 and matching_lines:
                    matching_lines.append("  --")

        if matching_lines:
            rel_path = file_path.relative_to(base_path) if base_path.is_dir() else file_path
            results.append(f"{rel_path}:\n" + "\n".join(matching_lines))

    if not results:
        msg = f"No matches for '{pattern}'"
        if file_pattern:
            msg += f" in files matching '{file_pattern}'"
        return msg

    output = "\n\n".join(results)
    if error_files:
        output += f"\n\n[Could not read {len(error_files)} file(s)]"
    return output


def register_search_tools() -> None:
    """Register all search tools into the global registry."""
    register_tool(Tool(
        name="glob",
        description=(
            "Find files matching a glob pattern. "
            "Supports wildcards: * (any chars in name), ** (any path), ? (single char). "
            "Examples: '**/*.py', 'src/**/*.ts', '*.json'"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match files against",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: current directory)",
                    "default": ".",
                },
            },
            "required": ["pattern"],
        },
        handler=glob,
        requires_permission=False,
    ))

    register_tool(Tool(
        name="grep",
        description=(
            "Search for a regex pattern in files. "
            "Returns matching lines with file paths and line numbers."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regular expression pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "File or directory to search in (default: current directory)",
                    "default": ".",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Filter files by name pattern (e.g., '*.py', '*.ts')",
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "Whether search is case sensitive (default: true)",
                    "default": True,
                },
                "context": {
                    "type": "integer",
                    "description": "Number of lines of context to show around matches (default: 0)",
                    "default": 0,
                },
            },
            "required": ["pattern"],
        },
        handler=grep,
        requires_permission=False,
    ))
