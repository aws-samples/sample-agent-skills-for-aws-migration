# Graph Report - sample-agent-skills-for-aws-migration  (2026-05-06)

## Corpus Check
- 37 files · ~123,727 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 116 nodes · 100 edges · 37 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8a2bbd66`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]

## God Nodes (most connected - your core abstractions)
1. `validateMarketplace()` - 7 edges
2. `readJson()` - 5 edges
3. `main()` - 5 edges
4. `addError()` - 4 edges
5. `validatePluginJson()` - 4 edges
6. `validateMcpJson()` - 4 edges
7. `run_check()` - 4 edges
8. `check_phrases()` - 3 edges
9. `load_invariants()` - 3 edges
10. `check_custom()` - 3 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Communities (37 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (23): check_content_absent(), check_content_present(), check_cross_file_join(), check_custom(), check_file_absent(), check_file_exists(), check_json_every(), check_json_path_value() (+15 more)

### Community 1 - "Community 1"
Cohesion: 0.46
Nodes (7): addError(), addWarning(), isSafeRelativePath(), main(), pathExists(), readJson(), validateMarketplace()

### Community 2 - "Community 2"
Cohesion: 0.71
Nodes (6): addError(), findFiles(), main(), readJson(), validateMcpJson(), validatePluginJson()

### Community 3 - "Community 3"
Cohesion: 0.33
Nodes (5): generate_response(), get_embedding(), Chatbot API — uses OpenAI SDK for text generation and embeddings., Generate a chat response using GPT-4o., Generate text embeddings for semantic search.

### Community 4 - "Community 4"
Cohesion: 0.67
Nodes (3): check_phrases(), main(), Check all required phrases exist in their target files.      Returns a list of r

### Community 5 - "Community 5"
Cohesion: 0.67
Nodes (3): find_nulls(), main(), Recursively find null values, returning their paths.

### Community 6 - "Community 6"
Cohesion: 0.67
Nodes (3): has_bigquery(), main(), Check if any BigQuery resources exist in the design.

## Knowledge Gaps
- **17 isolated node(s):** `Check all required phrases exist in their target files.      Returns a list of r`, `Load invariant definitions for the given fixture.      Looks for fixture-specifi`, `Assert a file exists in the migration directory.`, `Assert file(s) do NOT exist in the migration directory.`, `Assert patterns are NOT present in a file.` (+12 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What connects `Check all required phrases exist in their target files.      Returns a list of r`, `Load invariant definitions for the given fixture.      Looks for fixture-specifi`, `Assert a file exists in the migration directory.` to the rest of the system?**
  _17 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.09 - nodes in this community are weakly interconnected._