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
- `change_request` (follow-up escalation artifact; schema in `config/runtime/change_request_schema.yaml`, state path in `config/runtime/state_layout.yaml`)

Contract rules:

- each mode consumes only the artifacts explicitly listed in its mode prompt;
- full article body is a special intermediate artifact and must not become a default downstream input;
- each mode should emit at least one structured output plus a `run_manifest`;
- detailed field-by-field schemas live in `config/runtime/state_schemas.yaml`;
- shard naming and lookup rules live in `config/runtime/state_layout.yaml`.
- follow-up escalation artifacts must use the policy in `cowork/shared/change_request_policy.md`;
- when an external runner cannot proceed without a persistent repo change, it should emit a `change_request` rather than mutate source-of-truth files.
- `run_manifest.status` keeps the stable enum `pending | running | completed | failed | partial`; use `run_manifest.operator_report` for stage-specific weekday run semantics.

If a mode cannot complete using its declared inputs, that is a contract problem and should be surfaced explicitly.

## Operator report contract

Weekday run reports must not collapse mixed outcomes into a single success label.
The final report should include separate fields for:

- `source_discovery`
- `enrichment`
- `digest_generation`
- `qa_review`
- `telegram_delivery`

Stage fields should use compact state such as `canonical_source_complete`,
`evidence_completeness`, `digest_status`, `validated`, and `delivered` where
applicable. A mode-level `status: completed` means that mode emitted its own
artifact; it does not mean the end-to-end weekday run is production-clean.

If source discovery or enrichment is `partial` but `build_daily_digest` still
emits files, the digest may be reported as generated, but the operator report
must mark `digest_generation.digest_status` as `partial_digest` or
`non_canonical_digest` and include a warning that the run is not production-clean.

## Delivery contracts

Telegram delivery format rules (parse_mode, GFM-to-HTML mapping, operator content strip rules)
are documented in `cowork/adapters/telegram_format.md`.

Digest file write rule: always use full overwrite (`Write`), never `Edit`.
See `cowork/modes/build_daily_digest.md` → "Delivery constraints" for details.
