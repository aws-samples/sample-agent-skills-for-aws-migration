# Category F: AI/Bedrock Questions (Q14–Q22)

Fires when `ai-workload-profile.json` exists. Ask in Batch 3.

---

## Q14 — AI Integration Pattern

**Auto-detect:** If `integration.gateway_type` is non-null OR `integration.frameworks` is non-empty in `ai-workload-profile.json`, skip Q14 and set `ai_framework` from detected values with `chosen_by: "extracted"`.

**Context:** How your application calls Azure OpenAI determines the migration approach and effort.

> How does your application integrate with Azure OpenAI / AI services? (Select all that apply)
>
> A) Azure OpenAI REST API or SDK directly (no framework)
> B) Azure API Management as a gateway / load balancer only
> C) LangChain or LangGraph with Azure OpenAI provider
> D) Semantic Kernel (Microsoft's AI orchestration SDK)
> E) AutoGen or similar multi-agent framework
> F) Custom agent loop (your own orchestration code)
> G) Azure AI Studio or Prompt Flow
> H) Other framework — specify

Interpret → `ai_framework` (array):
- A → `["direct"]`
- B → `["gateway_only"]` (config change only, skip SDK migration)
- C → `["langchain"]`
- D → `["semantic_kernel"]`
- E → `["autogen"]`
- F → `["custom_loop"]`
- G → `["azure_ai_studio"]`
- H → `["other"]`

---

## Q15 — AI Monthly Spend

> What is your approximate Azure OpenAI / AI services monthly cost?
>
> A) Under $500
> B) $500–$2K
> C) $2K–$10K
> D) Over $10K
> E) I don't know

Interpret → `ai_monthly_spend`: map to string label. Default: B → `"$500-$2K"`.

---

## Q16 — AI Migration Priority

> What is your primary goal for migrating AI workloads to AWS?
>
> A) Cost reduction — minimize AI inference costs
> B) Performance — reduce latency or increase throughput
> C) AWS consolidation — simplify billing and vendor management
> D) Capabilities — access Bedrock-specific features (Nova, extended thinking, Guardrails)
> E) Balanced — no single dominant priority

Interpret → `ai_priority`: A → `"cost"`, B → `"performance"`, C → `"consolidation"`, D → `"capabilities"`, E → `"balanced"`. Default: E → `"balanced"`.

---

## Q17 — Critical AI Feature

> Which AI feature is most critical to your workload? (Select one)
>
> A) JSON / structured output
> B) Function calling / tool use
> C) Streaming responses
> D) Embeddings / vector search
> E) Image / vision input
> F) Extended thinking / reasoning (chain-of-thought)
> G) Real-time speech (speech-to-speech)
> H) RAG (retrieval-augmented generation)
> I) Document processing / OCR
> J) None — standard text generation

Interpret → `ai_critical_feature`: map letter to string. Impacts model selection in design.

---

## Q18 — Token Volume and Cost Sensitivity

> How would you describe your token usage and cost sensitivity?
>
> A) Low volume, quality is top priority (< 1M tokens/day)
> B) Medium volume, balanced cost/quality (1M–100M tokens/day)
> C) High volume, cost is critical (> 100M tokens/day)
> D) I don't know

Interpret → `ai_token_volume`: A → `"low"`, B → `"medium"`, C → `"high"`, D → `"unknown"` → default `"low"`. Default: A → `"low"`.

---

## Q19 — Current Azure OpenAI Model

**Auto-detect:** If `models[].model_id` populated in `ai-workload-profile.json`, skip and set from detected values.

> Which Azure OpenAI model(s) are you currently using?
>
> A) GPT-4o (latest)
> B) GPT-4o mini
> C) GPT-4 Turbo
> D) GPT-3.5 Turbo
> E) o1 / o1-mini / o3 (reasoning)
> F) text-embedding-3-large or text-embedding-3-small
> G) DALL-E 3
> H) Whisper (speech-to-text)
> I) Multiple models
> J) Other / custom fine-tuned

Interpret → `ai_model_baseline`: map to Bedrock recommendation:
- A (GPT-4o) → `"claude-sonnet-4-6"` (comparable multimodal, 57% cheaper on input)
- B (GPT-4o mini) → `"claude-haiku-4-5"` or `"amazon-nova-lite"` (90%+ cheaper)
- C (GPT-4 Turbo) → `"claude-sonnet-4-6"` (70% cheaper on input)
- D (GPT-3.5 Turbo) → `"amazon-nova-micro"` or `"claude-haiku-4-5"` (87–94% cheaper)
- E (o-series reasoning) → `"claude-sonnet-4-6"` with extended thinking
- F (embeddings) → `"amazon-titan-embed-text-v2"` or `"cohere-embed-v3"`
- G (DALL-E 3) → `"amazon-nova-canvas"` or `"stability-ai-sdxl"` (note: validate image quality)
- H (Whisper) → `"amazon-transcribe"` (note: not a Bedrock model — AWS Transcribe service)
- I / J → flag for per-model mapping in Design

---

## Q20 — Input Modalities

> What types of inputs does your AI workload process?
>
> A) Text only
> B) Text + images (vision)
> C) Text + documents (PDFs, Word)
> D) Text + audio
> E) Multiple modalities

Interpret → `ai_vision`:
- A → `"text-only"` (no vision constraint)
- B → `"vision-required"` → Claude Sonnet 4.6 (multimodal)
- C → `"document-processing"` → Bedrock Data Automation or Textract
- D → `"audio-required"` → Nova 2 Sonic or Amazon Transcribe
- E → `"multimodal"` → Claude Sonnet 4.6 + Transcribe as needed

Default: A → `"text-only"`.

---

## Q21 — Latency Requirements

> How sensitive is your application to AI inference latency?
>
> A) Critical — under 500ms required (real-time UX)
> B) Important — under 2 seconds preferred
> C) Moderate — under 5 seconds acceptable
> D) Flexible — batch or async processing

Interpret → `ai_latency`: A → `"critical"`, B → `"important"`, C → `"moderate"`, D → `"flexible"`. Default: B → `"important"`.

**If A (critical):** Note: Haiku 4.5 or Nova Micro + streaming + provisioned throughput.

---

## Q22 — Task Complexity

> How would you describe the complexity of reasoning your AI workload requires?
>
> A) Simple — classification, extraction, summarization
> B) Moderate — multi-step reasoning, complex instructions
> C) Complex — multi-hop reasoning, planning, code generation
> D) Very complex — research-level reasoning, autonomous agent tasks

Interpret → `ai_complexity`: A → `"simple"`, B → `"moderate"`, C → `"complex"`, D → `"very-complex"`. Default: B → `"moderate"`.

**If C or D:** Note: Claude Sonnet 4.6 standard or with extended thinking; Opus 4.6 for hardest tasks.
