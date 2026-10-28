---
name: claude-council
description: |
  Read-only LLM Council for research work. Four workflows: (1) decisions — six advisors (Red Team, Methodologist, First Principles, Expansionist, Outsider, Executor) read the user's data/scripts, peer review, forced debate, dual chairman with dissent ledger; modes quick/standard/deep, "with codex"; (2) /claude-council audit <path> — research-code audit (physics, numerics, data path, statistics, reproducibility), every finding verified; (3) /claude-council review <file> — review of a Spanish thesis chapter, paper, poster or talk (referee, numbers vs sources, physics, outsider, language), likely jury questions; (4) outcome <sha> <note> / meta. Triggers: /claude-council, "council this", "pressure-test this", "I'm torn between X and Y", "audit this analysis code", "review this chapter", "revisá este texto". Not for factual questions, quick yes/no, ordinary coding or debugging help.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion
---

# LLM Council

> **Install path assumption:** This skill assumes installation at `~/.claude/skills/claude-council/`. If installed elsewhere (e.g., `~/.claude/plugins/<name>/skills/claude-council/`), adjust script paths in Steps 0, 2, 8b and 10 accordingly.

Run any high-stakes decision through six structured thinking lenses (advisors inspect the actual data, scripts and notes involved), a peer-review round, a forced debate when consensus is too clean, and a dual-chairman synthesis that preserves dissent. Every run logs to a journal; outcomes feed a self-improvement loop that proposes persona refinements over time.

**Not for:** factual lookups, debugging, single-domain technical questions, quick yes/no decisions, emotional support. If none of the options feel genuinely hard, just answer directly.

**Read-only council.** Every `Agent()` call in this skill (bias audit, advisors, reviewers, debaters, chairmen, dissent pass, Decision Science fallback) uses `subagent_type="council-advisor"` — an agent type with no Edit/Write/NotebookEdit tools (`~/.claude/agents/council-advisor.md`). If that type is unavailable, fall back to `general-purpose`, and write `HARD BLOCK: off (council-advisor agent not installed)` at the top of the transcript. Their shell commands run in a read-only, offline `bwrap` sandbox when `scripts/sandbox_hook.py` is registered as a PreToolUse hook in `~/.claude/settings.json`: check with `grep -q sandbox_hook ~/.claude/settings.json` and write `SANDBOX: on` or `SANDBOX: off (hook not registered)` under the HARD BLOCK line. Step 8b audits every run.

---

## Step 0 — Handle special invocations first

- `/claude-council outcome <sha1> <note>` — look up the run in `~/Documents/Tesis/council/journal/council-log.jsonl` by sha1 prefix, update its `outcome` field, and confirm. Done.
- `/claude-council audit <path> [...] [-- focus] [quick]` — research-code audit (physics, numerics, data path, statistics, reproducibility). Follow `references/audit.md` instead of Steps 1–10. Done.
- `/claude-council review <file> [...] [-- focus] [quick]` — review of a Spanish scientific text (thesis chapter, paper, poster, talk): referee, methodologist, numbers checker, physics, outsider, language. Follow `references/review.md` instead of Steps 1–10. Done.
- `/claude-council meta` — run `bash ~/.claude/skills/claude-council/scripts/meta_analysis.sh` and surface the resulting amendment file path. Done.
- Any other invocation → continue to Step 1.

---

## Step 1 — Triage

Reject and answer directly if ANY applies:
1. Factual / one right answer ("capital of France?")
2. Single-domain technical with a settled textbook/datasheet answer — answer directly (a genuine trade-off between methods, designs, recipes or analysis approaches IS councilable)
3. No stakes named — ask once via AskUserQuestion "what makes this high-stakes?"; if user shrugs, drop
4. Binary with obvious answer ("ship untested code to prod Friday?")
5. Already decided and seeking validation — ask: challenge or confirm? If confirm, skip
6. Emotional-support framing — say so kindly, don't council it

---

## Step 2 — Pre-run journal lookup

