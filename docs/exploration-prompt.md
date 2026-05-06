# Problem Statement: Evaluation Harness for a Claude Code Plugin

## Context

This is a pre-work document for a Claude Code session. The session's goal is to explore a local codebase — a Claude Code plugin for GCP-to-AWS infrastructure migration — and produce a requirements document for an evaluation harness.

The plugin lives locally on disk. You (Claude Code) have filesystem access to it. **Start by exploring the codebase before doing anything else.** This document describes what to look for and why, not what the code contains.

---

## The Problem

### What the plugin does (at a high level)

A Claude Code plugin called `migration-to-aws` helps users migrate GCP Terraform infrastructure to AWS. A user points it at a directory of `.tf` files, and the plugin produces a structured migration plan — an inventory of GCP resources, a mapping of each resource to its AWS equivalent with reasoning, and cost estimates.

The plugin is installed via the Claude Code plugin marketplace:

```
/plugin marketplace add <this-repo>
/plugin install migration-to-aws@<this-repo>
```

### Why validation is hard

This plugin is not traditional code. Its behavior is almost entirely determined by natural-language instructions written in markdown. When Claude loads the plugin, it reads these markdown files as prompts and follows them. The "source code" is a set of carefully-crafted documents that steer Claude's reasoning.

When a contributor submits a PR that edits one of these markdown files, they are changing the prompt. This means:

- Unit tests don't apply — there are no functions to test
- Output diffs are noisy — two valid runs produce different wording
- Subtle prompt regressions are invisible — removing a single "CRITICAL" directive can silently degrade behavior
- Schema validation catches structural issues but not behavioral ones

### The validation gap today

The repo has static checks (markdown linting, formatting, security scanning), but **nothing exercises the plugin's actual behavior.** A PR that deletes a mandatory instruction from a prompt file would pass all existing CI.

### What we want to build

An evaluation harness that:

1. **Catches prompt regressions before merge.** Some plugin behaviors are documented as non-negotiable (e.g., "this phase must never mention AWS services"). These should become executable assertions.

2. **Works without running Claude API calls in CI.** API costs on every PR are unbounded; the team will not commit to bearing them. The design direction is an **honor-based, contributor-run** model: contributors run evaluation locally against their own Claude credentials, commit the results artifact to the PR, and CI validates the artifact.

3. **Uses golden fixtures.** A fixture is a hand-crafted Terraform project designed to exercise specific plugin behaviors, paired with a set of invariants (hard assertions) and distributions (soft observations). Running a fixture means running the plugin end-to-end against that Terraform project and checking whether the output satisfies the invariants.

4. **Respects the interactive nature of the plugin.** The plugin has mandatory interactive checkpoints where it waits for user input. Automated testing needs to work around these — likely by pre-seeding certain files that bypass the checkpoints.

---

## Your Task (This Claude Code Session)

Explore the local plugin codebase and produce a document that will feed into a subsequent requirements-writing session. The document should cover:

1. **Actual file layout.** What files exist, where they live, what each one does.
2. **The plugin's architecture and execution model.** How the orchestrator invokes pillars/skills, what files it reads, what files it writes, in what order.
3. **Interactive checkpoints.** Where does the plugin stop and wait for user input? What files, if pre-seeded, would bypass those checkpoints?
4. **Output schemas.** What structured files does the plugin produce? What invariants does each output file have according to its instructions?
5. **Documented anti-patterns and forbidden behaviors.** The prompts contain explicit "do not do X" rules. These are the highest-value test targets — they guard against known failure modes.
6. **The seams where testing could hook in.** Identify the specific points where an evaluation harness can:
   - Invoke the plugin non-interactively
   - Pre-seed inputs to control execution
   - Observe outputs without interfering with the run
7. **Candidate first fixture.** Based on what the plugin handles, propose a minimal Terraform project that would exercise core plugin behaviors without being so large that outputs can't be hand-verified.
8. **Candidate invariants.** Based on documented rules in the prompts, propose a set of assertions that a correct run must satisfy. Distinguish "hard invariants" (always hold) from "soft observations" (vary across runs but should stay within bounds).

---

## How to Explore

### Step 1: Understand the plugin's shape

Start with the repo root. Look for:

- A plugin manifest (`.claude-plugin/` directory, plugin.json, or similar). This tells Claude Code what the plugin is and how to load it.
- A marketplace manifest if the repo is a marketplace (lists multiple plugins).
- A top-level README that describes the plugin to humans.
- Directory structure — skills, agents, commands, hooks, MCP servers. Claude Code plugins can contain any of these.

Map out the directory tree and note what category each file falls into.

### Step 2: Find the entry point

Claude Code plugins typically have one of these shapes:

- **Agent skills** — directories under `skills/` or similar, each with a `SKILL.md` that has YAML frontmatter describing when the skill should activate
- **Slash commands** — files under `commands/` invoked via `/commandname`
- **Subagents** — specialized agents under `agents/`
- **MCP servers** — configured via `mcp.json` or similar, provide tools
- **Hooks** — fire on specific events

