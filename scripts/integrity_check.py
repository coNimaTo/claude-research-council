#!/usr/bin/env python3
"""Read-only integrity check for a council run.

  integrity_check.py start <sha>           mark the start of a run
  integrity_check.py end <sha> [dir ...]   report files changed since start + suspicious subagent tool calls

Always exits 0; the first output line is "INTEGRITY: clean" or "INTEGRITY: WARNING ...".
"""
import json, os, re, sys
from pathlib import Path

HOME = Path.home()
COUNCIL_OUT = HOME / "Documents/Tesis/council"
MARKER_DIR = COUNCIL_OUT / "journal"
PROJECTS = HOME / ".claude/projects"
# Dirs whose churn is not caused by advisors writing: caches python creates on import, Claude's own state.
SKIP_DIRS = {"__pycache__", ".ipynb_checkpoints", ".pytest_cache", ".mypy_cache"}
SKIP_ROOTS = [HOME / ".claude", COUNCIL_OUT]
EDIT_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
# shortcut: pattern match on Bash text, so writes hidden inside scripts are missed; the file scan is the backstop.
WRITE_CMD = re.compile(
    r"\b(rm|rmdir|mv|cp|tee|touch|truncate|mkdir|ln|dd|chmod|chown|install|wget)\b"
    r"|\b(sed|perl)\s+(-\w*\s+)*-i"
    r"|\bgit\s+(commit|add|push|checkout|reset|stash|clean|restore|rm|mv)\b"
    r"|\bcurl\b.*\s-o\b"
    r"|open\([^)]*['\"][wax]\+?b?['\"]|\.to_csv\(|\.to_excel\(|savefig\(|np\.save|\.write_text\(|\.write\("
)
# Shell redirects are matched only outside quotes, so awk '$2>=880' or python -c "x > 0" do not trip it.
REDIRECT = re.compile(r"(?<![0-9&>=<-])>>?(?!\s*(/dev/null|&|=))")
QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")


def writes(cmd):
    return bool(WRITE_CMD.search(cmd) or REDIRECT.search(QUOTED.sub("", cmd)))


def marker(sha):
    return MARKER_DIR / f".run-{sha}.marker"


def changed_files(dirs, since_ns):
    hits = []
    for d in dirs:
        d = Path(d).expanduser().resolve()
        if d in (HOME, Path("/")) or not d.is_dir():
            continue
        for root, subdirs, files in os.walk(d):
            r = Path(root)
            subdirs[:] = [s for s in subdirs if s not in SKIP_DIRS and not any((r / s).is_relative_to(x) for x in SKIP_ROOTS)]
            for f in files:
                p = r / f
                try:
                    if p.lstat().st_mtime_ns > since_ns:
                        hits.append(str(p))
                except OSError:
                    pass
    return sorted(set(hits))


def audit_subagents(since_ns):
    findings, agents = [], []
    for tr in PROJECTS.glob("*/*/subagents/agent-*.jsonl"):
        try:
            if tr.stat().st_mtime_ns <= since_ns:
                continue
            meta = json.loads(tr.with_suffix(".meta.json").read_text()) if tr.with_suffix(".meta.json").exists() else {}
        except (OSError, ValueError):
            meta = {}
        who = meta.get("description", tr.stem)
        agents.append((who, meta.get("agentType", "?")))
        try:
            lines = tr.read_text().splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                content = json.loads(line).get("message", {}).get("content")
            except ValueError:
                continue
            if not isinstance(content, list):
                continue
            for b in content:
                if b.get("type") != "tool_use":
                    continue
                if b.get("name") in EDIT_TOOLS:
                    findings.append(f"[{who}] {b['name']} {b.get('input', {}).get('file_path', '')}")
                elif b.get("name") == "Bash":
                    cmd = b.get("input", {}).get("command", "")
                    if writes(cmd):
                        findings.append(f"[{who}] Bash: {cmd[:200]}")
    return agents, findings


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("start", "end"):
        print(__doc__.strip())
        return
    m = marker(sys.argv[2])
    if sys.argv[1] == "start":
        MARKER_DIR.mkdir(parents=True, exist_ok=True)
        m.touch()
        print(f"Integrity marker set: {m}")
        return
    if not m.exists():
        print("INTEGRITY: WARNING — no start marker found; check could not run")
        return
    since = m.stat().st_mtime_ns
    files = changed_files(sys.argv[3:], since)
    agents, findings = audit_subagents(since)
    m.unlink()
    not_blocked = [w for w, t in agents if t != "council-advisor"]
    problems = []
    if files:
        problems.append(f"{len(files)} file(s) changed during the council")
    if findings:
        problems.append(f"{len(findings)} suspicious subagent tool call(s)")
    print("INTEGRITY: clean" if not problems else "INTEGRITY: WARNING — " + "; ".join(problems))
    print(f"Subagents audited: {len(agents)}" + (f" (not council-advisor, hard block off: {', '.join(not_blocked)})" if not_blocked else ""))
    for f in files[:50]:
        print(f"CHANGED: {f}")
    for f in findings[:50]:
        print(f"SUSPECT: {f}")


if __name__ == "__main__":
    main()
