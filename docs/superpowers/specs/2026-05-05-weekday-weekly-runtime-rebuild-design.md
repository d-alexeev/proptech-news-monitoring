# Weekday/Weekly Runtime Rebuild Design

Date: 2026-05-05
Branch: `codex/refactor-plan-weekday-weekly-cleanup`

## Goal

Rebuild this repository as a compact runtime package for two supported server
jobs only:

- weekday daily digest
- weekly digest

The current repository is treated as a prototype and migration source. The
target repository should keep the proven launch and safety concepts, but remove
legacy modes, historical run artifacts, benchmark work, broad compatibility
layers, and old development scaffolding.

## Non-Goals

- Preserve backward compatibility with old `cowork/`, `config/runtime/`,
  `ops/codex-cli/`, or legacy digest paths.
- Keep `breaking_alert`, `stakeholder_fanout`, stakeholder profiles, or their
  fixtures.
- Keep the benchmark suite or old prompt layer.
- Keep the historical digest archive in tracked git.
- Change the operator goal: the monitor remains focused on market signals that
  matter for Avito Real Estate.

## Target Structure

```text
proptech-monitor/
├── AGENTS.md
├── README.md
├── .env.example
├── runtime/
│   ├── manifest.yaml
│   ├── schedules.yaml
│   ├── sources/
│   │   ├── weekday.yaml
│   │   └── weekly.yaml
│   ├── judgment/
│   │   ├── industry_filter.yaml
│   │   ├── discovery_rules.yaml
│   │   └── scoring_profile.yaml
│   ├── prompts/
│   │   ├── shared.md
│   │   ├── weekday_discovery.md
│   │   ├── weekday_finish.md
│   │   └── weekly_digest.md
│   ├── adapters/
│   └── schemas/
│       ├── artifacts.yaml
│       └── state_layout.yaml
├── runner/
│   ├── run.sh
│   ├── tools/
│   │   ├── fetch_sources.py
│   │   ├── fetch_articles.py
│   │   ├── materialize_digest.py
│   │   ├── send_telegram.py
│   │   └── validate_runtime.py
│   └── tests/
├── samples/
│   ├── weekday-digest.md
│   ├── weekly-digest.md
│   └── run-report.json
└── docs/
    ├── operations.md
    └── design.md
```

## Runtime Entry Points

Server launch remains a first-class requirement:

```bash
runner/run.sh weekday
runner/run.sh weekly
```

The runner must support cron/systemd operation, lock concurrent runs, load a
restricted `.env`, write local run logs under `.state/`, preserve delivery
evidence, and provide self-tests:

```bash
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
```

## Judgment Layer

The rebuild uses four logical filtering stages represented by three editable
judgment files.

```text
runtime/judgment/
├── industry_filter.yaml
├── discovery_rules.yaml
└── scoring_profile.yaml
```

### Level 0: Source Scope

`runtime/sources/weekday.yaml` and `runtime/sources/weekly.yaml` define which
sources are monitored. Sources outside these files are not part of runtime.

### Level 1: Industry Filter

`industry_filter.yaml` answers whether an item belongs to the configured
industry before any scoring. The initial profile is `real_estate_marketplaces`,
but the file should be editable enough to retarget the agent to another industry
later.

For broad sources such as AIM Group, this gate must prevent generic marketplace,
automotive, jobs, travel, ecommerce, retail media, or payments items from
entering the shortlist unless there is direct real estate marketplace relevance.

Rejected items do not receive a high score later. They leave discovery with a
rejection reason such as `reject_not_industry`.

### Level 2: Discovery Shortlist

`discovery_rules.yaml` answers whether an industry-relevant item is worth
fetching in full text. Discovery uses only titles, snippets, listing metadata,
source metadata, URL markers, and adapter notes. It does not assign the final
priority score.

Expected outputs include:

- `triage_decision`: `shortlist`, `reject`, or `maybe_weekly`
- `provisional_priority`: `high`, `medium`, or `low`
- `industry_filter.status`
- matched topics and compact evidence
- `shortlist_reason`

The weekday shortlist should remain bounded so article fetching does not grow
without operator intent.

### Level 3: Full-Text Scoring

`scoring_profile.yaml` defines the score after article prefetch and enrichment.
The scoring profile includes a detailed `strategic_relevance` dimension for
Avito Real Estate.

Initial dimensions:

- strategic relevance
- market impact
- novelty
- evidence quality
- urgency

Strategic relevance should score highest when a story affects real estate
marketplace monetization, lead generation or lead quality, agent/developer/seller
tooling, AI/search/listing discovery, buyer or renter journey, or competitive
advantage for relevant portals such as Zillow, Rightmove, REA, CoStar, and
similar companies.

### Level 4: Digest Selection

Digest selection bands also live in `scoring_profile.yaml`. A typical policy:

- `90-100`: must cover if evidence is valid
- `75-89`: strong daily candidate
- `60-74`: weekly/context candidate, not usually a daily top story
- below `60`: reject or log only

Items without full text can continue as `snippet_fallback`, but their maximum
score should be capped so weak evidence cannot look production-clean.

## Runtime Flow

### Weekday

```text
cron/systemd
  -> runner/run.sh weekday
      -> fetch_sources.py
      -> Codex discovery prompt
          -> applies industry_filter.yaml
          -> applies discovery_rules.yaml
          -> emits raw + shortlist
      -> fetch_articles.py
          -> fetches full text only for shortlisted URLs
          -> writes .state/articles/ and article prefetch manifest
      -> Codex finish prompt
          -> reads shortlist + article manifest
          -> may read full text only for matching shortlisted URLs
          -> applies scoring_profile.yaml
          -> emits finish draft
      -> materialize_digest.py
      -> send_telegram.py
      -> validate_runtime.py / run report
```

