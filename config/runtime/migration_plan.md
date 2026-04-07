# Migration, Backfill, and Rollback Plan

## Scope

This document describes how to migrate from the current legacy state model to the shard-based layout defined in:

- `config/runtime/state_layout.yaml`
- `config/runtime/state_schemas.yaml`

This milestone is design-only. It does not perform cutover, full historical backfill, or dual-write.

## Legacy Inputs

Primary legacy inputs:

- `./.state/dedupe.json`
- `./.state/delivery-log.json`
- `./.state/raw/*.json`
- `./.state/articles/YYYY-MM/*.md`
- `./digests/*`

Legacy inputs remain read-only during migration and rollback preparation.

## Synthetic Naming for Backfilled Runs

When a legacy run must be represented as a shard-era `run_manifest`, use:

- `legacy_<mode>__<YYYYMMDDTHHMMSSZ>__<scope>`

Rules:

- preserve the original legacy `run_id` in `notes` or `legacy_run_id`;
- keep synthetic manifests additive under `./.state/runs/*`;
- never rewrite legacy `run_id` values inside `delivery-log.json`.

## Minimal Working Backfill

### 1. `story_brief`

Required legacy inputs:

- `./.state/dedupe.json`

Optional legacy inputs:

- `./.state/articles/YYYY-MM/*.md`
- `./.state/delivery-log.json`
- `./.state/raw/enriched-*.json`

Minimum algorithm:

1. Iterate `dedupe.json -> seen`.
2. Group records by existing `story_id`.
3. If a record has no `story_id`, create a synthetic one from legacy title hash or canonical URL slug. Prefix: `legacy_story_`.
4. Use the URL key as `canonical_url`.
5. Use `title` as `title_snapshot`.
6. Use `first_seen` when present; otherwise fall back to `published`.
7. Compute `last_seen` as the latest available `published` or `digest_date` within the grouped entries.
8. Derive `first_seen_month` from `first_seen`.
9. Fill `companies`, `topic_tags`, `event_types_seen`, `latest_priority_score` from legacy enriched fields when available.
10. Recover `source_ids` in this priority order:
    - article frontmatter from `article_file` if available;
    - known source mapping from legacy raw exports;
    - URL-domain inference as last fallback.

Minimum working guarantee:

- one `story_brief` file per grouped `story_id`;
- enough data for anti-repeat and compact context lookup;
- no dependency on `dedupe.json` after shard file is written.

### 2. `daily_brief`

Required legacy inputs:

- `./.state/delivery-log.json`
- daily digest markdown file referenced by `digest_file`
- `./.state/dedupe.json`

Optional legacy inputs:

- `./.state/raw/enriched-*.json`
- `./.state/articles/YYYY-MM/*.md`

Minimum algorithm:

1. Select legacy runs from `delivery-log.json` where `digest_file` ends with `-daily.md`.
2. Derive `digest_date` from the digest filename.
3. Map `schedule` to delivery profile using runtime config:
   - `weekday_digest -> telegram_digest`
   - `manual + daily digest file -> telegram_digest`
4. Create synthetic `run_manifest` for the legacy digest run when one does not already exist in shard layout.
5. Resolve `story_ids` from `run.articles[*].url` via `dedupe.json`.
6. If a URL is absent in `dedupe.json`, synthesize `legacy_story_*` from the article title or URL slug.
7. Store `markdown_path` as the original legacy digest file path.
8. Backfill `top_story_ids` and `weak_signal_ids` only when they can be recovered from digest structure or enriched raw export; otherwise leave them empty.

Minimum working guarantee:

- `daily_brief` exists with `digest_date`, `delivery_profile`, `story_ids`, and `markdown_path`;
- weekly synthesis can use the brief even if section-level detail is partial.

### 3. `weekly_brief`

Required legacy inputs:

- weekly digest markdown file in `./digests/*weekly-digest.md`
- backfilled `daily_brief` files for the same ISO week

Optional legacy inputs:

- `./.state/dedupe.json`
- `./.state/delivery-log.json`
- `./.state/raw/enriched-*.json`

Minimum algorithm:

1. Discover weekly digest files by filename pattern `YYYY-Www-weekly-digest.md`.
2. Derive `week_id` from the filename.
3. Backfill `daily_brief` files for all daily digest files within the same ISO week first.
4. Set `story_ids` as the union of `story_ids` from those daily briefs.
5. Create synthetic `run_manifest` for the weekly digest if no legacy run exists in `delivery-log.json`.
6. Store `markdown_path` as the weekly digest path.
7. Backfill `trend_ids`, `prior_week_refs`, and `synthesis_notes` only when they can be extracted reliably; otherwise keep them empty.

Minimum working guarantee:

- `weekly_brief` exists even when weekly run metadata is missing in `delivery-log.json`;
- weekly consumers can use compact week-level references without reading the full archive.

## Required vs Optional Backfill Data

Required for minimum viable migration:

- `dedupe.json -> seen`
- `delivery-log.json -> runs` for daily digests
- daily digest markdown files
- weekly digest markdown files
- runtime config mapping for schedules and delivery profiles

Optional enrichments:

- article frontmatter from `./.state/articles/*`
- enriched raw exports for section reconstruction or score recovery
- manual reconciliation of ambiguous story matches
- older digest windows outside the initial migration window

## Recommended Migration Window

Required initial window:

- latest 30-45 days of daily digests
- latest 2-4 weekly digests
- all matching `dedupe.json` entries referenced by those digests

Optional later window:

- older daily digests
- older weekly digests
- deeper story history beyond the immediate anti-repeat horizon

## Sample Migration Walkthrough

Use the real fixture cases in:

- `config/runtime/migration-fixtures/recent_runs.yaml`

Interpretation:

- the daily case proves `delivery-log -> daily_brief + run_manifest + story_brief references`;
- the weekly case proves `weekly digest markdown + backfilled daily_briefs -> weekly_brief`.

## Rollback Contract

Rollback is reader-side only. Migration writes are additive and must not destroy legacy state.

Rules:

1. Do not delete or rewrite:
   - `./.state/dedupe.json`
   - `./.state/delivery-log.json`
   - legacy raw exports
   - legacy digest markdown files
2. Write migrated artifacts only to shard-era paths under:
   - `./.state/runs/`
   - `./.state/stories/`
   - `./.state/briefs/`
3. If shard readers fail, rollback by switching consumers back to legacy inputs.
4. Keep shard artifacts as audit trail even during rollback.
5. Do not require re-backfill before resuming legacy flow.

Rollback outcome:

- legacy flow can resume immediately;
- new shard artifacts remain available for inspection or future retry;
- no migrated data is lost because rollback does not delete additive files.

## Rollback Rehearsal Checklist

Use:

- `config/runtime/migration-fixtures/rollback_checklist.yaml`

Required rehearsal outcome:

- legacy files remain unchanged;
- shard-era files are ignored safely by legacy readers;
- rollback requires only configuration/reader switching, not destructive cleanup.
