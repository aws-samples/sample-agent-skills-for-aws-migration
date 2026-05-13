# Graph Report - sample-agent-skills-for-aws-migration  (2026-05-06)

## Corpus Check
- 37 files · ~199,864 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 116 nodes · 146 edges · 36 communities (35 shown, 1 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b856898d`
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
- [[_COMMUNITY_Community 7|Community 7]]

## God Nodes (most connected - your core abstractions)
1. `main()` - 45 edges
2. `validateMarketplace()` - 10 edges
3. `readJson()` - 8 edges
4. `addError()` - 6 edges
5. `validatePluginJson()` - 5 edges
6. `validateMcpJson()` - 5 edges
7. `main()` - 5 edges
8. `check_phrases()` - 4 edges
9. `run_check()` - 4 edges
10. `find_nulls()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `check_phrases()` --calls--> `main()`  [EXTRACTED]
  tools/eval_check_phrases.py → tools/eval_check.py
- `addError()` --calls--> `validateMarketplace()`  [EXTRACTED]
  tools/validate-manifests.mjs → tools/validate-cross-refs.mjs
- `readJson()` --calls--> `main()`  [EXTRACTED]
  tools/validate-manifests.mjs → tools/eval_check.py
- `readJson()` --calls--> `validateMarketplace()`  [EXTRACTED]
  tools/validate-manifests.mjs → tools/validate-cross-refs.mjs
- `findFiles()` --calls--> `main()`  [EXTRACTED]
  tools/validate-manifests.mjs → tools/eval_check.py

## Communities (36 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (22): check_content_absent(), check_content_present(), check_cross_file_join(), check_custom(), check_file_absent(), check_file_exists(), check_json_every(), check_json_path_value() (+14 more)

### Community 1 - "Community 1"
Cohesion: 0.46
Nodes (7): addError(), addWarning(), isSafeRelativePath(), main(), pathExists(), readJson(), validateMarketplace()

### Community 2 - "Community 2"
Cohesion: 0.71
Nodes (6): addError(), findFiles(), main(), readJson(), validateMcpJson(), validatePluginJson()

### Community 3 - "Community 3"
Cohesion: 0.33
Nodes (5): generate_response(), get_embedding(), Chatbot API — uses OpenAI SDK for text generation and embeddings., Generate a chat response using GPT-4o., Generate text embeddings for semantic search.

### Community 5 - "Community 5"
Cohesion: 0.67
Nodes (3): check_phrases(), main(), Check all required phrases exist in their target files.      Returns a list of r

### Community 6 - "Community 6"
Cohesion: 0.67
Nodes (3): find_nulls(), main(), Recursively find null values, returning their paths.

### Community 7 - "Community 7"
Cohesion: 0.67
Nodes (3): has_bigquery(), main(), Check if any BigQuery resources exist in the design.

## Knowledge Gaps
- **17 isolated node(s):** `Check all required phrases exist in their target files.      Returns a list of r`, `Load invariant definitions for the given fixture.      Looks for fixture-specifi`, `Assert a file exists in the migration directory.`, `Assert file(s) do NOT exist in the migration directory.`, `Assert patterns are NOT present in a file.` (+12 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 13`, `Community 14`, `Community 15`, `Community 16`, `Community 17`, `Community 18`, `Community 19`, `Community 20`, `Community 21`, `Community 22`, `Community 23`, `Community 24`, `Community 25`, `Community 26`, `Community 27`, `Community 28`, `Community 29`, `Community 30`, `Community 31`, `Community 32`, `Community 33`, `Community 34`?**
  _High betweenness centrality (0.823) - this node is a cross-community bridge._
- **Why does `validateMarketplace()` connect `Community 1` to `Community 2`, `Community 4`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `run_check()` connect `Community 0` to `Community 4`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **What connects `Check all required phrases exist in their target files.      Returns a list of r`, `Load invariant definitions for the given fixture.      Looks for fixture-specifi`, `Assert a file exists in the migration directory.` to the rest of the system?**
  _17 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.09 - nodes in this community are weakly interconnected._