For this plugin, identify which of these the plugin uses. Look specifically for:

- An orchestrator file (possibly named `POWER.md`, `SKILL.md`, or similar) that coordinates everything
- The trigger phrases or conditions that activate the plugin (usually in YAML frontmatter)
- Whether the plugin has multiple phases/pillars and how they're wired together

### Step 3: Read the orchestrator carefully

The orchestrator is the heart of the plugin. Read it end-to-end and extract:

- What does it do on activation?
- What files does it scan in the user's workspace?
- What menu or options does it present?
- What interactive checkpoints does it have? Look for strong language like `MANDATORY`, `WAIT`, `DO NOT SKIP`, `STOP HERE`.
- What steering files does it load, and when?
- What files does it write, and where?

Pay attention to rules about output locations. The plugin likely has a convention like "always write outputs to `migration-output/`" — this matters for how testing is set up.

### Step 4: Read each pillar/skill in turn

For each of the plugin's sequential phases, document:

- **Inputs it expects** (files read from disk)
- **Outputs it produces** (files written to disk)
- **Processing logic** (what it does in between) — at the level of the steps it follows
- **Schemas for structured outputs** (JSON files typically have schemas either inline in the prompt or in a separate `schemas/` directory)
- **Hard rules** — anything with "MUST", "NEVER", "CRITICAL", "FORBIDDEN" is a candidate invariant
- **Anti-patterns** — the prompts often show explicit wrong-way examples ("❌ DO NOT do this"). These are gold for test design.
- **Known failure modes the prompts guard against** — if the prompt says "if you find yourself writing X, STOP and delete it," there's a history of the model doing exactly that. Tests should watch for X.

### Step 5: Find the reference files and schemas

Plugins often have two kinds of supporting material:

- **Reference files** — domain knowledge the orchestrator pulls in on demand (e.g., mapping tables from one cloud's services to another)
- **Schemas** — JSON Schema files that define the exact structure of output files

Catalog both. For each schema, note what output file it governs.

### Step 6: Identify interactive seams

For the harness to run the plugin non-interactively, we need to bypass user prompts. Look specifically for:

- Statements like "if file X already exists, skip this step" — these are bypass points
- Environment variables or flags the plugin respects
- Default values that can be pre-seeded

Document every bypass mechanism you find. If there aren't any (or they're inadequate), flag that — it may mean the plugin itself needs a small change to support testing.

### Step 7: Note anything existing around testing

Look for:

- A `tests/` or `test/` directory
- Existing fixtures, examples, or sample inputs in the repo
- Any CI workflow files (`.github/workflows/*.yml`) that already run checks
- Documentation in CONTRIBUTING.md about how changes are validated
- Tooling config (mise, pre-commit, etc.) that already defines tasks

Existing infrastructure should be reused where possible.

---

## What to Produce

Write a single markdown document covering what you found, organized as:

1. **Plugin overview** — what it does, how it's structured, key directories
2. **Execution flow** — from activation to completion, phase by phase
3. **Interactive checkpoints and bypass mechanisms** — where the plugin stops and how to get past that for testing
4. **Outputs and their schemas** — every file the plugin writes and its structural rules
5. **Hard rules and anti-patterns** — the documented invariants we can test against, with file-and-line citations so they can be traced back to the source
6. **Testing seams** — specifically where an evaluation harness can intervene
7. **Proposed first fixture** — a minimal Terraform project, justified by which plugin behaviors it exercises
8. **Proposed invariants** — a concrete list, split into hard (always hold) and soft (distributional), each traceable to a specific rule in the prompt source
9. **Open questions** — things you noticed that are ambiguous, risky, or worth discussing before finalizing requirements

Include **actual file paths and line numbers** for anything you cite. The next session will use this to write a requirements document, and traceability from claims back to source lines matters.

---

## Ground Rules for the Exploration

- **Do not modify files.** This is a read-only exploration.
- **Do not run the plugin.** We're not executing it, just reading it.
- **Do not invent details.** If something is unclear from the code, say so explicitly in the "Open questions" section rather than guessing.
- **Prefer direct quotes over paraphrases** when citing rules or anti-patterns. The exact wording of a prompt directive matters.
- **Flag uncertainty.** If a file looks important but its purpose isn't obvious, note it and move on rather than speculating.
- **The goal is a faithful survey, not a design proposal.** The fixture and invariants you propose should be directly grounded in what the code says, not in what you think an evaluation harness should look like in general.

---

## Why This Matters

The downstream work is a requirements document for an evaluation harness. That document will drive implementation decisions: what to build, in what order, with what trade-offs. Getting the requirements right depends on understanding the codebase accurately.

A common failure mode is skimming the code and producing a requirements document based on generic "how to test LLM plugins" advice. This doesn't work because:

- Specific plugins have specific failure modes, often encoded in specific "do not do X" directives in their prompts
- Specific plugins have specific testing seams that are unique to their architecture
- A generic test suite catches generic bugs; this plugin needs tests that catch the bugs its authors already know about

Your job is to extract the plugin-specific signal so the next session can write plugin-specific requirements.