### Weekly

```text
cron/systemd
  -> runner/run.sh weekly
      -> reads compact daily briefs from current week
      -> optionally fetches configured weekly context sources
      -> applies industry/discovery/scoring rules where new weekly context exists
      -> renders weekly digest from compact artifacts
      -> send_telegram.py
      -> validate_runtime.py / run report
```

Weekly should primarily synthesize compact daily briefs. It must not depend on
the historical markdown digest archive or broad full-text article state.

## Full-Text Boundary

Full article text appears only in `runner/tools/fetch_articles.py`, after
discovery has written a shortlist.

Contract:

- input: current-run shortlist
- output: article prefetch manifest
- allowed writes: `.state/articles/`
- forbidden: fetching URLs not present in the current shortlist
- forbidden: using article bodies in discovery
- forbidden: letting digest or weekly modes read article bodies directly

Finish/enrichment may read full text only when a manifest entry matches a
current-run shortlisted URL or canonical URL.

## Error Handling

- Source fetch partial: continue only with `source_status: partial` in the run
  report.
- Industry filter uncertainty: reject from daily shortlist; optionally mark
  `maybe_weekly` when the source and context justify review.
- No shortlist: write an explicit run report; do not fake a clean digest.
- Article fetch failed: allow `snippet_fallback`, but cap score and surface the
  evidence limit.
- All selected items snippet-only: generated digest must be `partial_digest`.
- Telegram not configured: preserve digest and report `not_configured`.
- Telegram failed: retry, then report `delivery_failed_*`.
- Invalid finish draft: materialization fails and Telegram is not called.

## Validation

Required checks for the rebuilt repo:

```bash
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
python3 runner/tools/validate_runtime.py --check config
python3 runner/tools/validate_runtime.py --check schemas
python3 runner/tools/validate_runtime.py --check samples
python3 -m pytest runner/tests
```

Validation must verify:

- schedules contain only weekday and weekly jobs;
- all sources resolve to an adapter or explicit `none`;
- judgment YAML files contain required sections;
- prompts reference new `runtime/judgment/` files, not old paths;
- full-text fields are forbidden outside article fetch and enrichment contracts;
- samples match expected digest/report shape;
- server wrapper self-test resolves all required paths.

## Keep, Rewrite, Remove

### Keep or Rewrite Into New Structure

- current weekday and weekly launch behavior;
- Telegram daily and weekly delivery profiles;
- source discovery prefetch behavior;
- article prefetch after shortlist;
- deterministic materialization;
- Russian daily digest requirements;
- compact daily and weekly brief contracts;
- source adapter knowledge needed by retained sources;
- 1-2 curated sample artifacts.

### Remove From Target Runtime

- `benchmark/`
- legacy `prompts/`
- `breaking_alert`
- `stakeholder_fanout`
- stakeholder profiles
- old migration and compatibility fixtures
- historical `digests/` archive except curated samples
- old plans, audits, and run reviews except what becomes current docs
- tracked `.auto-memory/`
- old `cowork/`, `config/runtime/`, `ops/codex-cli/`, and root `tools/` after
  the new `runtime/` and `runner/` paths are verified

## Milestones

1. Spec and inventory: map keep/remove/rename decisions, runtime contracts, and
   acceptance criteria. No runtime deletions.
2. Scaffold new structure: add `runtime/`, `runner/`, `samples/`, and new docs
   while old files remain.
3. Judgment layer: add industry, discovery, and scoring configs; update prompts
   to use them.
4. Runner simplification: implement `runner/run.sh weekday|weekly`, remove
   `breaking_alert` from launch surface, and preserve server self-tests.
5. Validation and samples: migrate tests, add curated samples, and verify
   sample shape.
6. Remove legacy: delete old benchmark, prompt, mode, config, doc, digest, and
   memory artifacts once new checks cover the target runtime.
7. Completion audit: compare original requirements to implemented state and
   document any migration caveats.

## Coverage Matrix

| Requirement | Covered By |
| --- | --- |
| Keep only what is needed for Weekday and Weekly Digest | Target structure, Runtime Entry Points, Remove list |
| Preserve server/cron launch | Runtime Entry Points, Runtime Flow, Validation |
| Use current repo as prototype but rebuild cleanly | Goal, Keep/Rewrite, Milestones |
| Remove legacy previous runs and development artifacts | Remove list, Milestone 6 |
| Keep one or two examples | Target Structure, Keep/Rewrite, Validation |
| Make industry filters configurable | Judgment Layer Level 1 |
| Add shortlist rules before full text | Judgment Layer Level 2 |
| Include precise strategic relevance in scoring | Judgment Layer Level 3 |
| Clarify when full text appears | Full-Text Boundary, Runtime Flow |
| Keep repo reviewable and safe | Milestones, Validation, Completion audit |

## Acceptance Criteria

- `runtime/schedules.yaml` defines only weekday and weekly.
- `runner/run.sh weekday` and `runner/run.sh weekly` exist.
- Server self-tests pass for both schedules.
- `runtime/judgment/industry_filter.yaml`,
  `runtime/judgment/discovery_rules.yaml`, and
  `runtime/judgment/scoring_profile.yaml` exist and are referenced by prompts.
- Discovery cannot shortlist an item that fails the industry filter.
- Full text is fetched only after shortlist and only for shortlisted URLs.
- Finish/enrichment can read full text only through the current-run article
  manifest.
- Weekly digest reads compact daily/weekly artifacts, not the historical digest
  archive.
- Telegram delivery works for daily and weekly profiles or reports explicit
  not-configured/failure status.
- Tracked repo contains curated samples but no large historical digest archive.
- Removed legacy surfaces are not referenced by new docs, prompts, runner, or
  manifest.

