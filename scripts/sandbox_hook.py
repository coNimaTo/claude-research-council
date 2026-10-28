#!/usr/bin/env python3
"""PreToolUse hook: run council-advisor Bash commands inside a read-only bwrap sandbox.

Registered in ~/.claude/settings.json (matcher "Bash"). Other agents and the main
session pass through untouched. Inside the sandbox the whole filesystem is read-only,
/tmp is a throwaway tmpfs and there is no network. Claude's own /tmp/claude-<uid>
scratchpads stay visible (read-only) so agents can read briefs the orchestrator
writes there. Fails closed: if the sandbox cannot be built, the command is denied
rather than run unprotected.
"""
import json, os, shlex, shutil, sys


def decide(event):
    if event.get("tool_name") != "Bash" or event.get("agent_type") != "council-advisor":
        return None
    tool_input = event.get("tool_input") or {}
    bwrap = shutil.which("bwrap")
    if not bwrap or not tool_input.get("command"):
        return deny("council sandbox unavailable (bwrap missing or empty command) — command blocked")
    cwd = event.get("cwd") or os.getcwd()
    scratch = shlex.quote(f"/tmp/claude-{os.getuid()}")
    sandboxed = (f"{bwrap} --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp --ro-bind-try {scratch} {scratch} "
                 f"--unshare-net --unshare-pid "
                 f"--die-with-parent --chdir {shlex.quote(cwd)} -- bash -c {shlex.quote(tool_input['command'])}")
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "permissionDecisionReason": "council sandbox: read-only filesystem, no network",
        "updatedInput": {**tool_input, "command": sandboxed},
    }}


def deny(reason):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": reason}}


def main():
    try:
        out = decide(json.load(sys.stdin))
    except Exception as e:  # fail closed: a broken hook must not let the command through unsandboxed
        out = deny(f"council sandbox hook error: {e}")
    if out:
        print(json.dumps(out))


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        assert decide({"tool_name": "Bash", "agent_type": "general-purpose", "tool_input": {"command": "ls"}}) is None
        assert decide({"tool_name": "Read", "agent_type": "council-advisor"}) is None
        o = decide({"tool_name": "Bash", "agent_type": "council-advisor", "cwd": "/tmp",
                    "tool_input": {"command": "echo 'a b' > f", "description": "x"}})["hookSpecificOutput"]
        assert o["permissionDecision"] == "allow" and o["updatedInput"]["description"] == "x"
        assert o["updatedInput"]["command"].endswith("-- bash -c 'echo '\"'\"'a b'\"'\"' > f'"), o
        print("self-check passed")
    else:
        main()
