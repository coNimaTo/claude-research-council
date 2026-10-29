# Audit mode — research-code audit

Invocation: `/claude-council audit <path> [<path> ...] [-- focus text] [quick]`

Six auditors read the code with a research lens (physics, numerics, data path, statistics, reproducibility, the headline result). Every finding must cite `file:line`. Verifiers then try to disprove each finding, and an editor ranks what survives. There is no debate or chairman: an audit needs coverage and proof, not a verdict between options.

Generic style/bug review already exists (`/code-review`, `/ponytail-audit`); this mode is for **whether the numbers the code produces are right**.

All `Agent()` calls use `subagent_type="council-advisor"` (read-only), with the same fallback and `SANDBOX:` rules as the decision workflow. If the sandbox is off, say so to the user before dispatching auditors, since they import the target code.

| Mode | Auditors | Calls |
|---|---|---|
| Audit | 6 | 6 + 1–6 verifiers + 1 editor (≈ 8–13) |
| Audit quick (`quick` suffix) | 3: Data-path tracer, Model checker, Methodologist | 3 + 1–3 verifiers + 1 editor (≈ 5–7) |

---

## A1 — Scope (before any agent runs)

A path is required. If none was given, ask once with AskUserQuestion (offer the current project folder and its main subfolders). Never default to a whole home directory.

```bash
python3 -I ~/.claude/skills/claude-council/scripts/audit_scope.py <path> [<path> ...]
```

- `SCOPE: TOO BIG` → do not proceed. AskUserQuestion with 2–4 narrower targets drawn from the listing (e.g. the package folder, the one notebook that produces the result, the fitting module), plus the user's own choice. Re-run the scope check on the answer.
- Notebooks flagged as heavy: tell auditors in the brief to read those cells selectively.
- The listing feeds the brief; do not paste it whole into prompts if it is long, keep the CODE part.

## A2 — Brief

Escape and hash the target exactly like the decision workflow's Step 2, with the question replaced by `audit:` + the absolute target paths joined by spaces (so re-auditing the same target finds the earlier run):

```bash
AUDIT_KEY='audit:/abs/path1 /abs/path2'
SHA=$(printf '%s' "$AUDIT_KEY" | sha1sum | cut -c1-8)
bash ~/.claude/skills/claude-council/scripts/journal_search.sh "$AUDIT_KEY"
python3 -I ~/.claude/skills/claude-council/scripts/integrity_check.py start "$SHA"
```

Read `CLAUDE.md`, a README, and the notes/memory the project has (cap 3 files) to learn what the code is for. Then write `{{AUDIT_BRIEF}}`:

```
RESEARCH CONTEXT: <$RESEARCH_CONTEXT from the settings, or "not set">
TARGET: <absolute paths>
PURPOSE: <what this code computes, for which experiment/thesis section>
HEADLINE RESULTS: <the numbers, fits, figures or tables downstream work relies on, with where they are produced (file / notebook cell)>
ENTRY POINTS: <scripts/notebooks/functions that produce those results>
CODE: <file list with line counts from audit_scope.py>
NOTES: <notes files relevant to the target>
DATA: <data directories the code reads>
KNOWN ISSUES / RECENT FIXES: <from notes, journal, git log -10 if a repo; "none known">
FOCUS: <user's focus text, or "none — full audit">
PRIOR AUDITS: <journal hits for this target, with outcome, or "none">
```

If HEADLINE RESULTS cannot be found in the files, ask the user once ("Which results from this code matter most?"). It steers every auditor; do not guess silently.

## A3 — Auditors (single turn, parallel)

Each prompt = the lens section below + AUDIT RULES + FINDING FORMAT, with `{{AUDIT_BRIEF}}` substituted.

### Shared: AUDIT RULES

```
AUDIT RULES:
- Read the code before judging. Start from the ENTRY POINTS and follow the path that produces the HEADLINE RESULTS; read helpers only as deep as that path needs. For notebooks, read the cells that build the result and their saved outputs.
- READ-ONLY: never edit, move or delete files. Do not execute notebooks, run scripts that save files, refit and save, or talk to instruments. You MAY run small print-only checks (python3 -c / python3 - <<'EOF' that import the package and print a value, evaluate a function at a known point, compare against a hand calculation) — first read the module to make sure importing it does not write files.
- A finding needs evidence: the exact file:line, the code quoted, and either a print-only check you ran with its output or a short derivation. No evidence → put it under SUSPICIONS, not FINDINGS.
- Severity: BLOCKER = changes a reported number, figure or conclusion beyond its stated uncertainty, or invalidates it. MAJOR = biases results within uncertainty, or is silently wrong on a reachable path (other samples, other angles, new data). MINOR = robustness or reproducibility friction with no effect on current results.
- Stay in your lens; other auditors cover the rest. At most 8 findings, most severe first. Quality over count: one proven BLOCKER beats ten style remarks. Ignore style, naming and formatting entirely.
- Use web search only to check a reference value or published formula you need; name the source.
```

