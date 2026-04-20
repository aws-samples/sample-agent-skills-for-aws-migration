# Requirements Document Authoring Prompt

## Context

You are helping design an evaluation harness for a Claude Code plugin. The prior work has been done in two stages:

1. **Problem definition** — a document that framed why we need this harness and what it should achieve (not included here; this document replaces it)
2. **Codebase exploration** — a report that surveys the plugin's actual structure, execution flow, schemas, hard rules, and testing seams, with file-and-line citations back to the source

The exploration report is attached to this session. **Read it in full before you begin.** It contains the plugin-specific signal that must ground everything in the requirements document.

Your task is to produce a **requirements document** for the evaluation harness. This document will be used to:

- Drive implementation decisions (what to build, in what order)
- Anchor PR review for the harness itself (is this change in scope?)
- Brief new contributors on the harness's purpose and constraints

---

## What the Evaluation Harness Must Do

This section is decided context — **do not re-derive it from first principles.** Your job is to take these decisions as inputs and produce a requirements document that operationalizes them, grounded in what the exploration report actually found.

### The model: honor-based, contributor-run evaluation

Contributors run evaluation locally against their own Claude credentials. The runner produces a results artifact. The contributor commits that artifact to their PR. CI validates the artifact **without making any Claude API calls of its own.** This is a deliberate trade-off: we accept that a motivated actor could fabricate results; we mitigate via structural binding of results to commit SHA and file hashes, and via cultural norms.

### The structure: fixtures, invariants, distributions

- A **fixture** is a hand-crafted input (a directory of Terraform files plus any seed files needed to bypass interactive checkpoints) designed to exercise specific plugin behaviors.
- A **hard invariant** is an assertion that must hold on every correct run. Invariant failures block merge.
- A **soft observation** (or distribution) is a property that should hold on average across runs. These are informational, not blocking.

### The validation layers

- **Layer 1 — structural checks:** fast, deterministic, no Claude calls. Schema validity, cross-reference integrity, required-phrase presence in prompts. Runs on every PR.
- **Layer 2 — fixture evaluation:** contributor-run. Results artifact validated by CI.

### The contributor flow

```
1. Contributor edits a prompt file or schema
2. Runs a single command (likely mise-based) that executes fixtures locally
3. Runner produces .eval-results.json (or equivalent) in repo root
4. Contributor commits it to the PR
5. CI validates the artifact (structure, SHA binding, invariants passing)
6. CI passes → PR is mergeable
```

### Constraints

- CI runs on GitHub-hosted runners, no self-hosted infrastructure
- The repo likely already uses `mise` for tasks, `dprint` for formatting, etc. — integrate, don't replace
- Running a single fixture should cost well under $1 on a contributor's Claude usage
- Evaluation failures must produce actionable error messages, not raw invariant dumps

---

## Your Task

Produce a requirements document with the structure below. **Every substantive claim must be traceable to something in the exploration report** — either by direct quote, by referencing a file path and line number, or by citing a section of the exploration. If the exploration report does not support a claim, either remove the claim or flag it explicitly as a design decision that needs confirmation.

### Required sections

**1. Problem statement**
Why this harness exists. Describe the plugin briefly (paraphrasing from the exploration report), the validation gap, and what shipping the harness will achieve. Keep this to one page at most.

**2. Business outcomes**
The concrete outcomes the harness produces. Distinguish primary outcomes (the main thing) from secondary outcomes (nice follow-ons). Also state explicit non-goals — what the harness is not trying to be. This section frames the scope for future arguments about what to include.

**3. Source code context**
A digest of the exploration report focused on what's relevant for testing. Organize around:

- Plugin architecture — what kind of plugin is it, how is it structured, where do the files live
- Execution flow — from activation to completion
- Interactive checkpoints and bypass mechanisms — critical for non-interactive testing
- Outputs and schemas — what files the plugin writes, what invariants those files already have in the source
- Hard rules and anti-patterns documented in the source — with citations

Include **actual file paths** from the exploration report. Do not guess or paraphrase paths.

**4. What the harness validates**
Be specific about the two layers. For layer 1 (structural), list the checks. For layer 2 (fixture-based), describe the model — fixtures, invariants, distributions — and explain how each maps to what the plugin actually does.

**5. Proposed first fixture**
Base this on what the exploration report recommended. Include:

- Inventory of resources with rationale for each ("this resource is included because it tests [specific plugin behavior]")
- Expected structural outcome (resource counts, cluster counts, etc.) — only include properties the exploration report grounds in actual plugin logic
- Pre-seeded files needed to bypass interactive checkpoints
- Why this composition is small enough to hand-verify and rich enough to exercise core behaviors