Escape the raw question for safe shell passing: replace all single quotes with `'\''`, then wrap in single quotes. Store as `$ESCAPED_QUESTION`. Never pass raw user text directly to bash — `$(...)`, backticks, and `\` sequences in the question would execute.

```bash
SHA=$(printf '%s' "$ESCAPED_QUESTION" | sha1sum | cut -c1-8)
bash ~/.claude/skills/claude-council/scripts/journal_search.sh "$ESCAPED_QUESTION"
python3 -I ~/.claude/skills/claude-council/scripts/integrity_check.py start "$SHA"
```

`$SHA` is computed here (not in Step 9) because Step 7a needs it, and it hashes the raw question with the same recipe as `journal_search.sh`, so a repeated question finds its earlier run.

If ≥1 prior run matches on sha1-prefix or keyword overlap: surface a one-line summary ("Related council on DATE — recommended X — outcome: Y") and inject up to 2 prior verdicts as **"Prior council context"** in the framed question.

---

## Step 3 — Frame the question + Bias Audit

**3a. Workspace scan** — Glob for `CLAUDE.md`, `memory/`, any user-referenced files. Cap at 3 files chosen by recency + CLAUDE.md precedence. Cap framed question at ~4k tokens; note truncation in transcript.

Separately, list the **absolute paths** of the data files, analysis scripts, notebooks, simulation outputs and notes the decision depends on (user-named ones plus obvious ones found by a quick Glob). These go in the `FILES:` field — advisors open them themselves, so this list is not capped by the ~4k token budget; don't paste their contents into the framed question. If no `CLAUDE.md` or `memory/` files are found, include in the transcript: "Workspace scan: no project context found. Council proceeds with user-provided context only."

If question is vague, use AskUserQuestion **once** to clarify. Then produce `{{FRAMED_QUESTION}}`:
```
DECISION: <core question>
CONTEXT: <workspace + user context>
STAKES: <what's at stake>
OPTIONS: <options named by user, if any>
FILES: <absolute paths advisors should inspect, one per line; "none" if the question is general>
PRIOR: <prior council context if any>
```

Store the full framed question text as the shell variable `FRAMED_QUESTION` for use in later steps. Escape single quotes in the text (`'` → `'\''`).

**3b. Bias Audit** — **skip in Quick mode** (latency cost is not justified; see `references/modes.md`). In Standard/Deep: single Agent() call using the prompt in `references/bias-audit.md`. Pass `{{FRAMED_QUESTION}}`. Receives back a structured bias-flags list. Append to framed question as:
```
BIAS FLAGS: <list — these are signals, not verdicts>
```

If the bias audit returns "BIAS AUDIT: Clean — no significant distortions detected.", omit the `BIAS FLAGS:` section from the framed question entirely. In the HTML report, render `{{BIAS_FLAGS_HTML}}` as an empty string.

---

## Step 4 — Mode selection

Read `references/modes.md` for full escalation logic. Summary:

| Mode | When | ~Calls |
|---|---|---|
| Quick | "quick" suffix / no scarce resource at risk / ≤ 1-day reversible | 5 |
| Standard | default | 16–18 |
| Deep | "deep" / high stakes / auto-escalate from low confidence | 19 + 1 Codex |

---

## Step 5 — Fan-out (parallel Agent calls)

Read `references/personas.md` for all six persona prompts. Append the **Ground Rules** block from that file to every persona prompt **except the Outsider's** (the Outsider's value is having no context — it must not open files). Dispatch in a **single turn**:

- **Standard/Deep:** 6 parallel `Agent(subagent_type="council-advisor", description="<persona>", prompt=<persona_prompt with FRAMED_QUESTION substituted + Ground Rules>)` calls
- **Quick:** 4 advisors (Red Team, Methodologist, Executor, First Principles)

**Deep mode enhancement:** For Deep mode, append to First Principles and Expansionist prompts: "Return ALL three reframings/options with full reasoning for each, not just the strongest + runner-up."

Every persona prompt mandates this appendix at the end of the response:
```
=== CONFIDENCE ===
confidence: high | medium | low
assumptions: <bulleted premises>
what_would_change_my_mind: <1-3 signals>
unknowns: <missing facts>
```

For Deep mode, the **Codex Decision Science pass** runs after advisors return (Step 6) — not in parallel — so Codex can evaluate advisor-surfaced options, not just the options the user named.

---

## Step 6 — Codex Decision Science pass (Deep mode / "with codex")

Read `references/decision-science.md`. Extract the options from `{{FRAMED_QUESTION}}` + advisors' responses.

**Codex invocation:**

```bash
if command -v codex >/dev/null 2>&1; then
  CODEX_OUTPUT=$(printf '%s' "$DECISION_SCIENCE_PROMPT" \
    | timeout 120 codex exec --sandbox read-only --skip-git-repo-check -) \
    || CODEX_OUTPUT=""
