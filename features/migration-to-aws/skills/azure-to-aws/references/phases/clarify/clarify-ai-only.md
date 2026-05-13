# Standalone AI-Only Migration Flow

Use this flow when ONLY `ai-workload-profile.json` exists — no infrastructure IaC and no billing data. The user wants to migrate Azure OpenAI / Azure AI services calls to Amazon Bedrock without a full infrastructure migration.

**Execute ALL steps in order. Do not skip or deviate.**

---

## Step 1: Present AI-Only Context

Output:

> "I see you have Azure OpenAI / Azure AI workloads but no infrastructure Terraform or billing data. I'll focus this migration on moving your AI provider calls to Amazon Bedrock.
>
> I have [N] questions about your AI workloads, then I can design your Bedrock migration path and generate adapter code."

---

## Step 2: Ask AI-Only Questions

Present all questions in a single batch. Use question text from `clarify-ai.md` for Q14–Q22. Additionally ask:

### AO1 — Deployment Target

> Where will your application code run after migration?
>
> A) Already on AWS (EC2, Lambda, ECS, EKS) — just swapping the AI provider
> B) Migrating to AWS as part of this effort
> C) Staying on Azure — just switching AI provider to Bedrock
> D) Other

Interpret → `deployment_target`: map to string. Affects which infrastructure instructions to include in Generate.

### AO2 — Migration Urgency

> What is driving the timeline for this AI migration?
>
> A) Cost — Azure OpenAI bills are too high
> B) Reliability — quota limits or outage concerns
> C) Features — need Bedrock capabilities not on Azure OpenAI
> D) AWS consolidation — reduce vendor count
> E) No urgency — exploring options

Interpret → `migration_urgency`: map to string. No constraint applied — informational only.

---

## Step 3: Write preferences.json (AI-Only)

```json
{
  "metadata": {
    "migration_type": "ai_only",
    "timestamp": "<ISO timestamp>",
    "discovery_artifacts": ["ai-workload-profile.json"],
    "questions_asked": ["Q14", "Q15", "Q16", "Q17", "Q18", "Q19", "Q20", "Q21", "Q22", "AO1", "AO2"]
  },
  "design_constraints": {
    "target_region": { "value": "us-east-1", "chosen_by": "default" }
  },
  "ai_constraints": {
    "ai_framework": { "value": ["direct"], "chosen_by": "extracted" },
    "ai_monthly_spend": { "value": "$500-$2K", "chosen_by": "user" },
    "ai_priority": { "value": "balanced", "chosen_by": "user" },
    "ai_token_volume": { "value": "low", "chosen_by": "user" },
    "ai_model_baseline": { "value": "claude-sonnet-4-6", "chosen_by": "user" },
    "ai_latency": { "value": "important", "chosen_by": "user" },
    "ai_complexity": { "value": "moderate", "chosen_by": "user" },
    "deployment_target": { "value": "already-on-aws", "chosen_by": "user" }
  }
}
```

---

## Step 4: Update Phase Status

Write `phases.clarify: "completed"`. Output: "Clarification complete. Proceeding to Phase 3: Design AWS Architecture (AI-only path)."
