# Review mode — scientific text review (Spanish)

Invocation: `/claude-council review <file> [<file> ...] [-- focus text] [quick]`

Six reviewers read a thesis chapter, paper, abstract, poster or talk, each through one lens. Comments on facts, numbers and claims are verified by agents who try to refute them; style comments are not. An editor merges everything into comments **in document order**, so the author can work through the file top to bottom.

The text is in **Spanish**. Replacement text (SUGGESTION) is always in Spanish, in the author's register; explanations (ISSUE, EVIDENCE) are in English unless the user asks otherwise.

All `Agent()` calls use `subagent_type="council-advisor"` (read-only), with the same fallback and `SANDBOX:` rules as the decision workflow. Reviewers never edit the text; the user applies the changes.

| Mode | Reviewers | Calls |
|---|---|---|
| Review | 6 | 6 + 0–3 verifiers + 1 editor (≈ 7–10) |
| Review quick (`quick` suffix) | 3: Hostile referee, Numbers checker, Language & style | 3 + 0–2 verifiers + 1 editor (≈ 4–6) |

---

## R1 — Scope

A file is required; if none was given, ask once. Accepted: `.md`, `.tex`, `.txt`, `.pdf`. Anything else (`.odt`, `.odp`, `.docx`): ask the user to export to PDF.

```bash
wc -w <file.md|.tex|.txt>
pdftotext <file.pdf> - | wc -w
```

Limit **15 000 words** per run (about one chapter). Over the limit: AskUserQuestion offering the chapters/sections (from headings) as narrower targets. Note the count in the transcript.

## R2 — Brief

```bash
REVIEW_KEY='review:/abs/file1 /abs/file2'
SHA=$(printf '%s' "$REVIEW_KEY" | sha1sum | cut -c1-8)
bash ~/.claude/skills/claude-council/scripts/journal_search.sh "$REVIEW_KEY"
python3 -I ~/.claude/skills/claude-council/scripts/integrity_check.py start "$SHA"
```

Write `{{REVIEW_BRIEF}}`:

```
TARGET: <absolute paths, word count>
DOCUMENT: <thesis chapter | paper | abstract | poster | talk slides> — <title / section>
AUDIENCE: <e.g. thesis jury (jurado) of physicists, conference poster session, supervisor>
LANGUAGE: Spanish (suggestions in Spanish; explanations in English)
SOURCES: <absolute paths of notebooks, notes, data, reports the text's numbers and figures come from — from the user, the project notes, or a quick Glob; "none known">
STYLE RULES: <university/journal/conference template or style guide if found; decimal separator and unit conventions already used in the text>
FOCUS: <user's focus text, or "none — full review">
PRIOR REVIEWS: <journal hits for this target, with outcome, or "none">
```

If SOURCES cannot be found, ask the user once — the Numbers checker is much weaker without them.

## R3 — Reviewers (single turn, parallel)

Each prompt = lens section + REVIEW RULES + COMMENT FORMAT, with `{{REVIEW_BRIEF}}` substituted. The Outsider gets only the text: no SOURCES, no other files.

### Shared: REVIEW RULES

```
REVIEW RULES:
- Read the whole TARGET first. For a PDF poster or slides, read it as pages (Read tool) so you see figures and layout, not only extracted text.
- Every comment quotes the exact text it is about (≤ 25 words, copied verbatim) so the author can search for it, plus the line number (.md/.tex/.txt) or page (.pdf).
- READ-ONLY: never edit any file. Print-only checks (python3 -c, grep, pdftotext <file> -) are fine.
- Severity: BLOCKER = factually wrong, a number that disagrees with its source, or a claim the jury/referees would reject; MAJOR = unsupported, ambiguous or misleading in a way that changes what the reader believes; MINOR = wording, typos, formatting.
- Stay in your lens. At most 20 comments, most severe first. A pattern that repeats (same anglicism, same unit formatting slip) is ONE comment listing where it occurs, not one per instance.
- Suggestions are concrete: give the replacement text in Spanish in the author's own register, or the exact action (add the uncertainty, cite X, move the paragraph). Do not rewrite whole paragraphs unless the paragraph is wrong.
- Use web search only to check a published value, a reference, or a usage rule (RAE, Fundéu); name the source.
```

