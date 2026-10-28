#!/usr/bin/env python3
"""Size up an audit target before any agent runs.

  audit_scope.py <path> [<path> ...]

Lists code files with line counts (notebooks: code-cell lines only), notes, and
data files grouped by directory. Last line is "SCOPE: OK" or "SCOPE: TOO BIG — ..."
(limits below) so the orchestrator can ask the user to narrow the target.
Always exits 0 except on bad arguments.
"""
import json, sys
from collections import defaultdict
from pathlib import Path

MAX_CODE_FILES = 40
MAX_CODE_LINES = 8000
CODE = {".py", ".ipynb", ".m", ".jl", ".r", ".c", ".h", ".cpp", ".hpp", ".f90", ".f", ".sh", ".js", ".ts"}
NOTES = {".md", ".tex", ".rst", ".txt"}
SKIP_DIRS = {".git", "__pycache__", ".ipynb_checkpoints", ".venv", "venv", "env", "node_modules",
             ".pytest_cache", ".mypy_cache", "build", "dist", ".tox", "site-packages"}


def code_lines(p):
    if p.suffix == ".ipynb":
        try:
            cells = json.loads(p.read_text(encoding="utf-8")).get("cells", [])
        except (OSError, ValueError):
            return 0
        return sum(len("".join(c.get("source", "")).splitlines()) for c in cells if c.get("cell_type") == "code")
    try:
        return sum(1 for line in p.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())
    except OSError:
        return 0


def walk(root):
    if root.is_file():
        yield root
        return
    for p in sorted(root.rglob("*")):
        if p.is_file() and not any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            yield p


def scan(paths):
    code, notes, data = [], [], defaultdict(lambda: [0, 0])
    for root in paths:
        for p in walk(root):
            ext = p.suffix.lower()
            if ext in CODE:
                code.append((p, code_lines(p), p.stat().st_size))
            elif ext in NOTES and p.stat().st_size < 2_000_000:
                notes.append((p, p.stat().st_size))
            else:
                d = data[p.parent]
                d[0] += 1
                d[1] += p.stat().st_size
    return code, notes, data


def verdict(code):
    n, lines = len(code), sum(c[1] for c in code)
    if n > MAX_CODE_FILES or lines > MAX_CODE_LINES:
        return f"SCOPE: TOO BIG — {n} code files / {lines} code lines (limit {MAX_CODE_FILES} / {MAX_CODE_LINES})"
    return f"SCOPE: OK — {n} code files / {lines} code lines"


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)
    home = Path.home().resolve()
    paths = []
    for a in sys.argv[1:]:
        p = Path(a).expanduser().resolve()
        if not p.exists():
            sys.exit(f"no such path: {p}")
        if p in (home, Path("/")):
            sys.exit(f"refusing to audit {p}: name a project folder or file")
        paths.append(p)
    code, notes, data = scan(paths)
    print("CODE (non-blank lines; notebooks = code cells only):")
    for p, n, size in sorted(code, key=lambda c: -c[1]):
        big = f"  [file {size // 1024} KB: outputs are heavy, read cells selectively]" if p.suffix == ".ipynb" and size > 1_000_000 else ""
        print(f"  {n:6d}  {p}{big}")
    print("NOTES:")
    for p, size in notes:
        print(f"  {size // 1024:6d} KB  {p}")
    print("DATA / OTHER (by directory):")
    for d, (n, size) in sorted(data.items()):
        print(f"  {n:4d} files {size / 1e6:8.1f} MB  {d}")
    print(verdict(code))


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        assert verdict([(Path("a.py"), 10, 0)]).startswith("SCOPE: OK")
        assert verdict([(Path("a.py"), MAX_CODE_LINES + 1, 0)]).startswith("SCOPE: TOO BIG")
        assert verdict([(Path("a.py"), 1, 0)] * (MAX_CODE_FILES + 1)).startswith("SCOPE: TOO BIG")
        print("self-check passed")
    else:
        main()
