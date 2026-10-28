# claude-council (personal fork)

Based on TorpedoD/claude-council, adapted for experimental-physics thesis work (Linux, read-only advisors, audit and review modes).

Pieces that live outside this folder:

- `~/.claude/agents/council-advisor.md` — the read-only agent type. A copy is kept in `agents/` (refreshed by the pre-commit hook); to restore: `cp agents/council-advisor.md ~/.claude/agents/`.
- Sandbox hook in `~/.claude/settings.json` (`hooks.PreToolUse`, matcher `Bash`):
  `python3 -I /home/nico/.claude/skills/claude-council/scripts/sandbox_hook.py`
- Reports and the journal (`journal/council-log.jsonl`) live in `~/Documents/Tesis/council/`, outside this repo.