### Shared: FINDING FORMAT

```
=== FINDINGS ===
FINDING <n>
SEVERITY: BLOCKER | MAJOR | MINOR
WHERE: /absolute/path:line[-line]
WHAT: <one sentence>
EFFECT: <which headline result it touches and the estimated size (nm, %, rms…), or "unknown">
EVIDENCE: <quoted code + the check you ran and its output, or the derivation>
FIX SKETCH: <1–2 lines; not applied>

=== SUSPICIONS ===
- <file:line — what looks wrong, what check would settle it>   (or "none")

=== CHECKED AND OK ===
- <file:line or area — what you verified and found correct>   (at least 3; this is the coverage record)

=== CONFIDENCE ===
confidence: high | medium | low
not_examined: <files/areas in your lens you did not get to>
```

### Model checker

```
You are the Model Checker on a research-code audit council — a theorist who checks that the code implements the physics it claims to. You compare equations in the code against their textbook/paper form.

What you check:
- Equations: transcription errors, wrong factor (2π, ½, n vs n²), conjugation, sign and phase conventions (e.g. e^{+iωt} vs e^{-iωt}), coordinate and angle conventions, formulas used outside the geometry they were derived for
- Units and conversions: nm/µm/m, eV↔nm, degrees↔radians, % vs fraction, per-cell vs per-layer quantities
- Material models: dispersion formulas and their parameters against the cited source, validity range (wavelength, composition x, temperature) and what happens outside it (extrapolation, clipping)
- Boundary and limit cases: does the code reproduce known limits (an analytic special case, a conservation law, a textbook value)? Run one such check when cheap.
- Hidden assumptions: normal incidence formulas used at oblique angles, incoherent vs coherent treatment of thick layers, substrate backside ignored

{{AUDIT_BRIEF}}
```

### Numerics

```
You are the Numerics auditor on a research-code audit council — a computational physicist who distrusts every grid, tolerance and optimiser setting until shown it is converged.

What you check:
- Sampling and grids: wavelength/angle step vs the narrowest feature (resonance linewidth, fringe spacing); interpolation onto measurement grids; edge effects of convolution/windowing; Gaussian FWHM vs sigma confusion
- Optimisation: parameter scaling, bounds that bind (a parameter sitting on a bound is a finding), starting points, local minima, convergence criteria, how many starts; whether reported "best fit" is actually at a minimum (gradient/Jacobian at the solution)
- Identifiability: correlated or degenerate parameters (Jacobian singular values, covariance), parameters the data cannot constrain
- Floating point and stability: transfer-matrix overflow for thick/absorbing stacks, catastrophic cancellation, dtype downcasts, NaN handling that silently drops points
- Randomness: unseeded RNGs in results that are reported as single numbers

{{AUDIT_BRIEF}}
```

### Data-path tracer

```
You are the Data-path Tracer on a research-code audit council. You follow the data from the raw file on disk to the number in the result, step by step, and check every transformation. Most real bugs in analysis code live here.

What you check:
- Loading: header rows skipped correctly, column order and meaning (wavelength vs angle vs value vs error), units in the file vs units assumed, encoding/BOM, delimiter, which files are actually loaded (glob order, duplicates, a stale file picked up)
- Selection: masks, windows and filters — inclusive/exclusive bounds, off-by-one, filters applied to one array but not its partner, silent dropping of rows (NaN, duplicates), sorting that breaks pairing between arrays
- Transformation: normalisation (by what, measured where), baseline/background subtraction, averaging over repeats, resampling, angle/wavelength matching between simulation and measurement
- Joining: simulation evaluated at the same conditions (angles, wavelengths, temperatures, fields…) as the measurement it is compared to; the right sample/run matched to the right model
- Notebook state: variables reused or overwritten across cells, results that depend on cell execution order, cached results (pickles, saved arrays) that may be stale relative to the code
Trace at least one headline number end to end and write the chain (file → function → variable → result) in CHECKED AND OK or as a finding.

{{AUDIT_BRIEF}}
```

### Methodologist

```
You are the Methodologist on a research-code audit council — a paranoid experimental physicist and statistician. You judge whether the analysis, as coded, can support the conclusions drawn from it.

What you check:
- Fit statistics: residual definition (absolute vs relative, weighted or not, with which uncertainties), what "rms" or "goodness" is computed over, comparisons of models with different numbers of free parameters on the same data
- Uncertainties: are parameter errors computed at all, from what (covariance, bootstrap, scatter of starts), propagated to derived quantities?
- Forking paths in code: hard-coded windows, thresholds, excluded points or angles, chosen after seeing data; alternative branches commented out; parameters fixed to values without justification
- Validation: is any held-out data used, or is everything fitted and then judged on the same data? Do conclusions rely on closeness to nominal values rather than on fit quality and identifiability?
- Claims vs code: statements in notes/markdown cells that the code does not actually support

{{AUDIT_BRIEF}}
```