fi
```

**Safety note:** The prompt is piped via stdin using `printf '%s'`, not a heredoc — this avoids shell expansion of any `$`, backticks, or metacharacters in the prompt text. The orchestrator must pre-build `$DECISION_SCIENCE_PROMPT` as a shell variable containing the full decision-science prompt (from `references/decision-science.md`) with `{{FRAMED_QUESTION}}` and `{{OPTIONS_LIST}}` already substituted in as literal text.

**Fallback** (Codex absent, timed out, or errored): `Agent(subagent_type="council-advisor", prompt=<decision-science prompt>)`. Set `CODEX_USED=false`. If Codex ran successfully, set `CODEX_USED=true`. These must be the literal JSON booleans `true` or `false` (no quotes) — `--argjson` in Step 10 requires valid JSON.

**Parsing Decision Science output:** The output contains JSON blocks followed by plain-text RANKING/DOMINATED/KEY ASSUMPTION sections. Parse JSON blocks by matching `{` ... `}` boundaries (the schema has no nested objects). If JSON parsing fails on any block, capture the raw text and present it in the transcript — do not crash the council. The plain-text sections follow the last JSON block.

---

## Step 7 — Anonymize + Peer review + Forced Debate

**7a. Anonymize** — Steps:
1. Generate a random A-F permutation (A-D in Quick) seeded from the first 4 hex digits of `$SHA` (deterministic per question, reduces journal diff noise). Record the mapping in the transcript.
2. Strip each response's first line if it contains a self-identification.
3. **Structural sanitisation** — regex-replace persona-signature patterns that leak identity through anonymised text:
   - `THE FAILURE MODE` / `THE ROOT CAUSE` / `THE MISSED SIGNAL` / `THE ALTERNATIVE` → `POINT 1` / `POINT 2` / `POINT 3` / `POINT 4`
   - `REFRAMING [ABC]` → `PERSPECTIVE [1/2/3]`; `STRONGEST:` / `RUNNER-UP:` → `PRIMARY:` / `SECONDARY:`
   - `OPTION [XYZ]` → `ALTERNATIVE [1/2/3]`; `DOMINANT:` → `RECOMMENDED:`
   - `FIELD:` / `NAIVE READ:` / `BUBBLE SPOTS:` / `CROSS-DOMAIN INSIGHT:` → `LENS:` / `INITIAL READ:` / `ASSUMPTIONS:` / `INSIGHT:`
   - `EVIDENCE CLAIM` / `THREATS` / `MISSING CONTROL` / `MINIMUM VALID DESIGN` → `CLAIM` / `ISSUES` / `GAP` / `PROPOSAL`; severity tags `BLOCKER` / `MAJOR` / `MINOR` → `HIGH` / `MEDIUM` / `LOW`
   - `RESEARCH STAGE` → `PHASE ASSESSMENT`; `COST-OF-TEST TABLE` → `OPTION COSTING`; `CHEAPEST DECISIVE TEST` → `FIRST TEST`; `STATUS: DRAFT` → `NOTE: INCOMPLETE DATA`
4. Preserve `=== CONFIDENCE ===` blocks unchanged (all personas share this format).

**7b. Peer review (Standard/Deep)** — Read `references/peer-review.md` for the full reviewer prompt. Dispatch 6 parallel Agent() calls, each receiving all anonymized A–F responses plus the reviewer prompt.

**Score extraction:** Each reviewer's Q4 answer must be a single integer 1–5. Extract using regex: `CONSENSUS STRENGTH:\s*(\d)` (case-insensitive). If a reviewer outputs a non-integer or out-of-range value, default to 3 (neutral) and log a warning in the transcript. Compute the arithmetic mean of all 6 extracted scores, rounded to one decimal.

**Consensus summary synthesis:** After collecting peer reviews, produce a 2-3 sentence `CONSENSUS_SUMMARY` capturing: (a) what the majority of advisors recommend, (b) the dominant reasoning, (c) any conditions or caveats shared across reviews. Store as the variable `$CONSENSUS_SUMMARY` — this is substituted into the Prosecutor and Defender prompts in `references/debate-round.md`.

**7c. Forced Debate** — if consensus-strength average ≥ 4.0 (or always in Deep): run two **sequential** Agent() calls using `references/debate-round.md`. If average is > 2.0 but < 4.0 in Standard mode: skip debate (healthy disagreement that doesn't need adversarial pressure). If average ≤ 2.0: skip debate and note in transcript: "Debate round skipped — insufficient consensus (score: X/5)."
1. Prosecutor — attacks the consensus. Wait for response.
2. Defender — substitutes `{{PROSECUTOR_RESPONSE}}` with the Prosecutor's output, then dispatches. Defender cannot run until Prosecutor returns.

Read `references/debate-round.md` for full prompts.

---

## Step 8 — Dual Chairman + Dissent Preservation

**De-anonymize before chairman dispatch:** Using the A-F mapping from Step 7a, restore persona labels on each response. The chairman prompts in `references/chairman.md` expect persona-labelled inputs (`Red Team: ...`, `Methodologist: ...`, `First Principles: ...`, etc.) — substitute the original (un-anonymised) response text, not the sanitised peer-review version.

Read `references/chairman.md`. Three Agent() calls in two waves:

**Wave A (parallel):** dispatch both in a single turn:

1. **Chairman-Consensus** (majority-biased) — standard 5-section verdict
2. **Chairman-Dissent** (minority-biased) — same structure, anchored on dissent

**Wave B (sequential, after both return):**
3. **Dissent Preservation Pass** — receives both chairmen outputs; produces Dissent Ledger (2–5 bullets of insights Consensus softened)

Final verdict = Chairman-Consensus output + Dissent Ledger appended.

Mandate verdict header:
```
Council confidence: high | medium | low  (n/6 high, n/6 medium, n/6 low)
Dominant assumption: <single shared premise>
Breakers: <top 2 signals that flip the recommendation>
```

**Escalation check (Standard mode only — Deep does not re-escalate):**

Trigger escalation if ANY of:
- `chairman_confidence` is `low`
- 3 or more advisors output `confidence: low`
- "Where the council clashes" section has ≥2 items where neither side was found "more persuasive"

If triggered: `AskUserQuestion` — *"Council confidence is low (reason: {which trigger}). Escalate to Deep mode for a more thorough analysis?"*
- If yes: re-run from Step 5 in Deep mode, passing prior advisor outputs as context so advisors refine rather than restart.
- If no: proceed with Standard verdict; render the confidence header with `confidence-low` (red) styling in the HTML report.
- If mode is already Deep: do not re-escalate. Proceed with low-confidence verdict and note it prominently.

---

## Step 8b — Integrity check (every mode)

Before writing any output, check that no council agent changed anything. Pass the parent directory of every `FILES:` path plus `$PWD` (the script ignores `$HOME` and `/` as too broad, plus `__pycache__` and `~/.claude`):

```bash
python3 -I ~/.claude/skills/claude-council/scripts/integrity_check.py end "$SHA" <dir> [<dir> ...]
```

The first output line is `INTEGRITY: clean` or `INTEGRITY: WARNING — …`, followed by `CHANGED:` lines (files modified since Step 2) and `SUSPECT:` lines (subagent Edit/Write calls, or Bash commands that look like writes, with the agent's name). `SUSPECT` is a pattern match — a comparison like `awk '$1 > 3'` can trip it — so `CHANGED` is the authoritative signal. Changes the user made themselves during the run also appear; say so rather than assume an agent did it.

- **Clean:** note it in the transcript; render `{{INTEGRITY_HTML}}` as `<div class="integrity integrity-clean">Integrity check: clean — no files changed, no write attempts (N subagents audited)</div>`.
- **Warning:** do NOT revert or touch the listed files. Tell the user in chat *before* the verdict, quoting every `CHANGED`/`SUSPECT` line, and render `{{INTEGRITY_HTML}}` as `<div class="integrity integrity-warning"><strong>Integrity warning</strong><ul><li>…one per line, HTML-escaped…</li></ul></div>`. Paste the full script output into the transcript.

---

## Step 9 — Generate outputs

**Timestamp + sha1:**
```bash
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
FILE_TS=$(date -u +%Y%m%d-%H%M%SZ)
```

`$SHA` comes from Step 2. `-u` forces UTC. `FILE_TS` is the filename-safe variant; `TS` is ISO 8601 for the journal.

**Filenames:** `council-report-${FILE_TS}-q${SHA}.html`, `council-transcript-${FILE_TS}-q${SHA}.md`

**Output directory:** always `~/Documents/Tesis/council/` (run `mkdir -p ~/Documents/Tesis/council` first), regardless of the current working directory.

**HTML token → source mapping:**

| Token | Source | Notes |
|---|---|---|
| `{{TITLE}}` | First 80 chars of DECISION line from framed question | **HTML-escape** all `<>&"'` |
| `{{TIMESTAMP}}` | `$TS` (ISO 8601 UTC) | |
| `{{MODE_LABEL}}` | `"Quick"` / `"Standard"` / `"Deep"` | |
| `{{MODE_CLASS}}` | `"quick"` / `"standard"` / `"deep"` (lowercase for CSS) | |
| `{{CODEX_BADGE_HTML}}` | `<span class="badge codex">Decision Science</span>` if codex ran; empty string otherwise | |
| `{{CONFIDENCE_HEADER_HTML}}` | Render verdict confidence header as `<div class="confidence-block confidence-{level}">` with Council confidence line, Dominant assumption, Breakers | Use `confidence-high`, `confidence-medium`, or `confidence-low` class |
| `{{QUESTION_HTML}}` | Full framed question text | **HTML-escape** all `<>&"'` to prevent XSS |
| `{{BIAS_FLAGS_HTML}}` | Bias audit output in `<div class="bias-flags"><strong>Pre-council bias scan</strong>...</div>`; empty string if Quick or clean audit | |
| `{{VERDICT_HTML}}` | Chairman-Consensus verdict (markdown → HTML: `## H2` → `<h2>`, `- bullet` → `<ul><li>`, paragraphs → `<p>`) | |
| `{{DISSENT_LEDGER_HTML}}` | Dissent bullets in `<div class="dissent-ledger"><strong>Dissent Ledger</strong><ul><li>...</li></ul></div>`; empty if Clean or Quick | |
| `{{AGREEMENT_GRID_HTML}}` | "Where the council agrees" as `<div class="card">` with `<table class="grid-table">` showing advisor agreement; empty if Quick | |
| `{{COST_TABLE_HTML}}` | Executor cost-of-test table as `<div class="card"><div class="card-title">Cost of Test</div><div class="card-body"><table class="cost-table">...</table></div></div>`, followed by the cheapest decisive test as a `<p>`; empty if no table | |
| `{{DECISION_SCIENCE_MATRIX_HTML}}` | Decision Science JSON as `<div class="card"><div class="card-title">Decision Science</div><div class="card-body"><table class="ds-table">...</table></div></div>`; empty if not ran | Rows: `dominant` class for dominant, `dominated` for dominated |
| `{{DEBATE_HTML}}` | Debate as `<div class="card"><div class="card-title">Debate Round</div><div class="card-body"><div class="debate-callout">...</div></div></div>` with prosecutor/defender sides; empty if skipped | |
| `{{ADVISORS_HTML}}` | Each advisor as `<details class="advisor-{kebab}"><summary>{Name} <span class="conf-{level}">{level}</span></summary><div class="detail-body">{text}</div></details>` | kebab: `red-team`, `methodologist`, `first-principles`, `expansionist`, `outsider`, `executor` |
| `{{REVIEWS_HTML}}` | Each review as `<details><summary>Reviewer {N}</summary><div class="detail-body">{text}</div></details>`; empty if Quick | |
| `{{INTEGRITY_HTML}}` | From Step 8b | **HTML-escape** each listed path/command |
| `{{FOOTER_HTML}}` | `LLM Council &middot; Mode: {mode} &middot; SHA: {sha} &middot; <a href="{transcript_path}">Full transcript</a>` | |

