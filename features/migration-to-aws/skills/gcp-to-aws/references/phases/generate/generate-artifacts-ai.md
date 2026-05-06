# Generate Phase: AI Artifact Generation

> Loaded by generate.md when generation-ai.json and aws-design-ai.json exist.

**Execute ALL steps in order. Do not skip or optimize.**

## Overview

Generate migration artifacts from the AI migration plan and design. Artifacts vary by gateway type detected in discovery.

**Outputs (all users):**

- `ai-migration/setup_bedrock.sh` — Bedrock model access and IAM setup
- `ai-migration/test_comparison.py` — A/B test harness (always Python)

**Outputs (direct SDK users — `ai_framework` = `"direct"`):**

- `ai-migration/provider_adapter.{py,js,go}` — Provider abstraction with feature flag

**Outputs (gateway users — `ai_framework` != `"direct"`):**

- `ai-migration/gateway_config.{yaml,py,json}` — Gateway-specific configuration snippet

**Outputs (if user opted into model evaluation in generate-ai.md Part 0):**

- `ai-migration/eval-prompts.jsonl` — Evaluation prompt dataset
- `ai-migration/run-evaluation.sh` — Bedrock evaluation job script

## Prerequisites

Read from `$MIGRATION_DIR/`:

- `aws-design-ai.json` (REQUIRED) — AI architecture with model mappings and code migration plan
- `generation-ai.json` (REQUIRED) — AI migration plan with timeline and rollback strategy
- `ai-workload-profile.json` (REQUIRED) — AI workload profile with models, languages, and capabilities

If any required file is missing: **STOP**. Output: "Missing required artifact: [filename]. Complete the prior phase that produces it."

**Sparse / IaC-only profile:** If `ai-workload-profile.json` has empty `models[]` or `metadata.profile_source` is `iac_vertex`, use `aws-design-ai.json` for Bedrock targets and example prompts; do **not** fail solely because discovery did not list model IDs.

---

## Step 0: Determine Artifact Path

Check `preferences.json` → `ai_constraints.ai_framework.value`:

- `"direct"` or absent → Generate provider adapter (Step 1) + setup (Step 3) + test harness (Step 2)
- `"llm_router"`, `"api_gateway"`, `"voice_platform"`, or `"framework"` → Skip Step 1, generate gateway config (Step 3B) instead

**Determine language** (direct SDK users only): Read `ai-workload-profile.json` → `integration.languages` array. Use the first entry: `"python"` → `.py`, `"javascript"`/`"typescript"` → `.js`, `"go"` → `.go`, other/unknown → `.py`.

---

## Step 1: Generate Provider Adapter (Direct SDK Only)

Generate `ai-migration/provider_adapter.{py,js,go}` — an abstraction layer that lets the user switch between the source AI provider and Bedrock via an environment variable.

**Requirements:**

- Read `AI_PROVIDER` env var to select provider: `vertex_ai` (current), `bedrock` (target), `shadow` (both — return source response, log Bedrock response)
- Expose only the methods matching capabilities in `ai-workload-profile.json` → `integration.capabilities_summary`:
  - `text_generation: true` → `generate(prompt) → str`
  - `streaming: true` → `generate_stream(prompt) → Iterator[str]`
  - `embeddings: true` → `embed(text) → list[float]`
- **Source provider class**: Use SDK imports from `ai-workload-profile.json` → `integration.sdk_imports`. Use model IDs from `ai-workload-profile.json` → `models[].model_id`.
- **Bedrock provider class**: Use `boto3` Converse API (`converse` for generate, `converse_stream` for streaming, `invoke_model` for embeddings with Titan). Use model IDs from `aws-design-ai.json` → `ai_architecture.bedrock_models[].aws_model_id`. Use region from `preferences.json` → `design_constraints.target_region`.
- **Shadow mode**: Send requests to both providers, return source response, log Bedrock response for comparison.
- Include error handling and logging for API calls.

For JS: use `@aws-sdk/client-bedrock-runtime` + `@google-cloud/vertexai`. For Go: use `github.com/aws/aws-sdk-go-v2/service/bedrockruntime` + `cloud.google.com/go/aiplatform`.

---

## Step 2: Generate Test Comparison Harness

Generate `ai-migration/test_comparison.py` — always Python regardless of adapter language.

**Requirements:**

