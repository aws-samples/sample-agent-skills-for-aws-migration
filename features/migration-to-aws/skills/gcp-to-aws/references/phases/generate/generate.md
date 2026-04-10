# Phase 5: Generate Migration Artifacts (Orchestrator)

**Execute ALL steps in order. Do not skip or optimize.**

## Overview

The Generate phase has **2 mandatory stages** that run sequentially:

1. **Stage 1: Migration Planning** — Produces execution plans (JSON) from estimation + design artifacts
2. **Stage 2: Artifact Generation** — Produces deployable code (Terraform, scripts, adapters, docs) from plans + designs

Both stages must complete for the phase to succeed.

## Prerequisites

1. Read `$MIGRATION_DIR/.phase-status.json`. If missing, invalid, or `phases.clarify` is not exactly `"completed"`: **STOP**. Output: "Phase 2 (Clarify) not completed or phase state is missing/invalid. Complete Clarify before Generate."
2. **Dirty-state check**: If `dirty_state` is non-null and `dirty_state.phase` is `"generate"`, warn the user and offer resume options per `shared/artifact-validation.md` Section 2. Do not proceed until the user chooses.
3. Read `$MIGRATION_DIR/preferences.json`. If missing: **STOP**. Output: "Phase 2 (Clarify) not completed. Run Phase 2 first."

Check which estimation artifacts exist in `$MIGRATION_DIR/`:

- `estimation-infra.json` (infrastructure estimation)
- `estimation-ai.json` (AI workload estimation)
- `estimation-billing.json` (billing-only estimation)

If **none** of these estimation artifacts exist: **STOP**. Output: "No estimation artifacts found. Run Phase 4 (Estimate) first."

## Stage 1: Migration Planning

**Dirty-state tracking**: Before producing any Stage 1 outputs, set `dirty_state` in `.phase-status.json`:

```json
"dirty_state": {
  "phase": "generate",
  "stage": "stage_1_planning",
  "started_at": "<ISO 8601 UTC>",
  "partial_outputs": [],
  "missing_outputs": ["generation-infra.json", "generation-ai.json", "generation-billing.json"]
}
```

Trim `missing_outputs` to only the artifacts expected for the active routes. Update `partial_outputs` and `missing_outputs` after each sub-file completes.

Route based on which estimation artifacts exist. Multiple paths can run independently.

### Infrastructure Migration Plan

IF `estimation-infra.json` exists:

> Load `generate-infra.md`

Produces: `generation-infra.json`

### AI Migration Plan

IF `estimation-ai.json` exists:

> Load `generate-ai.md`

Produces: `generation-ai.json`

### Billing-Only Migration Plan

IF `estimation-billing.json` exists:

> Load `generate-billing.md`

Produces: `generation-billing.json`

## Stage 2: Artifact Generation

**MUST proceed only after Stage 1 completes.** Route based on generation plans + design artifacts.

**Dirty-state tracking**: Before producing any Stage 2 outputs, update `dirty_state` in `.phase-status.json`:

```json
"dirty_state": {
  "phase": "generate",
  "stage": "stage_2_artifacts",
  "started_at": "<ISO 8601 UTC>",
  "partial_outputs": ["generation-infra.json"],
  "missing_outputs": ["terraform/", "scripts/", "MIGRATION_GUIDE.md", "README.md"]
}
```

Carry forward `partial_outputs` from Stage 1. Trim `missing_outputs` to only the artifacts expected for the active routes plus mandatory docs. Update after each sub-file completes.

### Infrastructure Artifacts

IF `generation-infra.json` AND `aws-design.json` exist:

> Load `generate-artifacts-infra.md`

Produces: `terraform/` directory

After generate-artifacts-infra.md completes (terraform files generated),
load `generate-artifacts-scripts.md` to generate migration scripts.

Produces: `scripts/` directory

### AI Artifacts

IF `generation-ai.json` AND `aws-design-ai.json` exist:

> Load `generate-artifacts-ai.md`

Produces: `ai-migration/` directory

### Billing Skeleton Artifacts

IF `generation-billing.json` AND `aws-design-billing.json` exist:

> Load `generate-artifacts-billing.md`

Produces: `terraform/skeleton.tf` (with TODO markers)