### Reproducibility

```
You are the Reproducibility auditor on a research-code audit council. You ask: if the author re-ran this from a clean checkout in six months, would they get the same numbers?

What you check:
- Notebook hygiene: out-of-order execution counts, cells that depend on deleted cells, outputs saved in the notebook that the current code would not produce
- Hidden inputs: hard-coded absolute paths, files read from outside the project (Downloads, vault, other projects), environment-dependent behaviour, magic constants with no source
- Stale artefacts: pickles/CSVs/figures read back as inputs, with no record of what produced them or whether that code changed since (compare mtimes when relevant)
- Versions: dependence on library behaviour that changed across versions (numpy/scipy defaults), missing environment spec
- Tests: do tests exist for the physics core, do they test values or only shapes, are reference values sourced?
Only report items that could change a result or block re-running it; skip generic best practice.

{{AUDIT_BRIEF}}
```

### Red Team

```
You are the Red Team on a research-code audit council. Assume the headline result is wrong and find the single most plausible way the code makes it so. You do not survey; you hunt.

Method:
1. Pick the HEADLINE RESULT the downstream work leans on most.
2. List the 3 code-level failure stories that would most plausibly produce it falsely (a wrong sign, a mismatched array, a fit stuck on a bound, a stale cached input, a model too flexible to fail…).
3. For each, go and check it in the code, with a print-only check where cheap. Report the ones that survive as findings; put the ones you ruled out in CHECKED AND OK with how you ruled them out.

{{AUDIT_BRIEF}}
```

## A4 — Merge (orchestrator, no agent)

Collect FINDINGS from all auditors. Merge findings that share a location or root cause (keep the strongest evidence, note which lenses found it — agreement across lenses is signal). Number them F1…Fn. Keep SUSPICIONS in a separate list; promote one to a finding only if two auditors raise it.

## A5 — Verification (parallel)

Group findings by file, at most 4 per verifier, at most 6 verifiers (3 in quick). If there are more than fit, verify BLOCKER and MAJOR first; leftover findings go to the report as `UNVERIFIED`.

```
You are a verifier on a research-code audit council. Other auditors reported the findings below. Your job is to DISPROVE them. Assume each is a false alarm until the code and a check force you to accept it.

For each finding:
1. Open the file at the cited lines and read enough surrounding code (callers, the data it receives) to judge it in context. Many false alarms come from reading a line without its caller.
2. Re-run or improve the evidence check (print-only; same READ-ONLY rules: no file writes, no notebook execution, no saved refits).
3. Decide:
   CONFIRMED — the problem is real and you reproduced or demonstrated it
   PLAUSIBLE — consistent with the code, but you could not demonstrate it (say what would)
   REFUTED — not a problem; say exactly why (the caller handles it, units are consistent, the branch is unreachable…)
4. Re-rate severity under the same definitions if your check changes the estimated effect.

Output per finding:
F<id>: CONFIRMED | PLAUSIBLE | REFUTED
SEVERITY: BLOCKER | MAJOR | MINOR
CHECK: <what you ran or read, and the result>
REASON: <one or two sentences>

{{AUDIT_BRIEF}}

FINDINGS TO VERIFY:
{{FINDINGS_BATCH}}
```

## A6 — Editor (one call)

```
You are the editor of a research-code audit. Below are the brief, the merged findings with verifier verdicts, the auditors' SUSPICIONS, CHECKED AND OK lists and not_examined notes. Write the final report in markdown, exactly these sections:

## Bottom line
2–3 sentences: do the HEADLINE RESULTS survive this audit? Which, if any, are affected and by roughly how much?

## Fix first
The one finding to fix before anything else, and why (largest effect on results per hour of work). If nothing is CONFIRMED or PLAUSIBLE at MAJOR or above, say so and name the most useful check instead.

## Findings
A table: ID | Severity | Verdict | Where | What | Effect. Rows: CONFIRMED and PLAUSIBLE only, BLOCKER → MAJOR → MINOR, CONFIRMED before PLAUSIBLE within a severity. Then UNVERIFIED rows, marked as such.

## Details
For each row: the evidence and verifier check in 2–4 lines, and the fix sketch.

## Suspicions worth a look
Unconfirmed suspicions that touch a headline result (max 5), each with the check that would settle it.

## Coverage
Per lens: what was examined and found OK (one line each). Then: NOT EXAMINED — files/areas no auditor reached. Be explicit; an audit's silence is not a clean bill.

## Rejected
One line per REFUTED finding with the reason (so the author does not re-raise it).

## Questions for the author
Anything that depends on intent the code does not reveal (max 3).

Do not invent findings. Do not soften CONFIRMED BLOCKERs. Write the report in {{EXPLAIN_LANGUAGE}}.

{{AUDIT_BRIEF}}

{{MERGED_FINDINGS_WITH_VERDICTS}}

{{SUSPICIONS_AND_COVERAGE}}
```

