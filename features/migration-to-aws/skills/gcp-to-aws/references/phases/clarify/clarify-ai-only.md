# AI-Only Migration — Clarify Requirements

**Standalone flow** — Used when ONLY `ai-workload-profile.json` exists (no infrastructure or billing artifacts). Infrastructure stays on GCP; only AI/LLM calls move to AWS Bedrock.

Produces the same `preferences.json` output but with `design_constraints` limited to region and `ai_constraints` fully populated.

---

## Step 1: Present AI Detection Summary

> **AI-Only Migration Detected**
> Your project has AI workloads but no infrastructure artifacts (Terraform, billing). I'll focus on migrating your AI/LLM calls to AWS Bedrock while your infrastructure stays on GCP.
>
> **AI source:** [from `summary.ai_source`]
> **Models detected:** [from `models[].model_id`]
> **Capabilities in use:** [from `integration.capabilities_summary` where true]
> **Integration pattern:** [from `integration.pattern`] via [from `integration.primary_sdk`]
> **Gateway/router:** [from `integration.gateway_type`, or "None (direct SDK)"]

---

## Step 2: Ask Questions (Q1–Q10)

Present all questions at once. User can answer each, skip individual ones (use defaults), or say "use all defaults."

## Q1 — AI framework or orchestration layer (select all that apply)

Same decision logic, auto-detect signals, and interpretation as Q14 in `clarify-ai.md`.

Auto-detect: No framework → A, LiteLLM/OpenRouter/Kong/Apigee → B, LangChain/LangGraph → C, CrewAI/AutoGen → D, OpenAI Agents SDK → E, MCP/A2A → F, Vapi/Bland.ai/Retell → G.

> A) No framework — direct API calls | B) LLM router/gateway | C) LangChain / LangGraph | D) Multi-agent framework | E) OpenAI Agents SDK | F) MCP/A2A | G) Voice platform

Interpret → `ai_framework` array. Default: auto-detect, fallback `["direct"]`.

## Q2 — What matters most for your AI application?

> A) Best quality/reasoning | B) Fastest speed | C) Lowest cost | D) Specialized capability (→ Q10) | E) Balanced | F) I don't know

| Answer   | Model Impact                                          |
| -------- | ----------------------------------------------------- |
| Quality  | Claude Sonnet 4.6 primary; Opus 4.6 for hardest tasks |
| Speed    | Claude Haiku 4.5; also Nova Micro/Lite                |
| Cost     | Claude Haiku 4.5 or Nova Micro                        |
| Special  | Deferred to Q10                                       |
| Balanced | Claude Sonnet 4.6                                     |

Interpret → `ai_priority`. Default: E → `"balanced"`.

## Q3 — Monthly AI spend on OpenAI or Gemini?

> A) < $500 | B) $500–$2K | C) $2K–$10K | D) > $10K | E) Don't know

Interpret → `ai_monthly_spend`. Default: B → `"$500-$2K"`.

## Q4 — Cross-cloud API call concerns

Unique to AI-only: infrastructure stays on GCP while AI calls route to AWS.

> A) Latency critical — AI in hot path | B) Latency acceptable — async/users can wait | C) Concerned about egress costs | D) Want to test first — parallel running

| Answer           | Impact                                         |
| ---------------- | ---------------------------------------------- |
| Latency critical | VPC endpoint; closest region to GCP deployment |
| Acceptable       | Standard endpoint; region by cost              |
| Egress concerned | PrivateLink; egress cost analysis              |
| Test first       | Phased migration; parallel running guidance    |

Interpret → `cross_cloud`. Default: B → `"latency-acceptable"`.

## Q5 — Current model in use?

Establishes baseline Bedrock recommendation. Override hierarchy: Q10 special features > Q2 priority > Q7/Q8 volume/latency > Q5 baseline.

> A) Gemini Flash | B) Gemini Pro | C) GPT-3.5 Turbo | D) GPT-4/4 Turbo | E) GPT-4o | F) GPT-5/5.x | G) o-series | H) Other/Multiple | I) Don't know

| Source         | Baseline Recommendation           | Pricing Context                    |
| -------------- | --------------------------------- | ---------------------------------- |
| Gemini Flash   | Claude Haiku 4.5 ($1/$5)          | Strong savings                     |
| Gemini Pro     | Claude Sonnet 4.6 ($3/$15)        | Comparable tier                    |
| GPT-3.5 Turbo  | Claude Haiku 4.5 ($1/$5)          | Faster and cheaper                 |
| GPT-4/4 Turbo  | Claude Sonnet 4.6 ($3/$15)        | Major savings (GPT-4T: $10/$30)    |
| GPT-4o         | Claude Sonnet 4.6 ($3/$15)        | Modest savings on output           |
| GPT-5/5.x      | Claude Sonnet 4.6 ($3/$15)        | Savings story is quality, not cost |
| GPT-5 flagship | Claude Opus 4.6 ($5/$25)          | Cheaper than GPT-5 Pro ($15/$120)  |
| o-series       | Sonnet 4.6 with extended thinking | o1 $15/$60 → significant savings   |

Override examples: GPT-4 + Q2=cost → Haiku; Flash + Q10=extended thinking → Sonnet; GPT-4o + Q10=speech → Nova Sonic.

Interpret → `ai_model_baseline`. Default: auto-detect, fallback Q2 priority-based.

## Q6 — What input types must the model accept: text only, images (vision), or audio/video?