**HTML:** Read `assets/report-template.html`, substitute all tokens per the table above, Write. Open with `xdg-open <path> >/dev/null 2>&1 &`.

**Transcript:** Write a markdown file with: invocation timestamp, framed question, anonymization map, all advisor responses with persona names, all peer reviews, debate transcript (if ran), both chairman outputs, dissent ledger, full verdict, Decision Science matrix (if ran).

**HTML sanitisation note:** Tokens marked "HTML-escape" in the table (`TITLE`, `QUESTION_HTML`) contain raw user text and must have `<>&"'` escaped. The remaining `*_HTML` tokens (`VERDICT_HTML`, `ADVISORS_HTML`, `REVIEWS_HTML`, `DEBATE_HTML`, `BIAS_FLAGS_HTML`, `FOOTER_HTML`) are orchestrator-generated HTML — they are safe because the orchestrator constructs them from controlled templates and never inserts raw user text directly. If any user-provided text appears inside these tokens (e.g., the question echoed in the verdict), it must be HTML-escaped at the point of insertion, not at the token level.

**After substitution, verify:** `grep '{{' <html_path>` must return zero matches. If any token remains unfilled, replace it with an empty string and log a warning in the transcript.

---

## Step 10 — Journal append + user prompt

Construct the journal payload from values collected during this run. All fields are required:

