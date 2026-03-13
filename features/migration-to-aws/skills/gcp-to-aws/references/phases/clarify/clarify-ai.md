# Category F — AI/Bedrock (If `ai-workload-profile.json` Exists)

_Fire when:_ `ai-workload-profile.json` exists in `$MIGRATION_DIR/`.

---

## AI Context Summary

Before presenting questions, show:

> **AI Context Summary:**
> **AI source:** [from `summary.ai_source`: "Gemini", "OpenAI", "Both", or "Other"]
> **Models detected:** [from `models[].model_id`]
> **Capabilities in use:** [from `integration.capabilities_summary` where true]
> **Integration pattern:** [from `integration.pattern`] via [from `integration.primary_sdk`]
> **Gateway/router:** [from `integration.gateway_type`, or "None (direct SDK)"]
> **Frameworks:** [from `integration.frameworks`, or "None"]

---

## Q14 — What AI framework or orchestration layer are you using? (select all that apply)

**Auto-detect signals** — scan IaC and application code before asking:

- No AI framework imports, raw HTTP calls to OpenAI/Gemini endpoints → A
- LiteLLM imports or config files → B
- OpenRouter base URL in code/config → B
- PortKey, Helicone, Martian SDK imports → B
- Kong AI Gateway, Apigee AI config files → B
- Custom proxy class wrapping the AI client → B
- LangChain/LangGraph imports → C
- LangChain/LlamaIndex with provider-agnostic model config → C
- CrewAI imports, `Crew` and `Agent` class definitions → D
- AutoGen imports, `ConversableAgent` patterns → D
- Custom multi-agent loop with dispatcher logic → D
- OpenAI Agents SDK / Swarm imports → E
- Custom while-loop agent with tool-call parsing → E
- `mcp.server` / `mcp.client` imports, MCP config JSON files → F
- A2A protocol config or SDK imports → F
- Vapi, Bland.ai, Retell SDK imports → G
- Nova Sonic or Whisper integration in code → G

_Skip when:_ Auto-detection fully resolves the framework(s). Use detected value(s) with `chosen_by: "extracted"`.

> How your AI calls reach the model determines migration effort. Gateway users can often migrate by changing a single config line.
>
> A) No framework — direct API calls to OpenAI/Gemini
> B) LLM router/gateway (LiteLLM, OpenRouter, PortKey, Kong, Apigee)
> C) LangChain / LangGraph
> D) Multi-agent framework (CrewAI, AutoGen, custom)
> E) OpenAI Agents SDK / custom agent loop
> F) MCP servers or A2A protocol
> G) Voice/conversational agent platform (Vapi, Retell, Bland.ai)
>
> _(Multiple selections allowed)_

| Answer                             | Recommendation Impact                                                                                     | Migration Effort  | Timeline                                           |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------- | ----------------- | -------------------------------------------------- |
| A) No framework — direct API calls | Swap SDK calls to Bedrock SDK; evaluate Bedrock Agents if planning agentic                                | Low               | 1–3 weeks depending on call sites                  |
| B) LLM router/gateway              | Add Bedrock as provider in gateway config; no app code changes; verify SigV4 auth                         | Minimal           | Hours to 1–3 days                                  |
| C) LangChain / LangGraph           | Provider swap via `ChatBedrock`; chains/graphs/tools preserved; validate tool schemas                     | Low               | 1–3 days; 1 week if complex graphs                 |
| D) Multi-agent framework           | Path 1: Keep framework, swap LLM provider (lower effort). Path 2: Migrate to Bedrock multi-agent (deeper) | Medium            | Path 1: 3–5 days; Path 2: 2–4 weeks                |
| E) OpenAI Agents SDK               | Highest effort; tightly coupled to OpenAI API; recommend Bedrock Agents or LangGraph as portable step     | High              | 2–4 weeks                                          |
| F) MCP / A2A                       | Bedrock Agents supports MCP natively; A2A interop available; recommend Bedrock Agents as orchestration    | Low–Medium        | 3–5 days MCP; 1–2 weeks A2A                        |
| G) Voice platform                  | If platform supports Bedrock natively → config change; otherwise evaluate Nova Sonic                      | Minimal to Medium | Hours if native; 2–3 weeks if Nova Sonic migration |

### Combination Logic

| Combination                          | Approach                                                                                               |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| A only                               | Simplest path — direct SDK migration                                                                   |
| B only                               | Quick win — gateway config change, skip SDK migration steps                                            |
| B + any other                        | Gateway swap is the quick win; assess framework migration as separate workstream                       |
| C + A                                | Two workstreams: LangChain provider swap (fast) + direct call migration (slower)                       |
| D + F                                | Complex — multi-agent with MCP tooling; recommend Bedrock Agents to unify orchestration and tools      |
| E + anything                         | E is the long pole; plan timeline around Agents SDK migration; other layers may be quick wins          |
| Multiple frameworks (C+D, C+E, etc.) | Assess independently; prioritize by traffic volume or business criticality; consolidate post-migration |

If answer includes B and no other selections, skip or abbreviate SDK migration steps. If answer is A only, proceed with standard model migration flow.