### Shared: COMMENT FORMAT

```
=== COMMENTS ===
COMMENT <n>
SEVERITY: BLOCKER | MAJOR | MINOR
WHERE: /absolute/path:line  (or page N)
QUOTE: "<exact text>"
ISSUE: <one sentence>
SUGGESTION: <replacement text in Spanish, or the action>
EVIDENCE: <for facts/numbers: the source file:line/value or reference you checked; "n/a" for style>

=== CHECKED AND OK ===
- <what you verified and found correct>   (at least 3; coverage record)

=== CONFIDENCE ===
confidence: high | medium | low
not_examined: <sections/pages in your lens you did not get to>
```

### Hostile referee (jurado escéptico)

```
You are the Hostile Referee on a text-review council: the jury member who arrives wanting to find the weak point of this thesis (or the referee who wants to reject the paper). You read as an expert in the field.

What you look for:
- Overclaiming: "demostramos", "por primera vez", "óptimo", "excelente acuerdo" without the evidence to back the strength of the word
- Missing context: no comparison with literature or prior work where a jury would expect it; results presented without saying how they compare to the state of the art or to the design target
- Weak justification: design choices, approximations or parameter values stated without why
- Logical gaps: conclusions that do not follow from the results shown; results that appear in conclusions but not in the body
- Scope: what the text implies was done vs what was actually done
Also list, at the end under === LIKELY JURY QUESTIONS ===, the 5 hardest questions you would ask at the defense based on this text, each with the passage that provokes it.

{{REVIEW_BRIEF}}
```

### Methodologist

```
You are the Methodologist on a text-review council — a paranoid experimental physicist and statistician. You check that every empirical claim in the text is backed by evidence the text shows or cites.

What you check:
- Each quantitative claim: is there an uncertainty, and is it stated what kind (std, standard error, fit error, instrument resolution)?
- Each comparison (measurement vs simulation, sample A vs B): is the comparison criterion stated, and is the difference larger than the uncertainty?
- Generalisation: one device/sample/run presented as typical; fits judged "good" without a metric
- Method description: could someone reproduce the measurement or analysis from the text (instrument, settings, fit model, free parameters, data excluded and why)?
- Figures: axes labelled with units, error bars present or their absence explained, the figure actually shows what the text says it shows

{{REVIEW_BRIEF}}
```

### Numbers checker

```
You are the Numbers Checker on a text-review council. You check every number in the text against its source and against itself.

Method:
1. List every number with a unit, every percentage, every figure/table/equation reference and every sample/wafer label in the TARGET.
2. For each, find the source in SOURCES (notebook outputs, notes, data files, reports) and compare. Report mismatches as BLOCKER with both values and the source file:line or cell.
3. Internal consistency: the same quantity must have the same value, unit and number of significant figures everywhere (abstract, body, captions, conclusions). Rounding consistent with the stated uncertainty.
4. Formatting: SI units with a space between number and unit, unit symbols upright, one decimal separator convention throughout (whichever the text mostly uses), ranges and uncertainties written consistently ("970 ± 2 nm").
5. References: every "Figura N", "Tabla N", "Ec. (N)" and citation points to something that exists and says what the text claims.
Put numbers you could not trace to any source under CHECKED AND OK as "unverified: <number> — no source found".

{{REVIEW_BRIEF}}
```

### Physics

```
You are the Physics reviewer on a text-review council — a senior physicist checking that the physics in the text is correct and correctly stated.

What you check:
- Equations: correct, dimensionally consistent, every symbol defined at first use, notation consistent across the text and with the cited sources
- Concepts: definitions (stopband, finesse, Q factor, quarter-wave, effective index…) stated correctly; mechanisms explained correctly (not only named)
- Approximations: stated, and used within their range of validity
- Terminology: standard Spanish physics terms (or the English term in italics where no standard Spanish one exists), used consistently — one name per concept
- Physical plausibility of every reported value (orders of magnitude, signs, trends)

{{REVIEW_BRIEF}}
```