```json
{
  "ts": "$TS",
  "question_sha1_prefix": "$SHA",
  "mode": "<Quick|Standard|Deep — the mode actually used, including escalation>",
  "codex_used": <true if Decision Science ran via Codex; false otherwise>,
  "biases_flagged": [<list of bias names from Step 3b, or empty array if Quick/clean>],
  "advisors_confidence": {
    "red_team": "<high|medium|low from Red Team's CONFIDENCE block>",
    "methodologist": "<from Methodologist>",
    "first_principles": "<from First Principles>",
    "expansionist": "<from Expansionist>",
    "outsider": "<from Outsider>",
    "executor": "<from Executor>"
  },
  "chairman_confidence": "<high|medium|low from the verdict header>",
  "recommendation_one_liner": "<one sentence — the Recommendation section's first sentence>",
  "dissent_ledger": [<each DISSENT PRESERVED bullet as a string, or empty array if Clean>],
  "html_path": "<absolute path to the HTML report written in Step 9>",
  "transcript_path": "<absolute path to the transcript written in Step 9>",
  "outcome": null
}
```

Build this as a valid JSON string. Use `jq -n` to construct it safely (handles quotes and special characters in recommendation text):

```bash
PAYLOAD=$(jq -n \
  --arg ts "$TS" \
  --arg sha "$SHA" \
  --arg mode "$MODE" \
  --argjson codex "$CODEX_USED" \
  --argjson biases "$BIASES_JSON" \
  --argjson conf "$ADVISORS_CONF_JSON" \
  --arg chair_conf "$CHAIRMAN_CONF" \
  --arg rec "$RECOMMENDATION" \
  --argjson dissent "$DISSENT_JSON" \
  --arg html "$HTML_PATH" \
  --arg transcript "$TRANSCRIPT_PATH" \
  '{ts:$ts, question_sha1_prefix:$sha, mode:$mode, codex_used:$codex,
    biases_flagged:$biases, advisors_confidence:$conf,
    chairman_confidence:$chair_conf, recommendation_one_liner:$rec,
    dissent_ledger:$dissent, html_path:$html, transcript_path:$transcript,
    outcome:null}')
bash ~/.claude/skills/claude-council/scripts/journal_append.sh "$PAYLOAD"
```

Where the shell variables are set from the run's outputs:
- `$TS` — from Step 9; `$SHA` — from Step 2
- `$MODE` — `"Quick"`, `"Standard"`, or `"Deep"`
- `$CODEX_USED` — `true` or `false` (JSON boolean, no quotes)
- `$BIASES_JSON` — JSON array, e.g. `'["anchoring","sunk cost"]'` or `'[]'`
- `$ADVISORS_CONF_JSON` — JSON object, e.g. `'{"red_team":"high","methodologist":"medium","first_principles":"medium","expansionist":"high","outsider":"low","executor":"medium"}'`
- `$CHAIRMAN_CONF` — `"high"`, `"medium"`, or `"low"`
- `$RECOMMENDATION` — first sentence of the Recommendation section
- `$DISSENT_JSON` — JSON array of dissent bullets, or `'[]'`
- `$HTML_PATH`, `$TRANSCRIPT_PATH` — absolute paths from Step 9

Tell the user: *"Council logged (sha: `$SHA`). To record how it turned out: `/claude-council outcome $SHA <short note>`. Run `/claude-council meta` after 5+ runs for persona refinement suggestions (requires `jq`)."*

Then show the HTML file path and a one-paragraph chat summary (recommendation + one thing to do first). No longer.