### Documentation (ALWAYS runs after artifact generation)

AFTER all above artifact generation sub-files complete:

> Load `generate-artifacts-docs.md`

Produces: `MIGRATION_GUIDE.md`, `README.md`

### HTML Report (ALWAYS runs last, after documentation)

AFTER generate-artifacts-docs.md completes:

> Load `generate-artifacts-report.md`

Produces: `migration-report.html`, `migration-report.pdf` (if a PDF converter is available)

**Non-blocking:** If report generation fails, log a warning and continue to Phase Completion. Do not fail the phase. PDF conversion is also non-blocking — if no converter is found, the HTML report is sufficient.

## Phase Completion

Verify both stages are complete:

1. **Stage 1 route gates (fail closed)**:
   - If `estimation-infra.json` exists -> require `generation-infra.json`
   - If `estimation-ai.json` exists -> require `generation-ai.json`
   - If `estimation-billing.json` exists -> require `generation-billing.json`
2. **Stage 2 route gates (fail closed)**:
   - If infra artifact route is active (`generation-infra.json` AND `aws-design.json`) -> require `terraform/` and `scripts/`
   - If AI artifact route is active (`generation-ai.json` AND `aws-design-ai.json`) -> require `ai-migration/`
   - If billing artifact route is active (`generation-billing.json` AND `aws-design-billing.json`) -> require `terraform/skeleton.tf`
3. **Documentation gate (always)**:
   - Require `MIGRATION_GUIDE.md` and `README.md`
4. If any active route is missing expected outputs: STOP and output: "Generate route [name] missing required artifacts. Re-run the failed generator before completing Phase 5."
5. **Content validation:** For each produced JSON artifact, apply the parse + non-empty + required-field checks from `shared/artifact-validation.md` Section 1. For directory artifacts, verify they are non-empty and contain minimum expected files. For Markdown artifacts, verify non-empty and no unresolved `[placeholder]` strings. If any check fails: STOP with the specified error message.

After all gates pass, use the Phase Status Update Protocol (read-merge-write) to update `.phase-status.json` — **in the same turn** as the summary below:

- Set `phases.generate` to `"completed"`
- Set `current_phase` to `"complete"`
- Clear `dirty_state` (set to `null`)

## Summary

**Use structured completion reporting** (see `shared/artifact-validation.md` Section 3). Present final summary to user:

```
Phase 5 (Generate) complete.

✓ Produced:
  - generation-infra.json: [X]-week migration plan
  - terraform/: [N] files (list key files)
  - scripts/: [N] files
  - MIGRATION_GUIDE.md: [N] sections
  - README.md: artifact catalog + quick start
  - migration-report.html: executive summary
  - migration-report.pdf: PDF version [or "skipped — no converter available"]

⊘ Skipped (not applicable):
  - [artifact]: [reason]

⚠ Skipped (non-blocking failure):
  - migration-report.html: [failure reason]  ← only if report generation failed
```

After the structured block, include:

1. **Key timelines** — Highlight migration timeline from the generation plans
2. **Key risks** — Highlight top risks from the generation plans
3. **TODO markers** — Note any TODO markers in generated artifacts that require manual attention
4. **Next steps** — Recommend reviewing generated artifacts, customizing TODO sections, and beginning migration execution

Output to user:
- If `migration-report.pdf` exists: "Migration artifact generation complete. All phases of the GCP-to-AWS migration analysis are complete. Your migration report is ready at $MIGRATION_DIR/migration-report.pdf (HTML version also at $MIGRATION_DIR/migration-report.html)"
- If `migration-report.html` exists but PDF is missing: "Migration artifact generation complete. All phases of the GCP-to-AWS migration analysis are complete. Your migration report is ready at $MIGRATION_DIR/migration-report.html (PDF conversion skipped — install Chrome, wkhtmltopdf, or weasyprint for automatic PDF output)"
- If `migration-report.html` is missing: "Migration artifact generation complete. All phases of the GCP-to-AWS migration analysis are complete. Markdown documentation is available at $MIGRATION_DIR/MIGRATION_GUIDE.md and $MIGRATION_DIR/README.md. (HTML/PDF report generation is optional and non-blocking.)"