- Accept prompts from a JSON file (`--prompts`) or use built-in defaults (`--quick`)
- Run each prompt against both the source provider and Bedrock
- Measure per-prompt: latency (ms), success/failure, response text (truncated to 500 chars)
- Compute summary statistics: p50/p95/mean latency per provider, quality score (trait matching against expected traits), pass/fail criteria
- Pass criteria: Bedrock latency ≤ 2x source latency, mean quality score ≥ 0.9
- Output structured JSON to `--output` (default: `comparison_results.json`)
- Built-in test prompts: include 3-5 prompts based on `ai-workload-profile.json` → `models[].usage_context` covering the primary use case
- Import the provider adapter via `from provider_adapter import get_provider`

---

## Step 3: Generate Bedrock Setup Script

Generate `ai-migration/setup_bedrock.sh`.

**Requirements:**

- Dry-run by default (`--execute` flag to run for real)
- Step 1 — Request model access: List each model from `aws-design-ai.json` → `bedrock_models[].aws_model_id` and the embedding model
- Step 2 — Create IAM role: Trust policy for the compute platform (Lambda, ECS, or EC2 based on `aws-design.json` if present). Bedrock policy: `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` scoped to `arn:aws:bedrock:*::foundation-model/*`
- Step 3 — Print required environment variables: `AWS_REGION`, `AI_PROVIDER=bedrock`, model IDs
- Step 4 — Check quota: Query current TPM quota for the primary model via `aws service-quotas get-service-quota`. If `aws-design-ai.json` → `ai_architecture.quota_risk` is `"high"` or `"medium"`, print warning: "⚠️ Your token volume may exceed default Bedrock quotas. Request a quota increase via Service Quotas console (allow 1–5 business days)." Include the `aws service-quotas request-service-quota-increase` command template.
- Step 5 — Verification: Test Bedrock access with a simple `converse` call using the primary model
- If `$MIGRATION_DIR/terraform/` exists, print coordination note: "Ensure the IAM role is referenced in compute.tf task definitions"
- Use region from `preferences.json` → `design_constraints.target_region`

---

## Step 3B: Generate Gateway Configuration (Gateway Users Only)

Skip if `ai_framework` = `"direct"` or absent. Read `preferences.json` → `ai_constraints.ai_framework.value` to determine format.

**`"llm_router"`** → Generate `gateway_config.yaml` (LiteLLM format):

- Map each model from `aws-design-ai.json` to a `bedrock/MODEL_ID` entry with `aws_region_name`
- Include embedding model entry if embeddings are used
- Note required env vars: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`

**`"llm_router"` + OpenRouter detected** (evidence: `base_url` containing `openrouter.ai` in `ai-workload-profile.json` → `detection_signals`):

Check `aws-design-ai.json` → `code_migration.openrouter_path` (set in Design Part 5):

- `"direct"` → Skip gateway config. Generate provider adapter instead (same as Step 1 for direct SDK users). Note: "Migrating from OpenRouter to direct Bedrock API removes the routing middleman and OpenRouter's margin."
- `"litellm"` → Generate `gateway_config.yaml` in LiteLLM format (standard `llm_router` logic above) + add header comment: "# Migration from OpenRouter to self-hosted LiteLLM with Bedrock backend\n# Install: pip install litellm\n# Run: litellm --config gateway_config.yaml"
- `"keep_openrouter"` → Generate `gateway_config.json` with OpenRouter model ID mappings:
  ```json
  {
    "models": {
      "original_model_id": "amazon/{bedrock_model_id}",
      "original_embedding_id": "amazon/{titan_embedding_model_id}"
    },
    "notes": "OpenRouter adds margin on top of provider pricing. Compare OpenRouter pricing vs direct Bedrock pricing in your cost estimate."
  }
  ```
- If `openrouter_path` is absent: default to `"litellm"` (standard LiteLLM config generation)

**`"framework"`** → Generate `gateway_config.py`:

- Show before/after import swap for the detected framework (`ai-workload-profile.json` → `integration.sdk_imports`)
- LangChain: `langchain_google_vertexai` → `langchain_aws.ChatBedrock` (or `langchain_openai` → `langchain_aws.ChatBedrock`)
- LlamaIndex: `llama_index.llms.vertex` → `llama_index.llms.bedrock_converse`
- Include pip install note for the AWS package

**`"voice_platform"`** → Generate `gateway_config.json`:

- Dashboard configuration steps: add Bedrock as provider, set model ID, set region, test before switching production
- Include the Bedrock model ID and region from design artifacts

**`"api_gateway"`** → Generate `gateway_config.yaml`:

- Upstream URL: `https://bedrock-runtime.{region}.amazonaws.com`
- Auth: AWS SigV4 signing for the `bedrock` service
- Note: Converse API endpoint is `POST /model/{modelId}/converse`
- Include gateway-specific notes (Kong plugin, Apigee policy)

---

## Step 3C: Generate AgentCore Harness Artifacts (Harness Users Only)