Interpret → `ai_framework` array (multiple selections → array of all selected values). Default: auto-detect from code, fallback `["direct"]`.

---

## Q15 — Approximately how much are you spending on OpenAI or Gemini per month?

> A) < $500/month
> B) $500–$2,000/month
> C) $2,000–$10,000/month
> D) > $10,000/month
> E) I don't know

| Answer               | Recommendation Impact                                                                             |
| -------------------- | ------------------------------------------------------------------------------------------------- |
| < $500/month         | AWS Activate or low-tier IW Migrate credits; Bedrock cost comparison shows modest savings         |
| $500–$2,000/month    | IW Migrate credits at 35% of ARR; Bedrock cost comparison highlighted                             |
| $2,000–$10,000/month | Significant IW Migrate credits; Bedrock cost savings prominently featured; Savings Plans analysis |
| > $10,000/month      | MAP eligibility likely; dedicated AI migration support; Bedrock provisioned throughput analysis   |

Interpret → `ai_monthly_spend`. Default: B → `"$500-$2K"`.

---

## Q16 — What matters most for your AI workloads?

Present with concrete anchors: Quality = legal analysis/code gen; Speed = autocomplete/live chat; Cost = classification/tagging at scale; Specialized = specific feature (→ Q17); Balanced = all-rounder.

> A) Best quality/reasoning — accuracy matters most, willing to pay more
> B) Fastest speed — response time is the primary constraint
> C) Lowest cost — high volume, budget tight, good-enough quality at scale
> D) Specialized capability — rely on a specific feature (covered in Q17)
> E) Balanced — no single dimension dominates
> F) I don't know

| Answer                 | Recommendation Impact                                                                                                        |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Best quality/reasoning | Claude Sonnet 4.6 (latest, highest reasoning in Sonnet family) — primary; Claude Opus 4.6 for most demanding reasoning tasks |
| Fastest speed          | Claude Haiku 4.5 — lowest latency in Claude family; also consider Amazon Nova Micro/Lite for cost-optimized speed            |
| Lowest cost            | Claude Haiku 4.5 or Amazon Nova Micro — lowest cost per token                                                                |
| Specialized capability | Deferred to Q17 to determine which model                                                                                     |
| Balanced               | Claude Sonnet 4.6 as default balanced recommendation                                                                         |

Interpret → `ai_priority`. Default: E → `"balanced"`.

---

## Q17 — What is your MOST CRITICAL specialized AI feature?

> A) Function calling / Tool use
> B) Ultra-long context (> 300K tokens)
> C) Extended thinking / Chain-of-thought
> D) Prompt caching
> E) RAG optimization
> F) Agentic workflows
> G) Real-time speed (< 500ms)
> H) Multimodal with image generation
> I) Real-time conversational speech
> J) None — standard features are sufficient

| Answer                               | Recommendation Impact                                                                                                                                                        |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Function calling / Tool use          | Claude Sonnet 4.6 — best-in-class tool use on Bedrock via structured JSON tool schemas; supports parallel tool calls and multi-turn tool use                                 |
| Ultra-long context (> 300K tokens)   | Claude Sonnet/Opus 4.6 Long Context (>200K, 2x input price); or Llama 4 Scout (10M), Llama 4 Maverick (1M), Nova 2 Pro/Lite (1M) for natively long context at standard price |
| Extended thinking / Chain-of-thought | Claude Sonnet 4.6 with extended thinking mode; Claude Opus 4.6 for most complex reasoning                                                                                    |
| Prompt caching                       | Claude Sonnet 4.6 with prompt caching enabled; cost savings analysis included                                                                                                |
| RAG optimization                     | Amazon Bedrock Knowledge Bases recommended alongside model; Titan Embeddings for vector store                                                                                |
| Agentic workflows                    | Claude Sonnet 4.6 with Bedrock Agents; multi-agent orchestration guidance included                                                                                           |
| Real-time speed (< 500ms)            | Claude Haiku 4.5 or Nova Micro; streaming response guidance included                                                                                                         |
| Multimodal with image generation     | Claude Sonnet 4.6 (vision) + Amazon Nova Canvas or Titan Image Generator for generation                                                                                      |
| Real-time conversational speech      | Amazon Nova Sonic recommended for speech-to-speech; latency guidance included                                                                                                |
| None                                 | Default recommendation from Q16 priority stands                                                                                                                              |

Interpret → `ai_critical_feature`. Default: J → no override.

---

## Q18 — What's your AI usage volume and cost tolerance?

> A) Low volume + quality priority — small-scale, quality matters most
> B) Medium volume + balanced — moderate production use, balanced approach
> C) High volume + cost critical — high scale, budget is tight, need cost control

| Answer                        | Recommendation Impact                                                                                         |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Low volume + quality priority | On-demand Claude Sonnet; no provisioned throughput needed                                                     |
| Medium volume + balanced      | On-demand Claude Sonnet or Haiku depending on Q16; Savings Plans analysis                                     |
| High volume + cost critical   | **Provisioned throughput strongly recommended**; Claude Haiku or Nova Micro; prompt caching analysis included |