> A) Text only | B) Vision required | C) Audio/Video inputs

| Answer      | Impact                                                                                   |
| ----------- | ---------------------------------------------------------------------------------------- |
| Text only   | Full model catalog                                                                       |
| Vision      | Claude Sonnet or Haiku (both support multimodal vision); Nova Micro excluded (text-only) |
| Audio/Video | Nova Reel/Sonic; Claude excluded for audio/video input                                   |

Interpret → `ai_vision`. Default: A → no constraint.

## Q7 — Monthly AI usage volume

> A) < 1M tokens | B) 1–10M | C) 10–100M | D) > 100M | E) Don't know

| Answer    | Impact                                             |
| --------- | -------------------------------------------------- |
| Low       | On-demand; no provisioned throughput               |
| Medium    | On-demand with prompt caching analysis             |
| High      | Provisioned throughput analysis; prompt caching    |
| Very high | Provisioned throughput required; capacity planning |

Interpret → `ai_token_volume`: A → `"low"`, B → `"medium"`, C → `"high"`, D → `"very_high"`. Default: B → `"medium"`.

## Q8 — Response speed importance

Present with concrete anchors: Critical = autocomplete/live chat; Important = chat assistant; Flexible = reports/batch.

> A) Critical (< 500ms) | B) Important (< 2s) | C) Flexible (2–10s)

| Answer    | Impact                                                       |
| --------- | ------------------------------------------------------------ |
| Critical  | Haiku/Nova Micro; streaming required; provisioned throughput |
| Important | Sonnet 4.6 with streaming; standard on-demand                |
| Flexible  | Any model; batch inference for cost savings                  |

Interpret → `ai_latency`. Default: B → `"important"`.

## Q9 — AI task complexity

Present with concrete examples: Simple = classify/extract/summarize; Moderate = analyze+JSON/few-shot; Complex = multi-turn reasoning/tool use/agentic.

> A) Simple | B) Moderate | C) Complex

| Answer   | Impact                                                              |
| -------- | ------------------------------------------------------------------- |
| Simple   | Haiku/Nova Micro sufficient; significant cost savings               |
| Moderate | Sonnet 4.6 recommended; Haiku may suffice with prompt engineering   |
| Complex  | Sonnet 4.6 required; extended thinking considered; Opus for hardest |

Interpret → `ai_complexity`. Default: B → `"moderate"`.

## Q10 — Specialized features needed

Same decision logic as Q17 in `clarify-ai.md`.

> A) Function calling | B) Ultra-long context (> 300K) | C) Extended thinking | D) Prompt caching | E) RAG optimization | F) Agentic workflows | G) Real-time speed | H) Image generation | I) Conversational speech | J) None

Interpret → `ai_critical_feature`. Default: J → no override.

---

## Step 3: Write preferences.json

Write `$MIGRATION_DIR/preferences.json`:

**Schema — AI-only structure:**

| Field                      | Path                                      | Notes                                       |
| -------------------------- | ----------------------------------------- | ------------------------------------------- |
| `migration_type`           | `metadata.migration_type`                 | `"ai-only"` — downstream skips infra phases |
| `discovery_artifacts`      | `metadata.discovery_artifacts`            | `["ai-workload-profile.json"]`              |
| `questions_asked`          | `metadata.questions_asked`                | Array of Q1-Q10 asked                       |
| `questions_defaulted`      | `metadata.questions_defaulted`            | Array of Q IDs where defaults used          |
| `target_region`            | `design_constraints.target_region`        | Derived from GCP region or cross-cloud pref |
| `ai_framework`             | `ai_constraints.ai_framework`             | From Q1                                     |
| `ai_priority`              | `ai_constraints.ai_priority`              | From Q2                                     |
| `ai_monthly_spend`         | `ai_constraints.ai_monthly_spend`         | From Q3                                     |
| `cross_cloud`              | `ai_constraints.cross_cloud`              | From Q4 (unique to AI-only)                 |
| `ai_model_baseline`        | `ai_constraints.ai_model_baseline`        | From Q5                                     |
| `ai_vision`                | `ai_constraints.ai_vision`                | From Q6                                     |
| `ai_token_volume`          | `ai_constraints.ai_token_volume`          | From Q7                                     |
| `ai_latency`               | `ai_constraints.ai_latency`               | From Q8                                     |
| `ai_complexity`            | `ai_constraints.ai_complexity`            | From Q9                                     |
| `ai_critical_feature`      | `ai_constraints.ai_critical_feature`      | From Q10                                    |
| `ai_capabilities_required` | `ai_constraints.ai_capabilities_required` | Derived from `capabilities_summary`         |

Each `ai_constraints` field uses `{ "value": ..., "chosen_by": "user"|"extracted"|"derived" }` format. No nulls. All schema rules from `clarify.md` apply.

---

## Step 4: Update Phase Status

Before phase completion, enforce output gate:

- `preferences.json` must exist.
- `preferences.json.metadata.migration_type` must equal `"ai-only"`.

If either check fails: STOP and output: "AI-only clarify output validation failed. Fix `preferences.json` before completing Phase 2."

Use the Phase Status Update Protocol (read-merge-write) to update `.phase-status.json` in the same turn as the output message:

- Set `phases.clarify` to `"completed"`
- Set `current_phase` to `"design"`

Output: "Clarification complete. Proceeding to Phase 3: Design AI Migration Architecture."