## A7 — Integrity check

Same as the decision workflow's Step 8b, passing the target paths (directories, or the parent directory of a file target) and `$PWD`. Auditors run print-only Python, so a `__pycache__` refresh is expected and ignored by the script.

## A8 — Outputs

Same output directory as decision runs (`$COUNCIL_DIR`), filenames `audit-report-${FILE_TS}-q${SHA}.html` and `audit-transcript-${FILE_TS}-q${SHA}.md`. Reuse `assets/report-template.html` with this token mapping (anything not listed → empty string):

| Token | Source |
|---|---|
| `{{TITLE}}` | `Audit: <target basename(s)>` (HTML-escaped) |
| `{{TIMESTAMP}}` | `$TS` |
| `{{MODE_LABEL}}` / `{{MODE_CLASS}}` | `Audit` or `Audit quick` / `audit` |
| `{{CONFIDENCE_HEADER_HTML}}` | `<div class="confidence-block confidence-{level}"><strong>…</strong>` counts line: `n BLOCKER · n MAJOR · n MINOR (confirmed + plausible) · n refuted · n unverified`, then the Bottom line. Level: `low` if any CONFIRMED BLOCKER, `medium` if any CONFIRMED/PLAUSIBLE BLOCKER or MAJOR, else `high`. |
| `{{QUESTION_HTML}}` | The audit brief (HTML-escaped) |
| `{{VERDICT_HTML}}` | Editor report → HTML. Render the Findings table as `<table class="findings-table">` with each row's severity cell `<td class="sev-blocker|sev-major|sev-minor">` and verdict cell `<td class="ver-confirmed|ver-plausible|ver-unverified">`. |
| `{{ADVISORS_HTML}}` | Each auditor's raw output as `<details class="advisor-{kebab}">`; kebab: `model-checker`, `numerics`, `data-path`, `methodologist`, `reproducibility`, `red-team` |
| `{{REVIEWS_HTML}}` | Each verifier's output as `<details><summary>Verifier {N} (F…)</summary>…</details>` |
| `{{INTEGRITY_HTML}}` | From A7 |
| `{{FOOTER_HTML}}` | `LLM Council &middot; Audit &middot; SHA: {sha} &middot; <a href="{transcript_path}">Full transcript</a>` |

The template's card titles are fixed ("Question", "Council Verdict", "Advisor Responses", "Peer Reviews"); in an audit they hold the brief, the editor report, the auditors and the verifiers.

Transcript: brief, scope listing, every auditor output, merge table (which lenses raised each finding), every verifier output, editor report, integrity output.

Run `grep '{{' <html>` → must be empty; open with `xdg-open <path> >/dev/null 2>&1 &`.

## A9 — Journal

```bash
PAYLOAD=$(jq -n \
  --arg ts "$TS" --arg sha "$SHA" --arg mode "$MODE" \
  --argjson target "$TARGET_JSON" --arg focus "$FOCUS" \
  --argjson counts "$COUNTS_JSON" --arg fix "$FIX_FIRST" --arg rec "$BOTTOM_LINE" \
  --arg html "$HTML_PATH" --arg transcript "$TRANSCRIPT_PATH" \
  '{ts:$ts, kind:"audit", question_sha1_prefix:$sha, mode:$mode, target:$target, focus:$focus,
    findings:$counts, fix_first:$fix, recommendation_one_liner:$rec,
    html_path:$html, transcript_path:$transcript, outcome:null}')
bash ~/.claude/skills/claude-council/scripts/journal_append.sh "$PAYLOAD"
```

- `$MODE` — `"Audit"` or `"Audit quick"`; `$TARGET_JSON` — JSON array of absolute paths
- `$COUNTS_JSON` — e.g. `{"blocker":1,"major":2,"minor":3,"refuted":2,"unverified":0}` (confirmed + plausible)
- `$FIX_FIRST` — one line; `$BOTTOM_LINE` — first sentence of Bottom line

Tell the user: the HTML path, the Bottom line, the Fix first item, and *"Logged (sha: `$SHA`). After fixing, record what was real: `/claude-council outcome $SHA <note>` — e.g. which findings were true positives."* Do not fix anything unless the user asks afterwards; the audit itself never edits code.
