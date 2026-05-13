# Sample Agent Skills for AWS Migration

AI agent skills for migrating workloads to AWS, built for [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview)
and [Cursor](https://www.cursor.com/).

## What This Does

Point this plugin at your codebase, Terraform files, or GCP billing data. It runs a structured 6-phase
migration assessment — discovering what you have, asking the right questions, designing the AWS
architecture, estimating costs with current pricing data, and generating runnable migration artifacts.

**For AI-focused startups**, it goes further:

- **Detects your entire AI stack** — not just "you use GPT-4o" but your agents, tools, orchestration
  patterns, memory layers, and multi-model pipelines
- **Recommends three migration paths** for agentic workloads: retarget (keep your framework, swap
  models), AgentCore Harness (config-based managed agents), or Strands Agents (AWS-native multi-agent
  SDK)
- **Surfaces options you wouldn't find on your own** — like Strands Agents (open-source, powers
  AgentCore internally) and AgentCore Harness (declare an agent in 3 API calls)
- **Generates runnable artifacts** — `harness.json`, deployment scripts, incremental migration scripts,
  provider adapters — tailored to your specific models, tools, and architecture
- **Gives honest pricing comparisons** — finds the best Bedrock option for your workload with current
  April 2026 pricing data, including side-by-side cost comparisons against your existing OpenAI/Gemini
  spend. Calls out cases where staying on your current provider is the cheaper choice.

## Quick Start

```bash
# 1. Add the marketplace and install the plugin (Claude Code)
/plugin marketplace add aws-samples/sample-agent-skills-for-aws-migration
/plugin install migration-to-aws@sample-agent-skills-for-aws-migration

# 2. cd into a project with Terraform, app code, or GCP billing exports
cd path/to/your/gcp-project

# 3. Trigger the skill
"migrate from GCP to AWS"
```

The skill creates a `.migration/<MMDD-HHMM>/` directory in the current working directory and writes
all artifacts there. The directory is automatically gitignored. You can resume an in-progress
migration by re-invoking the skill in the same project — phase status is persisted between runs.

## Plugins

| Plugin               | Description                                                                                                                                     | Status    |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| **migration-to-aws** | Migrate GCP infrastructure and AI/agentic workloads to AWS with resource discovery, architecture mapping, cost analysis, and execution planning | Available |

## Installation

### Claude Code

```bash
# Add the marketplace
/plugin marketplace add aws-samples/sample-agent-skills-for-aws-migration

# Install the plugin
/plugin install migration-to-aws@sample-agent-skills-for-aws-migration
```

### Cursor

This repository ships a Cursor plugin manifest at `.cursor-plugin/marketplace.json`. The plugin is
not yet published to the Cursor Marketplace; for now, install locally:

```bash
git clone https://github.com/aws-samples/sample-agent-skills-for-aws-migration.git
# Then point Cursor at the cloned repository's plugin directory:
#   features/migration-to-aws
```