Interpret → `ai_token_volume`: A → `"low"`, B → `"medium"`, C → `"high"`. Default: A → `"low"`.

---

## Q19 — Which Gemini or OpenAI model are you currently using?

Establishes baseline Bedrock recommendation. **Override hierarchy:** Q17 special features (hard override) > Q16 priority > Q18/Q21 volume and latency > Q19 source model (baseline only).

> A) Gemini Flash (1.5/2.0/2.5 Flash)
> B) Gemini Pro (1.5/2.5/3 Pro)
> C) GPT-3.5 Turbo
> D) GPT-4 / GPT-4 Turbo
> E) GPT-4o
> F) GPT-5 / GPT-5.x
> G) o-series (o1, o3)
> H) Other / Multiple models
> I) I don't know

| Source Model              | Baseline Bedrock Recommendation                                       | Pricing Context                                                  |
| ------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Gemini Flash variants     | Claude Haiku 4.5 ($1/$5) — speed and cost optimized                   | Strong savings vs Gemini Flash pricing                           |
| Gemini Pro variants       | Claude Sonnet 4.6 ($3/$15) — quality match                            | Comparable pricing tier                                          |
| GPT-3.5 Turbo             | Claude Haiku 4.5 ($1/$5) — cost-equivalent                            | Haiku is faster and cheaper                                      |
| GPT-4 / GPT-4 Turbo       | Claude Sonnet 4.6 ($3/$15) — quality equivalent                       | Major savings: GPT-4 Turbo is $10/$30 vs Sonnet $3/$15           |
| GPT-4o                    | Claude Sonnet 4.6 ($3/$15) — performance equivalent                   | Modest savings on output; input slightly higher on Bedrock       |
| GPT-5 / GPT-5.x           | Claude Sonnet 4.6 ($3/$15) — performance equivalent                   | GPT-5 is $1.25/$10 — savings story is quality/features, not cost |
| GPT-5 (flagship use case) | Claude Opus 4.6 ($5/$25) — flagship-to-flagship                       | Opus still cheaper than GPT-5 Pro ($15/$120)                     |
| o-series (o1, o3)         | Claude Sonnet 4.6 with extended thinking; Opus 4.6 for most demanding | o1 is $15/$60 — significant savings with Sonnet 4.6 at $3/$15    |

**Override examples:** GPT-4 + Q16=cost → Haiku; Flash + Q17=extended thinking → Sonnet; GPT-4o + Q17=speech → Nova Sonic; GPT-3.5 + Q22=complex → Sonnet; GPT-5 + Q16=balanced → Sonnet.

Interpret → `ai_model_baseline`. Default: auto-detect from code, fallback Q16 priority-based.

---

## Q20 — Do you need vision (image understanding) or just text?

> A) Text only
> B) Vision required — model must process images
> C) Audio/Video inputs needed

| Answer             | Recommendation Impact                                                                    |
| ------------------ | ---------------------------------------------------------------------------------------- |
| Text only          | Full model catalog available; cheapest/fastest text model per Q16 priority               |
| Vision required    | Claude Sonnet or Haiku (both support multimodal vision); Nova Micro excluded (text-only) |
| Audio/Video inputs | Amazon Nova Reel (video) or Nova Sonic (audio); Claude excluded for audio/video input    |

Interpret → `ai_vision`. Default: A → no constraint.

---

## Q21 — How important is AI response speed?

Present with concrete anchors: Critical = autocomplete/live chat/real-time transcription; Important = chat assistant/search augmentation; Flexible = report generation/batch analysis.

> A) Critical (< 500ms) — users staring at a loading spinner
> B) Important (< 2s) — quick response expected, brief pause acceptable
> C) Flexible (2–10s) — users can wait, background/async acceptable

| Answer             | Recommendation Impact                                                                             |
| ------------------ | ------------------------------------------------------------------------------------------------- |
| Critical (< 500ms) | Claude Haiku 4.5 or Nova Micro; streaming required; provisioned throughput for consistent latency |
| Important (< 2s)   | Claude Sonnet 4.6 with streaming; standard on-demand acceptable                                   |
| Flexible (2–10s)   | Any model; batch inference considered for cost savings at high volume                             |

Interpret → `ai_latency`. Default: B → `"important"`.

---

## Q22 — How complex are your AI tasks?

Present with concrete examples: Simple = classify/extract/summarize; Moderate = analyze+JSON/few-shot; Complex = multi-turn reasoning/tool use/agentic.

> A) Simple (classification, short summaries, extraction)
> B) Moderate (analysis, structured content, few-shot)
> C) Complex (multi-step reasoning, tool use, agentic workflows)

| Answer   | Recommendation Impact                                                                       |
| -------- | ------------------------------------------------------------------------------------------- |
| Simple   | Claude Haiku 4.5 or Nova Micro sufficient; significant cost savings vs larger models        |
| Moderate | Claude Sonnet 4.6 recommended; Haiku may suffice with prompt engineering                    |
| Complex  | Claude Sonnet 4.6 required; extended thinking considered; Claude Opus 4.6 for hardest tasks |

Interpret → `ai_complexity`. Default: B → `"moderate"`.