**6. Proposed invariants**
Split into hard (block merge) and soft (informational). For each invariant, cite the specific rule in the plugin source that justifies it. An invariant without a traceable source is not a requirement; it's an opinion.

Group invariants by which pillar/phase/skill they test.

**7. Contributor workflow specification**
The concrete flow a contributor follows. Include:

- Commands they run
- What the results artifact looks like (schema sketch)
- How the artifact is bound to the commit (SHA matching, file hashing)
- What happens when validation fails — what error messages look like

**8. CI validation specification**
What the CI job does. This should be straightforward once the contributor workflow is specified — CI is just "validate the artifact is real and passes." Be explicit about what CI does and does not do.

**9. Open questions and design decisions**
Every ambiguity the exploration report flagged. Every trade-off that's still open. Every place where the contributor experience hasn't been pinned down. The goal of this section is to make the remaining decisions visible, not hidden.

Examples of things that likely belong here:

- Whether the first fixture tests one phase or multiple phases
- How to handle dynamic values (e.g., cluster IDs that are generated by the plugin) in pre-seeded files
- Multi-run sampling — how many runs per fixture
- Whether to pre-cache deterministic-phase outputs to reduce contributor cost
- How fixture evolution works when new fixtures are added
- Escape hatches for intentional baseline changes

For each open question, describe the options and the trade-offs, but do not decide. This document is input to a decision process, not the output of one.

**10. Success criteria**
How will we know the harness is working? Propose a small set of measurable outcomes — not aspirations, but things we can check. Examples: false-positive rate under some threshold; at least one regression caught within N months; contributor eval time under N minutes.

**11. Implementation sequence (proposed)**
A sketch of how the harness gets built incrementally. Not a commitment, just a proposal that gives the team a starting point. Week-by-week or phase-by-phase. Make it small and boring — the first deliverable should be so unambitious it's almost embarrassing.

### Optional appendices

- **Glossary** — define terms that recur (fixture, invariant, distribution, pillar, secondary role, etc.) if the plugin uses domain-specific vocabulary
- **File reference** — a table of plugin files and their roles, for quick lookup during design discussions

---

## Ground Rules

**Traceability is non-negotiable.** Every invariant, every schema assertion, every "the plugin does X" statement must cite the exploration report or the source code. Reviewers of this document will trust it only to the extent that claims can be verified. Unsupported claims erode that trust faster than anything else.

**Distinguish facts from decisions from opinions.**

- A _fact_ is something the exploration report directly establishes (cite it)
- A _decision_ is something the problem statement already settled (cite the decision)
- An _opinion_ is a judgment you're making — flag these explicitly ("I recommend X because Y"), and put genuinely open opinions in Section 9 rather than embedded in other sections

**Conservatism over cleverness.** The first version of the harness will be small and obvious. Resist the urge to propose sophisticated mechanisms. If you find yourself designing a baseline-update DSL or a fixture-auto-selection algorithm, stop — put it in Section 9 as an open question.

**The exploration report is the source of truth about the codebase.** Do not import knowledge about Claude Code plugins generally that isn't supported by the exploration. If the exploration says the plugin has three skills, do not write about pillars even if the term makes more sense. Match the exploration's vocabulary exactly.

**No generic LLM-evaluation advice.** Everything in this document should be specific to this plugin. If a requirement could apply equally to any LLM-based tool, it probably doesn't belong here.

**If the exploration is ambiguous, say so.** Do not resolve ambiguity silently. If the exploration report says "the plugin appears to have three phases but one is underdocumented," your requirements document should reflect that uncertainty, not paper over it.

**Output format.** A single markdown file. Section headers as specified. Use fenced code blocks for file paths, commands, and JSON snippets. Include a table of contents if the document exceeds ~15 pages.

---

## Why This Document Matters

This is the artifact that gets reviewed, disputed, and eventually approved by the team. It's also the reference the implementer will return to when they're deep in code and unsure whether a mechanism belongs in scope. Quality here compounds — a precise requirements document produces a precise implementation; a vague one produces a system nobody quite trusts.

The goal is not to make every decision. The goal is to make every decision **explicit** — either decided-and-cited, or flagged-as-open-in-section-9. A document that appears decisive by hiding open questions is worse than one that's honestly uncertain.

Read the exploration report in full before writing. Don't start drafting sections in isolation — the document must hang together as a coherent argument from problem through solution through open questions.
