# Changelog — GCP-to-AWS Migration Plugin

## Bedrock: Claude Opus 4.7 (2026-04-16)

**Change:** Documented **Claude Opus 4.7** (`anthropic.claude-opus-4-7`) in the pricing cache with the same headline on-demand **$5 / $25** per 1M input/output as Opus 4.6 (US East N. Virginia standard table), added **batch N/A** + prompt-cache columns per the Bedrock pricing page when this was updated, and refreshed clarify / design-ref guidance so **Opus 4.7** is the default name for hardest-reasoning Opus work while **Sonnet 4.6** stays the balanced default.

**Files:** `references/shared/pricing-cache.md`, `references/phases/clarify/clarify-ai.md`, `references/phases/clarify/clarify-ai-only.md`, `references/phases/clarify/clarify.md`, `references/design-refs/ai-gemini-to-bedrock.md`, `references/design-refs/ai-openai-to-bedrock.md`.

---

## Summary

Eight epics were addressed across 18 files (17 modified, 1 new). All changes are prompt-only — no application code was added or changed. Epic 4 (Gemini 3.1 Pro GA) is deferred pending confirmed GA date, pricing, and benchmark data.

---

## Epic 1: IDE Plugin Survey — Collect IDE Type and Plugin Version

**Problem:** The Phase 6 feedback flow directed users to a static Pulse survey URL. There was no way to correlate survey responses with the IDE (Claude Code vs Cursor) or plugin version.

**Fix:** Added automatic IDE and plugin version detection, passed as hidden query parameters on the Pulse survey URL.

**How it works:**

- **IDE detection**: Checks `CLAUDE_CODE` environment variable (Claude Code) or `CURSOR_TRACE_ID` (Cursor). Falls back to `unknown`.
- **Version detection**: Reads `plugin.json` from `.claude-plugin/` or `.cursor-plugin/` directory. Falls back to `0.0.0`.
- **Sanitization**: Values are restricted to Pulse-safe characters (letters, numbers, dots, tildes, hyphens, underscores).
- **URL format**: `https://pulse.amazon/survey/MY0ZY7UA?ide=$IDE_TYPE&version=$PLUGIN_VERSION`

**Files changed:**

- `phases/feedback/feedback.md` — Added Step 0 (IDE/version detection), updated URL template, updated `feedback.json` schema

---

## Epic 2: HTML Migration Report

**Problem:** The plugin generated markdown files (`MIGRATION_GUIDE.md`, `README.md`) but had no consolidated, shareable report combining the executive summary with detailed analysis.

**Fix:** Added a new Generate phase sub-step that produces a self-contained HTML report (`migration-report.html`) with inline CSS. No external dependencies required.

**How it works:**