See [Cursor's plugin documentation](https://cursor.com/changelog/2-5) for current local-install steps.

## migration-to-aws

### Workflow

1. **Discover** — Scan Terraform files, application code, and/or billing data. Detects GCP resources,
   AI models, agentic frameworks, tools, and orchestration patterns.
2. **Clarify** — Ask targeted questions about migration preferences, AI priorities, agentic migration
   approach, memory requirements, and timeline. **Mandatory** — cannot be skipped.
3. **Design** — Map GCP services to AWS equivalents. For AI workloads: select Bedrock models with
   honest pricing comparison. For agentic workloads: design AgentCore Harness config or Strands
   architecture.
4. **Estimate** — Calculate monthly AWS costs using cached pricing data with the AWS Pricing MCP as
   fallback. Compare to current GCP/OpenAI spend.
5. **Generate** — Create migration artifacts: Terraform, provider adapters, `harness.json`, deployment
   scripts, incremental migration scripts, MIGRATION_GUIDE.md, README.md, and a self-contained HTML
   migration report.
6. **Feedback** _(optional)_ — Collect anonymized feedback to improve the tool. Offered at two
   checkpoints: after Discover and after Estimate.

### Inputs and Outputs

You provide **at least one** of these inputs:

| Input            | Files                                          | Enables                                |
| ---------------- | ---------------------------------------------- | -------------------------------------- |
| Terraform IaC    | `.tf` files (optionally `.tfvars`, `.tfstate`) | Full infrastructure design path        |
| Application code | Source files with GCP SDK or AI imports        | AI workload detection, agentic profile |
| Billing data     | GCP billing/cost/usage CSV or JSON exports     | Billing-only design fallback           |

The skill produces a per-run directory under `.migration/`:

```text
.migration/0226-1430/
├── .phase-status.json              # State machine: which phases are complete
├── .gitignore                      # Auto-generated to keep artifacts out of source control
├── gcp-resource-inventory.json     # From Discover (Terraform)
├── gcp-resource-clusters.json      # From Discover (Terraform)
├── ai-workload-profile.json        # From Discover (app code, when AI detected)
├── billing-profile.json            # From Discover (billing exports)
├── preferences.json                # From Clarify
├── aws-design.json                 # From Design (infrastructure path)
├── aws-design-ai.json              # From Design (AI workload path)
├── aws-design-billing.json         # From Design (billing-only fallback)
├── estimation-infra.json           # From Estimate
├── estimation-ai.json              # From Estimate
├── estimation-billing.json         # From Estimate
├── generation-infra.json           # From Generate
├── terraform/                      # Generated Terraform configurations
├── scripts/                        # Migration shell scripts
├── ai-migration/                   # Provider adapters, test harness
├── validation-report.json          # From Generate (infra path)
├── MIGRATION_GUIDE.md              # Human-readable migration plan
├── README.md                       # Overview of generated artifacts
├── migration-report.html           # Self-contained shareable report
├── feedback.json                   # From Feedback (if user opts in)
└── trace.json                      # Anonymized trace (if user opts in)
```

### What It Detects

| Category             | Examples                                                                                              |
| -------------------- | ----------------------------------------------------------------------------------------------------- |
| Infrastructure       | Cloud Run, Cloud SQL, GKE, Cloud Functions, Pub/Sub, Cloud Storage, VPC, DNS                          |
| AI Models            | OpenAI (GPT-4o, GPT-5.4, o-series, embeddings, image, speech), Gemini (Pro, Flash), Anthropic, Cohere |
| Agentic Frameworks   | LangGraph, CrewAI, AutoGen, OpenAI Agents SDK, Strands, custom agent loops                            |
| Integration Patterns | Direct SDK, LangChain, LlamaIndex, LiteLLM, OpenRouter, MCP servers                                   |
| Agent Architecture   | Single agent, hierarchical, swarm, graph, sequential orchestration                                    |
| Tools & Memory       | Tool definitions with transport/auth classification, memory backends (Redis, Postgres, vector stores) |

### What's Out of Scope

This plugin is intentionally narrow. Do **not** use it for:

- **Azure or on-premises migrations** to AWS
- **AWS-to-GCP** reverse migrations
- **GCP-to-GCP** refactoring
- **Multi-cloud deployments** that do not involve migrating off GCP
- General AWS architecture advice without migration intent

For these, use a different agent skill or work with your AWS account team directly.

### Specialist Engagement and Exclusions

The plugin makes a few opinionated decisions about what it will **not** auto-recommend, to avoid
generating bad migration plans for things that genuinely need human review.

**BigQuery → specialist gate.** Any `google_bigquery_*` resource is mapped to
`Deferred — specialist engagement` with `human_expertise_required: true`. The plugin does **not**
prescribe Athena, Redshift, Glue, or EMR as automated targets. Query patterns, data volume, SLAs, and
cost models all require assessment. Customers are directed to engage their AWS account team or a data
analytics migration partner. This applies to BigQuery ML (`google_bigquery_ml_*`) as well — no
automated SageMaker target.

**Third-party auth providers → keep existing.** Auth0, Firebase Auth, Supabase Auth, Clerk, Okta,
Keycloak, NextAuth, and `google_identity_platform_*` / `google_firebase_auth_*` resources are
detected but excluded from migration scope. Auth providers work cross-cloud and should not be
replaced with AWS Cognito as part of a lift-and-shift.

**Forbidden compute targets.** Containerized workloads steer to ECS Fargate (default), Lambda
(event-driven), or EKS (Kubernetes required). The skill will **not** generate Lightsail or Elastic
Beanstalk recommendations — these are explicitly excluded by negative invariants in the test suite.

### Confidence Labels

Every service mapping in `aws-design.json` is tagged with a confidence label that tells you how the
target was chosen:

| JSON value         | What it means                                                              | User-facing label               |
| ------------------ | -------------------------------------------------------------------------- | ------------------------------- |
| `deterministic`    | GCP resource type is in the fixed Direct Mappings table; no rubric needed  | **Standard pairing**            |
| `inferred`         | Agent ran the 6-criteria rubric (eliminators, op model, preferences, etc.) | **Tailored to your setup**      |
| `billing_inferred` | Mapping derived from GCP billing SKUs without full IaC                     | **Estimated from billing only** |

The MIGRATION_GUIDE.md and HTML report use the user-facing labels. The JSON artifacts keep the raw
values for downstream tooling.

### Defaults

- **IaC output**: Terraform (HCL)
- **Region**: `us-east-1` unless the user specifies, or GCP region → AWS region mapping suggests otherwise
- **Sizing**: Development tier (e.g., `db.t4g.micro`, 0.5 ACU for Aurora Serverless v2). Upgrade only
  when production is explicitly requested.
- **Re-platform by default**: Cloud Run → Fargate, Cloud SQL → RDS Aurora, etc. Existing application
  architecture patterns are preserved.
- **Cost currency**: USD
- **Timeline**: 2–18 weeks depending on complexity tier (small / medium / large)
- **One-time costs**: Quantifiable infrastructure charges only (e.g., GCP egress when billing data is
  available). The plugin does **not** estimate human migration cost (FTE counts, training, professional
  services).

### Agent Skill Triggers

| Agent Skill    | Triggers                                                                                                          |
| -------------- | ----------------------------------------------------------------------------------------------------------------- |
| **gcp-to-aws** | "migrate GCP to AWS", "move from GCP", "GCP migration plan", "estimate AWS costs", "migrate my AI app to AWS"     |

### MCP Servers

| Server           | Transport         | Purpose                                                          |
| ---------------- | ----------------- | ---------------------------------------------------------------- |
| **awsknowledge** | HTTP              | AWS documentation, regional availability, architecture guidance  |
| **awspricing**   | stdio (via `uvx`) | Real-time AWS service pricing — fallback when cache misses       |

The Estimate phase prefers `references/shared/pricing-cache.md` (cached 2026 rates, ±5–10% for
infrastructure, ±15–25% for AI models). The `awspricing` MCP is consulted only for services not in
the cache. If the MCP is unavailable after 3 attempts, the cache is used and `pricing_source:
"cached_fallback"` is recorded in the estimation JSON.

## What You Get That a Base LLM Can't

| Capability               | Base LLM                              | This Plugin                                                                                                                                  |
| ------------------------ | ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Model recommendation     | Generic "use Bedrock"                 | Your specific models mapped with pricing, honest assessment per model, stay-or-migrate recommendation                                        |
| Agentic migration        | "Swap ChatOpenAI for ChatBedrock"     | Detects your framework, agents, tools, orchestration pattern. Recommends retarget vs Harness vs Strands with effort ranges.                  |
| Multi-model coordination | Generic advice                        | Warns about re-embedding requirements, cascade pair testing, tiered strategies — based on your actual model usage                            |
| Framework gotchas        | Not covered                           | Documents real issues: LangGraph checkpointer incompatibility, CrewAI hierarchical process failures with smaller models, async exhaustion    |
| Regional validation      | Outdated region lists                 | Live `get_regional_availability` MCP call — catches "AgentCore Harness isn't in your target region" before you commit                        |
| Cost estimation          | Stale pricing                         | Three-tier pricing: cached current rates, live AWS Pricing API, fallback. Tolerance bands declared per artifact.                             |
| Generated code           | Generic templates                     | Your model IDs, your tool names, your system prompts, your region — in runnable scripts                                                      |
| Incremental migration    | Not suggested                         | Run existing OpenAI models on AgentCore infrastructure today, A/B test with Bedrock per-invocation, swap when confident                      |

## Requirements

- Claude Code >= 2.1.29 or [Cursor >= 2.5](https://cursor.com/changelog/2-5)
- AWS CLI configured with appropriate credentials
- `uvx` available on the PATH (used to run the `awspricing` MCP server)
- At least one input source: Terraform files, application code, or GCP billing data
- **For AI/agentic migration:** Application source code is required (billing/IaC alone cannot detect
  agent architecture)

## Development

This project uses [mise](https://mise.jdx.dev) for tool management and task running.

```bash
# Install tools
mise install

# Run the full build (lint, format, validate, security)
mise run build

# Individual tasks
mise run lint          # All linters (markdown, manifests, cross-refs)
mise run fmt           # Format with dprint
mise run fmt:check     # Check formatting
mise run security      # All security scanners (Bandit, SemGrep, Gitleaks, Checkov)
```

### Evaluating Changes

Prompt files are the source code of this plugin. Changes to files under
`features/migration-to-aws/skills/gcp-to-aws/` can alter migration behavior in subtle ways. Run the
evaluation harness before submitting a PR:

```bash
# 1. Quick structural check (instant, no Claude API calls)
mise run eval:check

# 2. Run the migration skill against a test fixture (see table below)
cd tests/fixtures/<FIXTURE_NAME>
# In Claude Code: "migrate from GCP to AWS"

# 3. Validate the output
python tools/eval_check.py \
  --migration-dir .migration/<RUN_ID> \
  --fixture <FIXTURE_NAME>

# 4. Commit results
git add .eval-results.json
```

#### Test Fixtures

Pick the fixture that covers your change area. For broad changes, run `minimal-cloud-run-sql` first,
then any fixture specific to your change.

| Fixture                    | Use when you changed...                                                 | Invariants |
| -------------------------- | ----------------------------------------------------------------------- | ---------- |
| `minimal-cloud-run-sql`    | General prompt changes, state machine, phase ordering, generate phase   | 26         |
| `bigquery-specialist-gate` | BigQuery handling, specialist gate, analytics exclusion                 | 9          |
| `ai-workload-openai`       | AI detection, model mapping, lifecycle rules, Category F questions      | 11         |
| `user-preferences`         | Clarify question flow, preference schema, Design preference consumption | 10         |
| `negative-services`        | Classification rules, auth exclusion, forbidden service mappings        | 8          |

See [docs/evaluation-guide.md](docs/evaluation-guide.md) for the full workflow and how to add new
invariants.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release notes. The plugin currently ships at v1.1.0.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