**Skip if** `aws-design-ai.json` → `agentic_design` is absent OR `agentic_design.migration_approach != "harness"`.

Read `aws-design-ai.json` → `agentic_design.harness_config` for all configuration values.

**Artifact 1: `ai-migration/harness.json`**

Generate the Harness configuration file:

```json
{
  "name": "{harness_config.name}",
  "model": "{harness_config.model_id}",
  "systemPrompt": "{harness_config.system_prompt}",
  "tools": [
    // Each tool from harness_config.tools, mapped to Harness tool format:
    // remote_mcp: {"type": "remote_mcp", "name": "...", "config": {"remoteMcp": {"url": "..."}}}
    // agentcore_browser: {"type": "agentcore_browser", "name": "browser"}
    // agentcore_code_interpreter: {"type": "agentcore_code_interpreter", "name": "code_interpreter"}
    // agentcore_gateway: {"type": "agentcore_gateway", "name": "...", "config": {"agentCoreGateway": {"gatewayArn": "[TODO: Gateway ARN]"}}}
    // inline_function: {"type": "inline_function", "name": "...", "config": {"inlineFunction": {"description": "...", "inputSchema": {...}}}}
  ]
}
```

Use actual values from `harness_config` — no placeholders except where noted with `[TODO: ...]`. Include a comment header explaining the file's purpose.

**Artifact 2: `ai-migration/deploy_harness.sh`**

Generate deployment script. Dry-run by default (`--execute` flag to run for real).

```bash
#!/bin/bash
# AgentCore Harness Deployment Script
# Generated by GCP-to-AWS migration plugin
# Run with --execute to perform actual deployment (default: dry-run)
set -euo pipefail

EXECUTE=${1:-""}
HARNESS_NAME="{harness_config.name}"
MODEL_ID="{harness_config.model_id}"
REGION="{target_region from preferences.json}"

run_cmd() {
    if [ "$EXECUTE" = "--execute" ]; then
        echo ">>> $*"
        eval "$@"
    else
        echo "[DRY-RUN] $*"
    fi
}

echo "=== AgentCore Harness Deployment: $HARNESS_NAME ==="
echo "Model: $MODEL_ID"
echo "Region: $REGION"
echo ""

# Step 1: Verify AgentCore CLI is installed
if ! command -v agentcore &> /dev/null; then
    echo "AgentCore CLI not found. Install with:"
    echo "  pip install bedrock-agentcore-cli"
    if [ "$EXECUTE" != "--execute" ]; then
        echo "[DRY-RUN] Continuing with remaining steps..."
    else
        exit 1
    fi
fi

# Step 2: Create project
run_cmd "agentcore create --name $HARNESS_NAME"

# Step 3: Add harness with model and tools
run_cmd "agentcore add harness --name $HARNESS_NAME \\
  --model-id $MODEL_ID \\
  --system-prompt '{harness_config.system_prompt}' \\
  --tools {comma-separated tool types from harness_config.tools}"

# Step 4: Deploy
run_cmd "agentcore deploy"

# Step 5: Test invocation
echo ""
echo "=== Test Invocation ==="
run_cmd "agentcore invoke --harness $HARNESS_NAME \\
  'Hello, this is a test invocation to verify deployment.'"

echo ""
echo "=== Deployment Complete ==="
echo "Next steps:"
echo "  1. Test with representative prompts: agentcore invoke --harness $HARNESS_NAME 'your prompt'"
echo "  2. Override model for A/B testing: agentcore invoke --harness $HARNESS_NAME --model-id <alt-model> 'prompt'"
echo "  3. View logs: agentcore logs --harness $HARNESS_NAME"
```

**Artifact 3: `ai-migration/incremental_migration.sh`** (only if `harness_config.incremental_migration == true`)

Generate incremental migration script showing multi-model switching:

```bash
#!/bin/bash
# Incremental Migration: Source Provider → Bedrock via AgentCore Harness
# This script demonstrates the multi-model switching capability.
# Run each phase manually and validate before proceeding to the next.
set -euo pipefail

HARNESS_NAME="{harness_config.name}"
SOURCE_PROVIDER="{harness_config.source_model_provider}"
SOURCE_MODEL="{harness_config.source_model_id}"
BEDROCK_MODEL="{harness_config.model_id}"
SESSION_ID=$(uuidgen)

echo "=== Incremental Migration Plan ==="
echo "Source: $SOURCE_PROVIDER / $SOURCE_MODEL"
echo "Target: Bedrock / $BEDROCK_MODEL"
echo "Session: $SESSION_ID"
echo ""

# Phase 0: Store source provider API key in AgentCore Identity
echo "--- Phase 0: Configure source provider credentials ---"
echo "Run once:"
echo "  agentcore add credential --type api-key --name source-provider-key --api-key \$SOURCE_API_KEY"
echo "  agentcore deploy"
echo ""

# Phase 1: Invoke with source provider model on AgentCore infrastructure
echo "--- Phase 1: Source provider on AgentCore ---"
echo "agentcore invoke --harness $HARNESS_NAME \\"
echo "  --model-provider $SOURCE_PROVIDER \\"
echo "  --model-id $SOURCE_MODEL \\"
echo "  --api-key-arn arn:aws:bedrock-agentcore:{region}:{account}:token-vault/default/apikeycredentialprovider/source-provider-key \\"
echo "  --session-id $SESSION_ID \\"
echo "  'Your test prompt here'"
echo ""

# Phase 2: Same session, switch to Bedrock model
echo "--- Phase 2: Bedrock model (same session, context preserved) ---"
echo "agentcore invoke --harness $HARNESS_NAME \\"
echo "  --model-id $BEDROCK_MODEL \\"
echo "  --session-id $SESSION_ID \\"
echo "  'Same test prompt for comparison'"
echo ""

# Phase 3: Update default model
echo "--- Phase 3: Switch default to Bedrock ---"
echo "Edit app/$HARNESS_NAME/harness.json: set \"model\" to \"$BEDROCK_MODEL\""
echo "agentcore deploy"
echo ""

# Phase 4: Remove source provider
echo "--- Phase 4: Clean up source provider credentials ---"
echo "After 48h stable on Bedrock:"
echo "  Remove API key from AgentCore Identity"
echo "  agentcore deploy"
echo ""
echo "=== Migration Complete ==="
```

---

## Step 3D: Generate Evaluation Artifacts (If User Opted In)

Skip if the user did not opt into model evaluation in `generate-ai.md` Part 0.

**`eval-prompts.jsonl`**: Generate 10-20 domain-specific prompts in JSONL format (`{"prompt": "...", "referenceResponse": "", "category": "..."}`). Base prompts on `ai-workload-profile.json` → `models[].usage_context`. Include function-calling prompts if `capabilities_summary.function_calling` is true, retrieval prompts if RAG patterns were detected. Include 2-3 edge case prompts.

**`run-evaluation.sh`**: Dry-run by default. Creates S3 bucket, uploads prompts, calls `aws bedrock create-evaluation-job` with model IDs from `aws-design-ai.json`, downloads results. Use the same model IDs and region as `setup_bedrock.sh`.

---

## Step 4: Self-Check

Verify all generated artifacts:

- [ ] Provider adapter (or gateway config) uses actual model IDs from `aws-design-ai.json` — no placeholders
- [ ] Only capabilities present in `capabilities_summary` have methods/tests generated
- [ ] Feature flag (`AI_PROVIDER` env var) controls provider selection in adapter
- [ ] Test harness includes domain-specific prompts from `usage_context`
- [ ] Test harness produces structured JSON output with latency and quality metrics
- [ ] Setup script has correct region from `preferences.json`
- [ ] Setup script IAM role follows least privilege
- [ ] All scripts default to dry-run mode
- [ ] Evaluation artifacts (if generated) have correct model IDs and region
- [ ] No hardcoded credentials in any file
- [ ] If Harness artifacts generated: `harness.json` uses actual model ID from `agentic_design.harness_config.model_id`
- [ ] If Harness artifacts generated: `harness.json` tool types match `tool_manifest[].transport` mapping
- [ ] If Harness artifacts generated: `deploy_harness.sh` defaults to dry-run
- [ ] If Harness artifacts generated: `incremental_migration.sh` only present when `incremental_migration == true`
- [ ] If OpenRouter path: artifact type matches `code_migration.openrouter_path` value

## Phase Completion

Report generated files to the parent orchestrator. **Do NOT update `.phase-status.json`** — the parent `generate.md` handles phase completion.

Output:

```
Generated AI migration artifacts:
- ai-migration/setup_bedrock.sh
- ai-migration/test_comparison.py
- ai-migration/provider_adapter.{py|js|go}    # Direct SDK users only
- ai-migration/gateway_config.{yaml|py|json}  # Gateway users only
- ai-migration/harness.json                    # Harness users only
- ai-migration/deploy_harness.sh              # Harness users only
- ai-migration/incremental_migration.sh       # Harness + incremental only
- ai-migration/eval-prompts.jsonl              # If evaluation opted in
- ai-migration/run-evaluation.sh               # If evaluation opted in

Gateway type: [ai_framework value]
Language: [detected language]
Models to migrate: [count] models
Capabilities covered: [list from capabilities_summary]
```