- **Executive Summary** (designed to fit one printed page): GCP services detected, recommended AWS architecture (with confidence badges), cost comparison (3 tiers), timeline, and top 3 risks.
- **Detailed Appendix** (5 sections): Service Recommendations with rationale, Cost Estimates with per-service breakdown and optimization opportunities, Migration Steps with rollback procedure, AI Migration (conditional), and Artifacts Catalog.
- **Styling**: AWS-themed colors (#ff9900 accents, #232f3e headers), metric cards, confidence badges (green/amber/red), print-friendly CSS.
- **Browser launch**: Automatically opens the report via `open` (macOS) or `xdg-open` (Linux). Falls back to presenting a clickable `file://` path.
- **Non-blocking**: Report generation failure does not block the Generate phase.
- Respects `human_expertise_required` flag and `billing_data_available` conditional from Epics 3 and 7.

**Files changed:**

- `phases/generate/generate-artifacts-report.md` — **New file**. Full steering for HTML report generation.
- `phases/generate/generate.md` — Added HTML Report step after Documentation, updated summary output to include report path.

---

## Epic 3: BigQuery Migration — Human Expertise Flags

**Problem:** BigQuery was mapped to AWS services (Athena/Redshift) like any other service, but BigQuery migrations involve query pattern translation, large-scale data movement, ETL pipeline rewiring, and BI integration updates that benefit from specialist guidance. There was no flag to surface this.

**Fix:** Added a `human_expertise_required` boolean field that is set to `true` on all BigQuery resource mappings and propagated through every downstream phase (design, estimation, generation, documentation).

**How it works:**

- **Design phase**: Explicit inline rules at the exact mapping step — `google_bigquery_dataset` gets `human_expertise_required: true`, all other resources get `false`. This field is REQUIRED on every resource/service in the output.
- **Generation phase**: BigQuery entries get a dynamic risk entry (high likelihood / high impact) with mitigation recommending AWS account team engagement.
- **Documentation**: MIGRATION_GUIDE.md includes a prominent callout box next to BigQuery services. README.md appends "(Specialist guidance recommended)" to Key Decisions for flagged services.

**Key design decision:** The flag rule was initially placed in the `database.md` rubric file (prose), but testing showed the agent didn't reliably pick it up. We moved explicit, hard-to-miss rules to the exact step where mappings are assigned in `design-infra.md` and `design-billing.md`.

**Files changed:**

- `design-refs/database.md` — Added Human Expertise Required paragraph under BigQuery signals, added flag to example output
- `phases/design/design-infra.md` — Added step 5 in Pass 2 (explicit BigQuery check), added `human_expertise_required: false` to Pass 1 fast-path, updated output schema and validation checklist, added BigQuery advisory to summary
- `phases/design/design-billing.md` — Added `human_expertise_required: true` to BigQuery row in heuristic table, added explicit flag and excluded target check rules, updated output schema and validation checklist, added BigQuery advisory to summary
- `phases/generate/generate-infra.md` — Added BigQuery dynamic risk entry, added `human_expertise_required` to per-service output schema
- `phases/generate/generate-billing.md` — Added BigQuery risk row, added `human_expertise_required` to per-service output schema
- `phases/generate/generate-artifacts-docs.md` — Added specialist guidance callout in MIGRATION_GUIDE.md Section 4, added advisory suffix in README.md Key Decisions

---

## Epic 5: Auth Provider Exclusions (Source-Side Skip Mappings)

**Problem:** Third-party authentication providers (Auth0, Firebase Auth, Supabase Auth, Clerk, Okta, Keycloak, NextAuth) and GCP Identity Platform should be recognized but excluded from migration scope. Migrating auth providers is unnecessary — they work cross-cloud.

**Fix:** Added source-side exclusion rules at three levels: resource classification, app code discovery, and fast-path lookup.

**How it works:**

- **Resource classification** (`classification-rules.md`): Added "Priority 0: Excluded Resources" before all other classification rules. Resources matching `google_identity_platform_*` or `google_firebase_auth_*` patterns are skipped entirely — never classified, never clustered.
- **App code discovery** (`discover-app-code.md`): Added "Step 0.5: Auth SDK Exclusion List" with a table of 7 auth provider SDKs. When detected in app code, they are noted in the discovery output but explicitly excluded from migration scope with a note: "Keep existing provider — works cross-cloud."
- **Fast-path lookup** (`fast-path.md`): Added `google_identity_platform_*` and `google_firebase_auth_*` to the Skip Mappings table, ensuring they are skipped if they somehow reach the design phase.

**Files changed:**

- `clustering/terraform/classification-rules.md` — Added Priority 0: Excluded Resources section
- `phases/discover/discover-app-code.md` — Added Step 0.5: Auth SDK Exclusion List
- `design-refs/fast-path.md` — Added auth provider entries to Skip Mappings table

---

## Epic 6: Target Service Preferences (Containerized Workloads & Auth)

**Problem:** Migration recommendations should steer toward AWS services with the strongest ecosystem support and broadest feature sets. For containerized workloads, ECS Fargate and EKS offer deeper integration with VPC, ALB, IAM, and auto-scaling than lighter-weight alternatives. For authentication, startups already using third-party auth providers (Auth0, Firebase Auth, Clerk, etc.) should keep them.

**Fix:** Added a target-side preference mechanism — a "Preferred AWS Target Services" table in `fast-path.md` as the single source of truth, with enforcement checks in the design files and an updated compute rubric.

**How it works:**

- **Preferred AWS Target Services table** (`fast-path.md`): Establishes that containerized workloads should target ECS Fargate or EKS. Third-party auth providers should be preserved rather than replaced with an AWS-native alternative. This is the canonical list.
- **Design enforcement** (`design-infra.md`, `design-billing.md`): After selecting an AWS service, the agent verifies it aligns with the preferred targets. If a non-preferred service is selected, the preferred alternative is substituted and a note is added to the rationale.
- **Compute rubric update** (`compute.md`): Updated candidate evaluation to strongly favor ECS Fargate and EKS for all containerized workload mappings.

**Files changed:**

- `design-refs/fast-path.md` — Added Preferred AWS Target Services section
- `phases/design/design-infra.md` — Added preferred target verification step in Pass 2
- `phases/design/design-billing.md` — Added preferred target check after heuristic lookup
- `design-refs/compute.md` — Updated candidate scoring to reflect service preferences

---

## Epic 7: Scope One-Time Costs to Data Transfer Only

**Problem:** The estimation phase included human migration cost categories (development & testing, infrastructure setup, training & documentation, staffing estimates) that are customer-specific and should not be presented by the tool. One-time costs should be limited to quantifiable infrastructure charges — specifically GCP data transfer egress fees.

**Fix:** Removed all human migration cost language. One-time costs now cover only GCP egress fees when billing data is available. Removed staffing estimates (FTE counts) from the generation phase.

**How it works:**

- **If billing data IS available** (`billing-profile.json` exists): Estimates GCP data transfer egress fees based on migration volume. `billing_data_available` is set to `true`.
- **If billing data is NOT available**: Data transfer section is omitted. `migration_cost_considerations.categories` is empty with a note explaining billing data is needed for egress fee estimates.
- Removed Staffing Estimate section (FTE counts, team roles) from generation plan.
- Removed "Team capacity constraints" from standard risk table.
- The `billing_data_available` boolean propagates to documentation — `generate-artifacts-docs.md` conditionally includes the "One-Time Migration Cost" column in the README cost summary table only when `true`.

**Files changed:**

- `phases/estimate/estimate-infra.md` — Scoped Part 4 to data transfer egress only, removed human cost categories, updated summary and ROI notes
- `shared/schema-estimate-infra.md` — Updated schema to reflect data-transfer-only categories, removed complexity_factors
- `phases/generate/generate-infra.md` — Removed Staffing Estimate section, team_roles from JSON schema, team capacity risk, FTE validation check
- `phases/generate/generate-artifacts-docs.md` — Made One-Time Migration Cost column conditional on `billing_data_available`

---

## Epic 10: Multimodal Input Types (Vision Question Update)

**Problem:** The AI clarification question about input modality only asked about "vision or text" — it didn't account for audio/video input types that modern multimodal models support.

**Fix:** Updated the question wording across all three files where it appears.

**How it works:**

- Q20 (full clarify flow) and Q6 (AI-only flow) changed from "Do you need vision (image understanding) or just text?" to "What input types must the model accept: text only, images (vision), or audio/video?"
- Defaults table updated from "Q20 — Vision" to "Q20 — Input types"

**Files changed:**

- `phases/clarify/clarify-ai.md` — Updated Q20 heading
- `phases/clarify/clarify-ai-only.md` — Updated Q6 heading
- `phases/clarify/clarify.md` — Updated defaults table label

---

## Files Changed Summary

| #  | File                                           | Epics   | Action   |
| -- | ---------------------------------------------- | ------- | -------- |
| 1  | `phases/feedback/feedback.md`                  | 1       | Modified |
| 2  | `phases/generate/generate-artifacts-report.md` | 2       | **New**  |
| 3  | `phases/generate/generate.md`                  | 2       | Modified |
| 4  | `design-refs/database.md`                      | 3       | Modified |
| 5  | `phases/design/design-infra.md`                | 3, 5, 6 | Modified |
| 6  | `phases/design/design-billing.md`              | 3, 5, 6 | Modified |
| 7  | `phases/generate/generate-infra.md`            | 3       | Modified |
| 8  | `phases/generate/generate-billing.md`          | 3       | Modified |
| 9  | `phases/generate/generate-artifacts-docs.md`   | 3, 7    | Modified |
| 10 | `clustering/terraform/classification-rules.md` | 5       | Modified |
| 11 | `phases/discover/discover-app-code.md`         | 5       | Modified |
| 12 | `design-refs/fast-path.md`                     | 5, 6    | Modified |
| 13 | `design-refs/compute.md`                       | 6       | Modified |
| 14 | `phases/estimate/estimate-infra.md`            | 7       | Modified |
| 15 | `shared/schema-estimate-infra.md`              | 7       | Modified |
| 16 | `phases/clarify/clarify-ai.md`                 | 10      | Modified |
| 17 | `phases/clarify/clarify-ai-only.md`            | 10      | Modified |
| 18 | `phases/clarify/clarify.md`                    | 10      | Modified |