### Outsider reader (lector externo)

```
You are the Outsider Reader on a text-review council: a capable physicist from another field (say, particle physics) reading this text with no background in its subfield and no access to anything but the text. You do not open any other file.

Report, as comments:
- Where you got lost, and what you needed to know at that point
- Acronyms and jargon used before they are defined (or never defined)
- Paragraphs whose point you could not state in one sentence
- Structure: sections whose purpose is unclear, ordering that forces you to read ahead, figures referenced long before or after they appear
- What you think the main result is, in one sentence, under === MY ONE-SENTENCE SUMMARY === — if it does not match what the author intends, the text has a problem

{{REVIEW_BRIEF}}
```

### Language & style (Spanish)

```
You are the Language & Style reviewer on a text-review council: an editor of scientific Spanish. You keep the author's voice and fix what a careful reader or jury would notice.

What you check:
- Ortografía and grammar per current RAE norms: tildes (including "solo" and demonstratives without tilde), concordancia, punctuation (no comma between subject and verb), dequeísmo/queísmo, gerundio de posterioridad
- Anglicisms and calques common in physics writing: "asumir" (for suponer), "eventualmente" (for finalmente), "remover", "chequear", "en orden a", "jugar un rol", "aplicar" (for solicitar), "basado en" overuse, "es por esto que", English word order with adjectives, unnecessary passive "fue medido" (prefer "se midió")
- Register: consistent person (impersonal "se" or plural "medimos" — whichever the text uses most), no colloquialisms, sentences over ~40 words split
- Terminology: one term per concept throughout; English terms in italics when kept; acronyms in the form chosen at first use
- Number and unit typography (coordinate with, do not duplicate, the Numbers checker: only flag style, not values)
Group repeated patterns into one comment with all locations.

{{REVIEW_BRIEF}}
```

## R4 — Merge (orchestrator, no agent)

Collect all comments. Merge comments on the same QUOTE (keep the best suggestion; note which lenses raised it). Number them C1…Cn in **document order**. Mark each as `fact` (claims, numbers, physics, references) or `style` (language, clarity, structure).

## R5 — Verification (fact comments only)

Verify BLOCKER and MAJOR `fact` comments; style comments and MINOR items are not verified. At most 4 per verifier, at most 3 verifiers (2 in quick); any left over are marked `UNVERIFIED`.

```
You are a verifier on a text-review council. Other reviewers flagged the passages below as factually wrong, unsupported or inconsistent with their sources. Your job is to DISPROVE each flag. Assume it is a false alarm until the text and the sources force you to accept it.

For each comment:
1. Read the quoted passage in context (the paragraphs around it, the figure or table it refers to).
2. Open the cited source (SOURCES file, reference, equation) and check the value or claim yourself. Print-only checks only; no file edits.
3. Decide: CONFIRMED (the problem is real — show both values / the contradiction) | PLAUSIBLE (consistent but not demonstrated — say what would settle it) | REFUTED (say exactly why: the text defines it later, the source agrees after rounding, the reviewer read the wrong cell…).
4. Re-rate severity if your check changes it.

Output per comment:
C<id>: CONFIRMED | PLAUSIBLE | REFUTED
SEVERITY: BLOCKER | MAJOR | MINOR
CHECK: <what you read or ran, and the result>
REASON: <one or two sentences>

{{REVIEW_BRIEF}}

COMMENTS TO VERIFY:
{{COMMENTS_BATCH}}
```

## R6 — Editor (one call)

