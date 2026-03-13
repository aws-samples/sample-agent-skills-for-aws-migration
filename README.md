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

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
