# Legacy Compatibility Bridge

## Purpose

This bridge keeps `./.state/dedupe.json` and `./.state/delivery-log.json` available
for temporary legacy readers while the shard-based runtime becomes canonical.

## Rules

- Legacy files are export targets only.
- Canonical data comes from shard artifacts under `./.state/runs/`,
  `./.state/enriched/`, `./.state/stories/`, `./.state/briefs/daily/`, and
  `./.state/briefs/weekly/`.
- No runtime mode may depend on legacy files to produce shard artifacts.
- Export is additive and must not delete shard artifacts or make old files part
  of the critical path again.

## Supported Compatibility Scope

- Daily windows can be exported to legacy `dedupe.json` and `delivery-log.json`.
- Weekly windows can be exported to legacy `dedupe.json` and `delivery-log.json`.
- Legacy readers that only require top-level structure and core fields remain
  supportable during the transition.

## Explicit Limitations

- Historical parity is not guaranteed across the full archive.
- `sources_used` may be derived from shard-era `source_groups` or `source_ids`,
  not necessarily from legacy fetch-engine labels.
- Optional legacy fields that are not present in shard artifacts may be omitted
  or synthesized conservatively.
- Weekly-only export may derive `digest_date` from the target ISO week when no
  daily digest date exists for the same story.
- Legacy files remain snapshots for compatibility, not the authoritative store.

## Temporary Reader Guidance

- Existing readers of `dedupe.json` and `delivery-log.json` may continue
  temporarily.
- New work should read shard artifacts directly.
- Any reader that needs richer context than the legacy files provide should be
  migrated to `daily_brief`, `weekly_brief`, `story_brief`, or `run_manifest`.
