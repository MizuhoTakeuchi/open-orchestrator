"""Tests for tool implementations."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from open_orchestrator.tools.bash_tool import bash
from open_orchestrator.tools.file_tools import edit_file, read_file, write_file
from open_orchestrator.tools.search_tools import glob, grep


class TestReadFile:
    def test_read_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\nline3\n")
        result = read_file(str(f))
        assert "line1" in result
        assert "line2" in result
        assert "1\t" in result  # line numbers

    def test_read_nonexistent_file(self) -> None:
        result = read_file("/nonexistent/path/file.txt")
        assert "Error" in result

    def test_read_with_offset_and_limit(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\nline3\nline4\nline5\n")
        result = read_file(str(f), offset=2, limit=2)
        assert "line2" in result
        assert "line3" in result
        assert "line1" not in result
        assert "line4" not in result

    def test_read_directory_returns_error(self, tmp_path: Path) -> None:
        result = read_file(str(tmp_path))
        assert "Error" in result


class TestWriteFile:
    def test_write_new_file(self, tmp_path: Path) -> None:
        path = str(tmp_path / "new_file.txt")
        result = write_file(path, "Hello, world!\n")
        assert "Successfully" in result
        assert Path(path).read_text() == "Hello, world!\n"

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = str(tmp_path / "a" / "b" / "c.txt")
        result = write_file(path, "content")
        assert "Successfully" in result
        assert Path(path).exists()

    def test_write_overwrites_existing(self, tmp_path: Path) -> None:
        f = tmp_path / "existing.txt"
        f.write_text("old content")
        result = write_file(str(f), "new content")
        assert "Successfully" in result
        assert f.read_text() == "new content"


class TestEditFile:
    def test_edit_unique_string(self, tmp_path: Path) -> None:
        f = tmp_path / "edit_me.txt"
        f.write_text("Hello world\nFoo bar\n")
        result = edit_file(str(f), "Hello world", "Goodbye world")
        assert "Successfully" in result
        assert f.read_text() == "Goodbye world\nFoo bar\n"

    def test_edit_nonexistent_file(self) -> None:
        result = edit_file("/nonexistent/file.txt", "old", "new")
        assert "Error" in result

    def test_edit_string_not_found(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("Hello world\n")
        result = edit_file(str(f), "not present", "replacement")
        assert "Error" in result
        assert "not found" in result

    def test_edit_ambiguous_string(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("foo bar\nfoo baz\n")
        result = edit_file(str(f), "foo", "qux")
        assert "Error" in result
        assert "2" in result  # found 2 times


class TestBashTool:
    @pytest.mark.asyncio
    async def test_run_simple_command(self) -> None:
        result = await bash("echo hello")
        assert "hello" in result

    @pytest.mark.asyncio
    async def test_run_failing_command(self) -> None:
        result = await bash("false")
        assert "Exit code" in result

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        result = await bash("sleep 10", timeout=1)
        assert "timed out" in result.lower()

    @pytest.mark.asyncio
    async def test_stderr_captured(self) -> None:
        result = await bash("echo error >&2")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_cwd(self, tmp_path: Path) -> None:
        result = await bash("pwd", cwd=str(tmp_path))
        assert str(tmp_path) in result


class TestGlob:
    def test_find_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").touch()
        (tmp_path / "b.py").touch()
        (tmp_path / "c.txt").touch()
        result = glob("*.py", str(tmp_path))
        assert "a.py" in result
        assert "b.py" in result
        assert "c.txt" not in result

    def test_no_matches(self, tmp_path: Path) -> None:
        result = glob("*.rs", str(tmp_path))
        assert "No files" in result

    def test_nonexistent_path(self) -> None:
        result = glob("*.py", "/nonexistent/path")
        assert "Error" in result

    def test_recursive_glob(self, tmp_path: Path) -> None:
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "deep.py").touch()
        result = glob("**/*.py", str(tmp_path))
        assert "deep.py" in result


class TestGrep:
    def test_find_pattern(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("hello world\nfoo bar\nbaz qux\n")
        result = grep("hello", str(f))
        assert "hello" in result
        assert "foo bar" not in result

    def test_no_matches(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("hello world\n")
        result = grep("xyz", str(f))
        assert "No matches" in result

    def test_case_insensitive(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("Hello World\n")
        result = grep("hello", str(f), case_sensitive=False)
        assert "Hello" in result

    def test_file_pattern_filter(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("import foo\n")
        (tmp_path / "b.txt").write_text("import bar\n")
        result = grep("import", str(tmp_path), file_pattern="*.py")
        assert "a.py" in result
        assert "b.txt" not in result

    def test_context_lines(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("before\nmatch here\nafter\n")
        result = grep("match", str(f), context=1)
        assert "before" in result
        assert "after" in result