```
You are the editor of a text review of a Spanish scientific document. Below are the brief, the merged comments (with verifier verdicts on fact comments), the reviewers' CHECKED AND OK lists, the referee's LIKELY JURY QUESTIONS and the outsider's ONE-SENTENCE SUMMARY. Write the final report in markdown, exactly these sections:

## Bottom line
2–3 sentences: is this text ready for its audience? What is the single biggest risk?

## Fix first
Up to 3 comments with the largest effect on how the text will be judged, and why.

## Comments in document order
A table: ID | Where | Severity | Lens | Quote | Suggestion. Include CONFIRMED, PLAUSIBLE, UNVERIFIED and style comments; exclude REFUTED. Mark UNVERIFIED in the Severity cell. Resolve conflicts between lenses (e.g. referee wants more detail, outsider wants less) by choosing one and saying why in a short note under the table.

## Recurring patterns
Style and formatting patterns that repeat, each with all locations — the author fixes these with search-and-replace.

## Likely jury questions
The referee's questions, deduplicated, with the passage that provokes each and, where the text already answers it, where.

## Does the main message land?
The outsider's one-sentence summary vs what the text intends to say.

## Coverage
What was checked (numbers traced to sources: n of m; sections read by each lens) and what was NOT examined.

## Rejected
One line per REFUTED comment with the reason.

Do not invent comments. Keep the author's voice in all suggestions. Suggestions in Spanish; explanations in English.

{{REVIEW_BRIEF}}

{{MERGED_COMMENTS_WITH_VERDICTS}}

{{COVERAGE_AND_EXTRAS}}
```

## R7 — Integrity check

Same as the decision workflow's Step 8b, passing the target's directory, each SOURCES directory and `$PWD`.

## R8 — Outputs

Output directory `~/Documents/Tesis/council/`, filenames `review-report-${FILE_TS}-q${SHA}.html` and `review-transcript-${FILE_TS}-q${SHA}.md`. Reuse `assets/report-template.html`; anything not listed → empty string:

| Token | Source |
|---|---|
| `{{TITLE}}` | `Review: <target basename(s)>` (HTML-escaped) |
| `{{TIMESTAMP}}` | `$TS` |
| `{{MODE_LABEL}}` / `{{MODE_CLASS}}` | `Review` or `Review quick` / `review` |
| `{{CONFIDENCE_HEADER_HTML}}` | `<div class="confidence-block confidence-{level}">` with counts `n BLOCKER · n MAJOR · n MINOR · n refuted · n unverified`, then the Bottom line. Level: `low` if any CONFIRMED BLOCKER, `medium` if any BLOCKER/MAJOR left, else `high`. |
| `{{QUESTION_HTML}}` | The review brief (HTML-escaped) |
| `{{VERDICT_HTML}}` | Editor report → HTML. The comments table as `<table class="findings-table">`; severity cells `sev-blocker` / `sev-major` / `sev-minor`; HTML-escape every QUOTE and SUGGESTION. |
| `{{ADVISORS_HTML}}` | Each reviewer's raw output as `<details class="advisor-{kebab}">`. Kebabs (reusing existing colours): Hostile referee → `red-team`, Methodologist → `methodologist`, Numbers checker → `data-path`, Physics → `model-checker`, Outsider reader → `outsider`, Language & style → `reproducibility`. Summary text is the reviewer's own name. |
| `{{REVIEWS_HTML}}` | Each verifier's output as `<details><summary>Verifier {N} (C…)</summary>…</details>`; empty if none ran |
| `{{INTEGRITY_HTML}}` | From R7 |
| `{{FOOTER_HTML}}` | `LLM Council &middot; Review &middot; SHA: {sha} &middot; <a href="{transcript_path}">Full transcript</a>` |

Transcript: brief, word count, every reviewer output, merge table, verifier outputs, editor report, integrity output. `grep '{{' <html>` must be empty; open with `xdg-open <path> >/dev/null 2>&1 &`.

## R9 — Journal

Same as audit mode's A9, with `kind:"review"`, `$MODE` = `"Review"` or `"Review quick"`, `$COUNTS_JSON` from the comments (`{"blocker":…,"major":…,"minor":…,"refuted":…,"unverified":…}`), `$FIX_FIRST` = the first Fix-first item, `$BOTTOM_LINE` = first sentence of Bottom line.

Tell the user: the HTML path, the Bottom line, the Fix-first items, and *"Logged (sha: `$SHA`). Record which comments were useful: `/claude-council outcome $SHA <note>`."* Do not edit the document unless the user asks afterwards.
