"""Gate: comments and docstrings must be English and at most MAX_LINES lines long."""

from __future__ import annotations

import ast
import io
import sys
import tokenize
import unicodedata
from pathlib import Path

MAX_LINES = 2
# Directive comments consumed by tools; their wording is not ours to police.
_DIRECTIVES = ("noqa", "type:", "fmt:", "pragma", "pylint:", "mypy:", "ruff:", "nosec")


def _foreign_letters(text: str) -> str:
    """Return non-ASCII letters found in text (emoji and symbols are allowed)."""
    return "".join(
        ch for ch in text if ch.isalpha() and ord(ch) > 127 and unicodedata.category(ch)[0] == "L"
    )


def _check_comments(source: str, path: str) -> list[str]:
    errors: list[str] = []
    run_start = 0
    run_len = 0
    prev_line = -10

    def flush() -> None:
        if run_len > MAX_LINES:
            errors.append(f"{path}:{run_start}: comment block is {run_len} lines (max {MAX_LINES})")

    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    lines = source.splitlines()
    for tok in tokens:
        if tok.type != tokenize.COMMENT:
            continue
        line_no = tok.start[0]
        text = tok.string.lstrip("#").strip()
        if line_no == 1 and tok.string.startswith("#!"):
            continue
        if any(text.startswith(d) or f" {d}" in f" {text}" for d in _DIRECTIVES):
            continue
        if letters := _foreign_letters(text):
            errors.append(f"{path}:{line_no}: non-English comment (found {letters[:10]!r})")
        standalone = lines[line_no - 1].lstrip().startswith("#")
        if standalone and line_no == prev_line + 1:
            run_len += 1
        else:
            flush()
            run_start, run_len = line_no, 1
        prev_line = line_no if standalone else -10
    flush()
    return errors


def _check_docstrings(source: str, path: str) -> list[str]:
    errors: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef | ast.ClassDef | ast.Module):
            continue
        doc = ast.get_docstring(node, clean=True)
        if not doc:
            continue
        line_no = node.body[0].lineno if node.body else 1
        if letters := _foreign_letters(doc):
            errors.append(f"{path}:{line_no}: non-English docstring (found {letters[:10]!r})")
        if (count := sum(1 for ln in doc.splitlines() if ln.strip())) > MAX_LINES:
            errors.append(f"{path}:{line_no}: docstring is {count} lines (max {MAX_LINES})")
    return errors


def check_source(source: str, path: str = "<string>") -> list[str]:
    """Return a list of violations found in a Python source string."""
    return _check_comments(source, path) + _check_docstrings(source, path)


_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".ruff_cache", ".mypy_cache", "node_modules"}


def _python_files(root: Path = Path()) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if not _SKIP_DIRS & set(p.parts))


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv] or _python_files()
    errors: list[str] = []
    for file in files:
        errors += check_source(file.read_text(encoding="utf-8"), file.as_posix())
    for err in errors:
        print(err)
    if errors:
        print(f"\n{len(errors)} comment violation(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
