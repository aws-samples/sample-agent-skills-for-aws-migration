# Sample Agent Skills for AWS Migration

AI agent skills for migrating workloads to AWS, built for [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview) and [Cursor](https://www.cursor.com/).

## Plugins

| Plugin               | Description                                                                                                            | Status    |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------- | --------- |
| **migration-to-aws** | Migrate GCP infrastructure to AWS with resource discovery, architecture mapping, cost analysis, and execution planning | Available |

## Installation

### Claude Code

#### Add the marketplace

```bash
/plugin marketplace add aws-samples/sample-agent-skills-for-aws-migration
```

#### Install the plugin

```bash
/plugin install migration-to-aws@sample-agent-skills-for-aws-migration
```

### Cursor

> **Coming soon** — This plugin is not yet published on the Cursor Marketplace. In the meantime, you can use it locally by cloning this repository and pointing Cursor to the plugin directory.

## migration-to-aws

Helps you systematically migrate GCP infrastructure to AWS through Terraform resource discovery, architecture mapping, cost estimation, and execution planning.

### Workflow

1. **Discover** - Scan Terraform files for GCP resources and extract infrastructure
2. **Clarify** - Understand compute workloads and architecture patterns
3. **Design** - Map GCP services to AWS equivalents with rationale
4. **Estimate** - Calculate monthly AWS costs and compare to GCP
5. **Generate** - Create migration artifacts, IaC, and documentation
6. **Feedback** _(optional)_ - Collect feedback after discover or estimate phase

### Agent Skill Triggers

| Agent Skill    | Triggers                                                                                                           |
| -------------- | ------------------------------------------------------------------------------------------------------------------ |
| **gcp-to-aws** | "migrate GCP to AWS", "move from GCP", "GCP migration plan", "estimate AWS costs", "GCP infrastructure assessment" |

### MCP Servers

| Server           | Purpose                                          |
| ---------------- | ------------------------------------------------ |
| **awsknowledge** | AWS documentation, architecture guidance         |
| **awspricing**   | Real-time AWS service pricing for cost estimates |

## Requirements

- Claude Code >=2.1.29 or [Cursor >= 2.5](https://cursor.com/changelog/2-5)
- AWS CLI configured with appropriate credentials

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
mise run security      # All security scanners
```

### Evaluating Changes

Prompt files are the source code of this plugin. Changes to files under
`features/migration-to-aws/skills/gcp-to-aws/` can alter migration behavior
in subtle ways. Run the evaluation harness before submitting a PR:

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

Pick the fixture that covers your change area. For broad changes, run
`minimal-cloud-run-sql` first, then any fixture specific to your change.

| Fixture                    | Use when you changed...                                                 | Invariants |
| -------------------------- | ----------------------------------------------------------------------- | ---------- |
| `minimal-cloud-run-sql`    | General prompt changes, state machine, phase ordering, generate phase   | 26         |
| `bigquery-specialist-gate` | BigQuery handling, specialist gate, analytics exclusion                 | 9          |
| `ai-workload-openai`       | AI detection, model mapping, lifecycle rules, Category F questions      | 11         |
| `user-preferences`         | Clarify question flow, preference schema, Design preference consumption | 10         |
| `negative-services`        | Classification rules, auth exclusion, forbidden service mappings        | 8          |

See [docs/evaluation-guide.md](docs/evaluation-guide.md) for the full workflow
and how to add new invariants.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
