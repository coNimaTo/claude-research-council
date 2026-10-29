# claude-council

A Claude Code skill that convenes a council of AI agents to examine research work. It does three jobs:

- **Decide**: pressure-test a hard choice, such as which fit procedure to trust, whether to spend the last wafer, or how to scope a chapter.
- **Audit**: check research code for errors in the physics, the numerics, the data handling and the statistics.
- **Review**: critique a scientific text (thesis chapter, paper, poster, talk) written in Spanish.

Each agent is given one perspective and can open the user's actual data, scripts, notebooks and notes. None of them can change anything. Every run produces an HTML report and a full transcript, and is logged in a journal so outcomes can be recorded and used to improve the advisors.

This is a fork of [TorpedoD/claude-council](https://github.com/TorpedoD/claude-council) (MIT), adapted for experimental-physics thesis work on Linux.

## Usage

```
/claude-council <decision>                 # decision council (auto-picks Quick/Standard/Deep)
/claude-council <decision> quick|deep      # force a mode; add "with codex" for a Decision Science pass
/claude-council audit <path> [-- focus] [quick]
/claude-council review <file> [-- focus] [quick]
/claude-council outcome <sha> <note>       # record how a run turned out
/claude-council meta                       # suggest advisor changes from 5+ recorded decision runs
```

Phrases such as "council this", "pressure-test this", "audit this analysis code" or "revisá este texto" also trigger it.

## Workflows

### Decide

```
question ─► frame (decision, context, stakes, options, FILES) ─► bias audit
        ─► 6 advisors in parallel, each reading the files
        ─► anonymised peer review (6 reviewers rank all answers, score consensus 1–5)
        ─► forced debate if consensus ≥ 4/5: Prosecutor attacks, Defender rebuts
        ─► Chairman-Consensus ‖ Chairman-Dissent ─► dissent ledger
        ─► verdict + confidence + "what would flip it" ─► report, journal
```

Modes keep cost bounded. **Quick** uses 4 advisors and no review (about 5 agent calls). **Standard** is the default (16–18 calls). **Deep** adds a debate every time and a Decision Science matrix (about 20 calls). A low-confidence Standard run offers to escalate to Deep.

Two chairmen are used because a single summariser tends to smooth over the sharpest objections. The dissent-biased chairman and the dissent ledger keep minority insights that lost the vote.

### Audit

```
path ─► size check (refuses whole home dirs; asks to narrow above 40 files / 8000 lines)
     ─► brief (purpose, headline results, entry points, sources)
     ─► 6 auditors in parallel; every finding needs file:line + evidence
     ─► merge duplicates ─► verifiers try to DISPROVE each finding
     ─► editor: bottom line, fix first, findings table, coverage, rejected
```

This mode is not a general code review. It asks whether the numbers the code produces are right.

### Review

```
file ─► size check (≤ 15 000 words, about one chapter)
     ─► brief (document, audience, the notebooks/data its numbers come from)
     ─► 6 reviewers in parallel; every comment quotes the exact text
     ─► verifiers try to disprove factual comments (style comments are not verified)
     ─► editor: comments in document order, recurring patterns, likely jury questions
```

Suggested replacement text is in Spanish, in the author's register. Explanations are in English.

## The personalities

### Decision advisors

| Advisor | Role |
|---|---|
| **Red Team** | Pre-mortem: assumes the preferred option has already failed and traces the failure back to the one assumption that caused it. |
| **Methodologist** | A paranoid experimental physicist and statistician who distrusts every result until its statistics, systematics, artifacts, forking paths and controls survive scrutiny. |
| **First Principles** | Strips the question to its components and proposes three reframings, each discarding one assumption. |
| **Expansionist** | Finds the options the user did not list and scores each on upside against extra effort. |
| **Outsider** | Has no context and opens no files. Reads the question as someone from an unrelated field would, to expose what only makes sense inside the bubble. |
| **Executor** | Works at bench level: research stage, a cost-of-test table (time, scarce resources consumed, reversibility, information gained) and the cheapest test that would settle the question. |

The supporting roles are a **bias auditor** (anchoring, sunk cost, garden of forking paths, artifact-as-signal, novelty pull), **peer reviewers**, a **Prosecutor and Defender**, and the two **chairmen**.

### Auditors

| Auditor | Looks for |
|---|---|
| **Model checker** | Equations against their textbook form, factors and sign conventions, units, material-model validity, known limiting cases. |
| **Numerics** | Grids against feature widths, convolution edges, optimiser setup, parameters stuck on bounds, identifiability, floating-point stability. |
| **Data-path tracer** | Follows a headline number from the raw file to the result: header rows, columns, masks, off-by-one errors, mismatched arrays, notebook state. |
| **Methodologist** | Fit statistics, missing uncertainties, thresholds chosen after seeing the data, conclusions never checked on held-out data. |
| **Reproducibility** | Notebook cell order, hidden inputs, stale pickles and cached arrays, library-version traps, tests that do not test values. |
| **Red Team** | Picks the result downstream work leans on most and hunts for the most plausible code-level way it is wrong. |

### Text reviewers

| Reviewer | Looks for |
|---|---|
| **Hostile referee** | Reads as the jury member who wants to find the weak point: overclaiming, missing comparison with literature, conclusions that do not follow. Lists the 5 hardest defense questions. |
| **Methodologist** | Whether every empirical claim has its uncertainty, comparison criterion and enough method to reproduce it. |
| **Numbers checker** | Traces every number back to its source notebook or data, checks that each value is consistent throughout the text, SI formatting, and that every figure, table and equation reference exists. |
| **Physics** | Correct equations, dimensions, definitions, stated approximations and consistent terminology. |
| **Outsider reader** | A physicist from another field with only the text: where they got lost, undefined acronyms, and their one-sentence summary of the main result. |
| **Language & style** | Spanish per current RAE norms, common physics anglicisms ("asumir", "eventualmente", "jugar un rol"), register and terminology consistency. |

## Safety: the council is read-only

Agents may read anything and run checks that only print to the screen. They cannot change files. This is enforced in three layers:

1. **Agent type.** Every agent runs as `council-advisor`, which has no Edit, Write or NotebookEdit tools.
2. **Sandbox.** A `PreToolUse` hook (`scripts/sandbox_hook.py`) runs each of the council's shell commands inside `bwrap`. The whole filesystem is read-only, there is no network (web research goes through the WebSearch and WebFetch tools), and `/tmp` is a temporary folder discarded afterwards. If the sandbox cannot be built, the command is blocked.
3. **Integrity check.** After every run, `scripts/integrity_check.py` lists any files that changed and any tool calls that look like writes. The report shows the result as a green or red line. It never reverts anything.

The transcript records `HARD BLOCK: on/off` (layer 1) and `SANDBOX: on/off` (layer 2) for every run.

## Install

Requirements: Claude Code, `jq`, `bwrap` (bubblewrap), Python 3. Optional: `pdftotext` for PDF reviews, `codex` for the Decision Science pass.

```bash
git clone <this repo> ~/.claude/skills/claude-council
cp ~/.claude/skills/claude-council/agents/council-advisor.md ~/.claude/agents/
```

Add the sandbox hook to `~/.claude/settings.json`:

```json
"hooks": { "PreToolUse": [ { "matcher": "Bash", "hooks": [ { "type": "command",
  "command": "python3 -I ~/.claude/skills/claude-council/scripts/sandbox_hook.py" } ] } ] }
```

Restart Claude Code.

**Paths to adapt.** Reports and the journal go to `~/Documents/Tesis/council/` (the report and journal paths are set in `SKILL.md`, `references/audit.md`, `references/review.md` and the `scripts/`). Some prompts assume an experimental-physics, MBE and optics context. For another field, edit the advisor and auditor prompts in `references/`.

## Files

| Path | Contents |
|---|---|
| `SKILL.md` | Decision workflow (Steps 0–10) and the entry points for the other modes |
| `references/personas.md` | Decision advisor prompts and the shared ground rules |
| `references/audit.md`, `references/review.md` | Audit and review workflows with all their agent prompts |
| `references/bias-audit.md`, `peer-review.md`, `debate-round.md`, `chairman.md`, `decision-science.md`, `modes.md` | Decision workflow stages |
| `assets/report-template.html` | Self-contained HTML report |
| `agents/council-advisor.md` | The read-only agent definition (copy; the live one is in `~/.claude/agents/`) |
| `scripts/` | Sandbox hook, integrity check, audit scope check, journal append/search/outcome, meta-analysis |

The journal (`~/Documents/Tesis/council/journal/council-log.jsonl`) holds one JSON line per run: mode, confidences, recommendation, dissent, report paths and the recorded outcome. Audit and review runs carry `kind: "audit"` or `kind: "review"`, and `meta` analyses decision runs only.
