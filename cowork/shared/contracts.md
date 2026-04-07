# Shared Contracts Overview

Runtime modes should exchange compact structured artifacts rather than large docs or free-form context.

Canonical artifact names:

- `raw_candidate`
- `shortlisted_item`
- `enriched_item`
- `story_brief`
- `daily_brief`
- `weekly_brief`
- `run_manifest`

Contract rules:

- each mode consumes only the artifacts explicitly listed in its mode prompt;
- full article body is a special intermediate artifact and must not become a default downstream input;
- each mode should emit at least one structured output plus a `run_manifest`;
- detailed field-by-field schemas live in `config/runtime/state_schemas.yaml`;
- shard naming and lookup rules live in `config/runtime/state_layout.yaml`.

If a mode cannot complete using its declared inputs, that is a contract problem and should be surfaced explicitly.
