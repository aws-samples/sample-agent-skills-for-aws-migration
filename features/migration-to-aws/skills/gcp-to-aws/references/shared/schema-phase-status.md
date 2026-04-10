# .phase-status.json

Lightweight phase tracking. This is the SINGLE source of truth for the `.phase-status.json` schema. All steering files reference this definition.

```json
{
  "migration_id": "0226-1430",
  "last_updated": "2026-02-26T15:35:22Z",
  "current_phase": "design",
  "phases": {
    "discover": "completed",
    "clarify": "completed",
    "design": "in_progress",
    "estimate": "pending",
    "generate": "pending",
    "feedback": "pending"
  }
}
```

**Field Definitions:**

| Field           | Type     | Set When                                                         |
| --------------- | -------- | ---------------------------------------------------------------- |
| `migration_id`  | string   | Created (matches folder name, never changes)                     |
| `last_updated`  | ISO 8601 | After each phase update                                          |
| `current_phase` | string   | Optional. Set to active phase (`discover`..`generate`) or `complete` |
| `phases.<name>` | string   | Phase transitions: `"pending"` → `"in_progress"` → `"completed"` |

**Rules:**

- Phase status progresses: `"pending"` → `"in_progress"` → `"completed"`. Never goes backward.
- Valid phase names: discover, clarify, design, estimate, generate, feedback.
- If `current_phase` exists, valid values are: discover, clarify, design, estimate, generate, complete.
- Deterministic fallback when `current_phase` is absent: execute first non-completed phase in ordered list [discover, clarify, design, estimate, generate]; if none, state is complete.
- Ordered consistency rule: no later phase may be `"completed"` if an earlier phase is not `"completed"`.
- Across core phases [discover, clarify, design, estimate, generate], at most one phase may be `"in_progress"`.
- `migration_id` matches the `$MIGRATION_DIR` folder name (e.g., `0226-1430`).
