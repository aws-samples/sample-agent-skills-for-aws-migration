# App Code Discovery: Azure AI Workload Detection

Scan application source code for Azure SDK imports, Azure OpenAI usage, and AI framework patterns. Produces `ai-workload-profile.json` when AI confidence ≥ 70%.

**Execute ALL steps in order. Do not skip or deviate.**

## Step 1: Scan Source Files

Glob for source files: `**/*.py`, `**/*.js`, `**/*.ts`, `**/*.go`, `**/*.java`, `**/*.cs`, `**/*.fs`, `**/*.rs`, `**/requirements.txt`, `**/package.json`, `**/*.csproj`, `**/go.mod`, `**/pom.xml`

Read each file. Build a signal list.

## Step 2: Detect Azure AI Signals

For each source file, scan (case-insensitive) for:

**Azure OpenAI / Cognitive Services signals:**
- `openai` import or `from openai import` (Python)
- `@azure/openai` (Node.js)
- `Azure.AI.OpenAI` (C#)
- `azure-cognitiveservices-*` in requirements.txt or package.json
- `AzureOpenAI(` or `AzureOpenAI.` constructor calls
- `azure.ai.` namespace imports
- `CognitiveServicesCredentials` or `ApiKeyCredentials`
- `openai.AzureOpenAI` or `openai.AzureChatOpenAI`

**Azure ML / MLflow signals:**
- `azureml` import
- `from azureml.core` or `import azureml`
- `mlflow.set_tracking_uri` with Azure ML endpoint

**AI Framework signals (framework-agnostic but relevant):**
- `langchain`, `langchain_openai`, `langchain_azure`
- `semantic_kernel` or `SemanticKernel`
- `autogen` or `AutoGen`
- `llamaindex` or `llama_index`
- Direct `openai` SDK (may be Azure-hosted)

**Agentic signals:**
- Tool definitions (`tools=[`, `function_call`, `tool_choice`)
- Agent loop patterns (`while True:` with LLM calls)
- Memory patterns (`ConversationBufferMemory`, `VectorStoreRetriever`)
- Multi-agent patterns (`AssistantAgent`, `UserProxyAgent`, `GroupChat`)

## Step 3: Score Confidence

Assign confidence based on signals found:

| Signal Type | Confidence Contribution |
|---|---|
| `AzureOpenAI(` constructor | +0.45 |
| `@azure/openai` or `Azure.AI.OpenAI` import | +0.40 |
| `azure-cognitiveservices-*` in requirements | +0.35 |
| Generic `openai` import (may be Azure-hosted) | +0.25 |
| `langchain_openai` or `langchain_azure` | +0.20 |
| `semantic_kernel` | +0.20 |
| Agentic signal | +0.15 |
| `azureml` import | +0.30 |

Cap total at 1.0.

## Step 4: Exit Gate

If total confidence **< 0.70**: Write no `ai-workload-profile.json`. Log: "App code AI confidence [X] below threshold (0.70) — skipping AI workload profile." Exit this sub-discovery. If an `iac_azure_openai` profile already exists from `discover-iac.md`, preserve it unchanged.

If total confidence **≥ 0.70**: Continue to Step 5.

## Step 5: Detect Models

Scan for model name strings:
- `gpt-4`, `gpt-4o`, `gpt-4-turbo`, `gpt-35-turbo`, `gpt-3.5-turbo`
- `text-embedding-ada-002`, `text-embedding-3-small`, `text-embedding-3-large`
- `dall-e-3`, `whisper-1`, `tts-1`
- Azure-specific deployment names (often environment variable references like `AZURE_OPENAI_DEPLOYMENT`)

For each detected model, record:
```json
{
  "model_id": "gpt-4o",
  "provider": "azure_openai",
  "deployment_name": "gpt-4o-deployment"
}
```

## Step 6: Detect Integration Pattern

Determine the primary SDK / framework:

| Pattern | `primary_sdk` | `pattern` |
|---|---|---|
| `AzureOpenAI(` direct | `azure_openai_sdk` | `direct_api` |
| LangChain + Azure | `langchain` | `framework` |
| Semantic Kernel | `semantic_kernel` | `framework` |
| AutoGen | `autogen` | `multi_agent` |
| Generic `openai` SDK (Azure endpoint) | `openai_sdk` | `direct_api` |
| Azure ML SDK | `azureml_sdk` | `ml_pipeline` |

Detect gateway: Look for Azure API Management patterns (`apim`, `api_management`) or custom proxy.

## Step 7: Detect Agentic Patterns

Set `is_agentic: true` if ANY of:
- Tool use detected (function calling arrays)
- Agent loop patterns found
- Multi-agent framework (AutoGen, Semantic Kernel Agent Framework) imported
- Memory/retrieval patterns (RAG) with agent orchestration

If agentic, set `migration_approach` suggestion:
- AutoGen / Semantic Kernel Agents → `"strands"` (Strands Agents SDK)
- LangChain agents → `"retarget"` (provider swap)
- Custom loop → `"harness"` (AgentCore Harness)

## Step 8: Write ai-workload-profile.json

If an existing `ai-workload-profile.json` exists with `metadata.profile_source == "iac_azure_openai"`, **merge** — preserve `iac_azure_openai` data and enrich with code-detected models and integration details.

Otherwise write fresh:

```json
{
  "metadata": {
    "profile_source": "app_code",
    "confidence": 0.85,
    "confidence_level": "high",
    "files_scanned": 12,
    "files_with_ai_signals": 3
  },
  "summary": {
    "ai_source": "azure_openai",
    "is_agentic": false
  },
  "models": [
    {
      "model_id": "gpt-4o",
      "provider": "azure_openai",
      "deployment_name": "gpt-4o-deployment"
    }
  ],
  "integration": {
    "pattern": "direct_api",
    "primary_sdk": "azure_openai_sdk",
    "gateway_type": null,
    "frameworks": [],
    "capabilities_summary": {
      "text_generation": true,
      "function_calling": false,
      "streaming": false,
      "embeddings": false,
      "vision": false,
      "audio": false,
      "image_generation": false
    }
  },
  "agentic_profile": {
    "is_agentic": false
  }
}
```

`ai_source` values: `"azure_openai"`, `"azure_openai_and_other"`, `"other"` (Azure ML, Cognitive Services non-OpenAI).
