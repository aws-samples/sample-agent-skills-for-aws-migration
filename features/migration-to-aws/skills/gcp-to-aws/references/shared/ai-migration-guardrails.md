# AI Migration Guardrails

Shared warnings and constraints for all agentic migration paths. Loaded once by `design-ai.md` when `agentic_profile.is_agentic == true`. Path-specific design references (Harness, Strands, retarget) should NOT duplicate these — reference this file instead.

---

## AgentCore Regional Availability

AgentCore services have different regional footprints. Always validate via `get_regional_availability` from the `awsknowledge` MCP server before recommending.

**As of April 2026:**

| Service | Availability | Regions |
|---------|-------------|---------|
| AgentCore Runtime (GA) | 9 regions | us-east-1, us-east-2, us-west-2, ap-southeast-1, ap-southeast-2, ap-northeast-1, eu-central-1, eu-west-1, ap-south-1 |
| AgentCore Harness (Preview) | 4 regions | us-west-2, us-east-1, ap-southeast-2, eu-central-1 |
| AgentCore Memory (GA) | 9 regions | Same as Runtime |
| AgentCore Gateway (GA) | 9 regions | Same as Runtime |

**IMPORTANT:** These lists go stale. The `get_regional_availability` MCP call is the source of truth. Use the table above only as a fallback if the MCP call fails.

**If target region is unavailable for a recommended service:**
1. Flag prominently in `aws-design-ai.json` → `regional_warnings[]`
2. Suggest nearest available region as alternative
3. Note in user summary: "[Service] is not yet available in [target region]. Nearest available: [alternative]."

---

## AgentCore Harness Preview Caveats

- Harness is in **public preview** — not GA. Production workloads should evaluate stability.
- No separate Harness charge — pay only for underlying AgentCore capabilities (Runtime, Memory, Gateway).
- Harness is powered by Strands Agents internally. Custom orchestration can switch from config-based to code-defined harness without rearchitecting.
- Harness supports Bedrock, OpenAI, and Google Gemini models. Third-party API keys stored in AgentCore Identity token vault.

---

## Bedrock Mantle Endpoint Throughput Limits

The `bedrock-mantle` endpoint (OpenAI-compatible) has a **hard limit of 10,000 RPM per account per region, shared across all models on that endpoint**. This is separate from the per-model TPM quotas on `bedrock-runtime`.

**Key implications for migrations:**

| Scenario | Risk | Action |
|----------|------|--------|
| Single model, moderate traffic | Low | Standard on-demand acceptable |
| Multiple models all routed through Mantle | Medium | 10K RPM is shared — monitor aggregate RPM, not per-model |
| High-volume production workload on Mantle | High | Request RPM quota increase via Service Quotas; consider `bedrock-runtime` (Converse API) for higher throughput |

**Claude 4.7+ on Mantle:** Input TPM is account-history-dependent (check Service Quotas console). Output TPM is capped at 2M. All other models on Mantle have no per-model TPM limit — only the shared 10K RPM applies.

**When to recommend `bedrock-runtime` over Mantle:**
- User has `ai_token_volume = "high"` or `"very_high"`
- Multiple models are being migrated simultaneously
- User needs batch inference (not available on Mantle)
- User needs reserved capacity (not available on Mantle)

Surface this in the design summary when `integration.pattern = "direct_sdk"` and `ai_source = "openai"` and `ai_token_volume` is `"medium"` or higher.

---

## Model Lifecycle Checks

Before recommending any Bedrock model in an agentic design:

1. Check `references/shared/ai-model-lifecycle.md` for model status
2. Do NOT recommend Legacy models as primary selections
3. If a model is approaching EOL, note the date and suggest the Active successor

---

## Pricing Source Rules

For agentic workload cost estimation:

1. **Primary:** `references/shared/pricing-cache.md` (±5-10% accuracy)
2. **Secondary:** `awspricing` MCP server (±5-10%, real-time)
3. **Tertiary:** `references/shared/pricing-fallback.md` (±15-25%, broad coverage)

AgentCore Runtime and Harness pricing: consumption-based, no upfront cost. Include in estimate only if the user selects Harness or Strands path.

---

## Effort Estimation Rules

Do NOT output fixed week estimates for agentic migrations. Output ranges with drivers:

**Format:** "[low]–[high] weeks depending on [driver 1] ([value]), [driver 2] ([value]), [driver 3] ([value])"

**Drivers to include:**
- Agent count (from `agentic_profile.agent_count`)
- Tool count (from `agentic_profile.tool_count`)
- Orchestration complexity (from `agentic_profile.orchestration_pattern`)
- Framework familiarity (team's experience with target framework)
- Test coverage (existing tests reduce migration risk)

**Example:** "2–5 weeks depending on agent count (3), tool count (8), and graph complexity (hierarchical with conditional routing)"
