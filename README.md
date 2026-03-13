# Sample Agent Skills for AWS Migration

AI agent skills for migrating workloads to AWS, built for [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview) and [Cursor](https://www.cursor.com/).

## Available Skills

| Skill                                                      | Description                                                                                                                             |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| [gcp-to-aws](features/migration-to-aws/skills/gcp-to-aws/) | Migrate workloads from Google Cloud Platform to AWS with guided discovery, architecture design, cost estimation, and execution planning |

## Getting Started

### Claude Code

```bash
# Add the marketplace
/plugin marketplace add aws-samples/sample-agent-skills-for-aws-migration

# Install the plugin
/plugin install migration-to-aws
```

### Cursor

```bash
# Add the marketplace
/plugin marketplace add aws-samples/sample-agent-skills-for-aws-migration

# Install the plugin
/plugin install migration-to-aws
```

## Project Structure

```
sample-agent-skills-for-aws-migration/
├── .claude-plugin/marketplace.json     # Claude Code marketplace registry
├── .cursor-plugin/marketplace.json     # Cursor marketplace registry
├── features/
│   └── migration-to-aws/
│       ├── .claude-plugin/plugin.json  # Claude Code plugin manifest
│       ├── .cursor-plugin/plugin.json  # Cursor plugin manifest
│       ├── .mcp.json                   # Claude Code MCP servers
│       ├── mcp.json                    # Cursor MCP servers
│       ├── rules/                      # Cursor rules
│       └── skills/
│           └── gcp-to-aws/
│               ├── SKILL.md            # Skill orchestrator
│               └── references/         # Reference files for the skill
├── tools/                              # Validation scripts
└── schemas/                            # JSON schemas
```

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
