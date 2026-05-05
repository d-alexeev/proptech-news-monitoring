# Weekday Weekly Runtime Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the repository into a compact runtime package that supports only the weekday daily digest and weekly digest through server/cron launch.

**Architecture:** Create a new `runtime/` source-of-truth and `runner/` execution layer beside the existing files, validate the new layer, then remove the legacy layer after parity checks pass. The runtime judgment model is explicit: source scope, industry filter, discovery shortlist rules, full-text scoring, and digest selection bands. Full text is fetched only after shortlist through `runner/tools/fetch_articles.py`.

**Tech Stack:** Bash, Python 3.11+, PyYAML, requests, feedparser, python-dateutil, pypdf, Playwright, pytest, Codex CLI, Telegram Bot API.

---

## Scope Check

The spec touches config, prompts, source adapters, runner orchestration, helper scripts, samples, docs, and legacy cleanup. It remains one plan because each subsystem is required for one testable product: `runner/run.sh weekday` and `runner/run.sh weekly`. Work is split into checkpoint tasks so each commit leaves either the old runtime untouched or the new runtime independently testable.

## File Structure Map

### New Runtime Files

- `runtime/manifest.yaml`: canonical index of runtime files, checks, and supported jobs.
- `runtime/schedules.yaml`: only weekday and weekly schedules plus Telegram delivery profiles.
- `runtime/sources/weekday.yaml`: weekday source universe migrated from current `daily_core`.
- `runtime/sources/weekly.yaml`: weekly context source universe migrated from current `weekly_context`.
- `runtime/judgment/industry_filter.yaml`: Level 1 industry gate before scoring.
- `runtime/judgment/discovery_rules.yaml`: Level 2 shortlist rules before article full text.
- `runtime/judgment/scoring_profile.yaml`: Level 3 full-text scoring and Level 4 digest selection.
- `runtime/prompts/shared.md`: compact shared runtime brief.
- `runtime/prompts/weekday_discovery.md`: Codex discovery prompt for weekday Stage A.
- `runtime/prompts/weekday_finish.md`: Codex enrichment/daily digest prompt for weekday Stage C.
- `runtime/prompts/weekly_digest.md`: Codex weekly synthesis prompt.
- `runtime/adapters/source_map.yaml`: source-to-adapter mapping for retained sources.
- `runtime/adapters/*.md`: retained source-specific adapter notes, copied and path-adjusted from `cowork/adapters/`.
- `runtime/schemas/artifacts.yaml`: compact artifact contracts for raw, shortlist, article prefetch, finish draft, daily brief, weekly brief, and run report.
- `runtime/schemas/state_layout.yaml`: compact `.state/` layout.

### New Runner Files

- `runner/run.sh`: server/cron entrypoint for `weekday`, `weekly`, and self-tests.
- `runner/tools/common.py`: shared path, JSON, YAML, datetime, and env helpers.
- `runner/tools/fetch_sources.py`: source prefetch helper for configured sources.
- `runner/tools/fetch_articles.py`: article/full-text helper for current-run shortlisted URLs only.
- `runner/tools/materialize_digest.py`: deterministic materializer for finish drafts.
- `runner/tools/send_telegram.py`: Telegram sender and delivery report writer.
- `runner/tools/validate_runtime.py`: offline validation gate for config, schemas, prompts, samples, and full-text boundaries.
- `runner/requirements.txt`: runtime and test dependencies.
- `runner/tests/*.py`: direct tests for each runner component.

### New Sample and Docs Files

- `samples/weekday-digest.md`: curated weekday example copied from a recent successful digest and scrubbed if needed.
- `samples/weekly-digest.md`: curated weekly example copied from an existing weekly digest and scrubbed if needed.
- `samples/run-report.json`: compact sample run report for validation.
- `docs/operations.md`: setup, `.env`, cron/systemd, manual runs, validation, full-text boundary, troubleshooting, and server recovery notes.
- `docs/design.md`: concise human-facing rebuild design copied from the approved spec.
- `README.md`: compact repository entry point for operators.
- `AGENTS.md`: compact contributor/runtime safety rules for future Codex work.
- `COMPLETION_AUDIT.md`: final comparison after legacy removal.

## Documentation Requirements

Documentation is a required deliverable, not cleanup after implementation. The
rebuild is not complete until these docs exist and pass validation:

- `README.md` explains the repository purpose, the two supported jobs, and the
  canonical runtime entry points.
- `docs/operations.md` explains setup, `.env`, dependency installation,
  self-tests, manual runs, cron/systemd, Telegram delivery states, full-text
  boundaries, and troubleshooting.
- `docs/design.md` preserves the approved design in the new compact docs set.
- `AGENTS.md` explains the new repo rules, behavior-change policy, validation
  expectations, and full-text safety boundary.
- `COMPLETION_AUDIT.md` compares original requirements, implemented behavior,
  partial items, missing items, and compatibility caveats.
- `runner/tools/validate_runtime.py --check all` must verify that the required
  docs exist and do not reference removed runtime paths.

### Legacy Files Removed Only After New Checks Pass

- `benchmark/`
- `prompts/`
- `cowork/`
- `config/runtime/`
- `ops/codex-cli/`
- root `tools/`
- tracked `.auto-memory/`
- historical `digests/` archive after selected samples are copied
- old `docs/plans/`, old run reviews, and old audit docs that are not current operations docs

---

### Task 1: Register the Active Rebuild Plan

**Files:**
- Modify: `PLANS.md`
- Verify: `docs/superpowers/specs/2026-05-05-weekday-weekly-runtime-rebuild-design.md`
- Verify: `docs/superpowers/plans/2026-05-05-weekday-weekly-runtime-rebuild.md`

- [ ] **Step 1: Verify branch and clean worktree**

Run:

```bash
git branch --show-current
git status --short
```

Expected:

```text
codex/refactor-plan-weekday-weekly-cleanup
```

`git status --short` should be empty before editing.

- [ ] **Step 2: Add this plan to the active plan index**

Edit `PLANS.md` and add this row to the Active Plan table:

```md
| Weekday Weekly Runtime Rebuild | planned | `docs/superpowers/plans/2026-05-05-weekday-weekly-runtime-rebuild.md` | Hard rebuild of the repository into a compact `runtime/` + `runner/` package that supports only weekday and weekly digest server jobs. |
```

- [ ] **Step 3: Verify the index mentions the new plan once**

Run:

```bash
rg -n "Weekday Weekly Runtime Rebuild" PLANS.md
```

Expected: exactly one matching row.

- [ ] **Step 4: Commit the plan registration**

Run:

```bash
git add PLANS.md docs/superpowers/plans/2026-05-05-weekday-weekly-runtime-rebuild.md
git commit -m "Add weekday weekly runtime rebuild plan"
```

Expected: commit succeeds with only planning files changed.

---

### Task 2: Create Runtime Config and Judgment Layer

**Files:**
- Create: `runtime/manifest.yaml`
- Create: `runtime/schedules.yaml`
- Create: `runtime/sources/weekday.yaml`
- Create: `runtime/sources/weekly.yaml`
- Create: `runtime/judgment/industry_filter.yaml`
- Create: `runtime/judgment/discovery_rules.yaml`
- Create: `runtime/judgment/scoring_profile.yaml`
- Create: `runtime/schemas/artifacts.yaml`
- Create: `runtime/schemas/state_layout.yaml`
- Create: `runner/requirements.txt`
- Create: `runner/tests/test_runtime_config.py`

- [ ] **Step 1: Write the failing config validation test**

Create `runner/tests/test_runtime_config.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import pathlib

import yaml


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def read_yaml(relative_path: str) -> dict:
    path = REPO_ROOT / relative_path
    assert path.exists(), f"missing required file: {relative_path}"
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    assert isinstance(data, dict), f"{relative_path} must contain a YAML mapping"
    return data


def test_runtime_manifest_points_to_new_runtime_only() -> None:
    manifest = read_yaml("runtime/manifest.yaml")
    assert manifest["version"] == 1
    assert manifest["supported_jobs"] == ["weekday", "weekly"]
    serialized = yaml.safe_dump(manifest, allow_unicode=True)
    assert "cowork/" not in serialized
    assert "config/runtime/" not in serialized
    assert "ops/codex-cli/" not in serialized


def test_schedules_contain_only_weekday_and_weekly() -> None:
    schedules = read_yaml("runtime/schedules.yaml")
    jobs = schedules["jobs"]
    assert sorted(jobs) == ["weekday", "weekly"]
    assert "breaking_alert" not in jobs
    assert "stakeholder_fanout" not in jobs
    assert jobs["weekday"]["delivery_profile"] == "telegram_digest"
    assert jobs["weekly"]["delivery_profile"] == "telegram_weekly_digest"
    assert sorted(schedules["delivery_profiles"]) == ["telegram_digest", "telegram_weekly_digest"]


def test_sources_have_expected_profiles() -> None:
    weekday = read_yaml("runtime/sources/weekday.yaml")
    weekly = read_yaml("runtime/sources/weekly.yaml")
    assert weekday["source_profile"] == "weekday"
    assert weekly["source_profile"] == "weekly"
    weekday_ids = {source["id"] for source in weekday["sources"]}
    weekly_ids = {source["id"] for source in weekly["sources"]}
    assert "aim_group_real_estate_intelligence" in weekday_ids
    assert "inman_tech_innovation" in weekday_ids
    assert "zillow_ios" in weekly_ids
    assert "rightmove_android" in weekly_ids


def test_judgment_files_define_four_logical_filter_levels() -> None:
    industry = read_yaml("runtime/judgment/industry_filter.yaml")
    discovery = read_yaml("runtime/judgment/discovery_rules.yaml")
    scoring = read_yaml("runtime/judgment/scoring_profile.yaml")
    assert industry["profile_id"] == "real_estate_marketplaces"
    assert industry["rule"]["require_at_least_one_pass_topic"] is True
    assert "automotive_classifieds" in industry["reject_topics"]
    assert "competitor_product_launch" in discovery["shortlist_triggers"]["high"]
    assert discovery["limits"]["weekday_max_shortlist"] == 12
    assert "strategic_relevance" in scoring["dimensions"]
    assert scoring["digest_selection"]["bands"]["90_100"]["daily_policy"] == "must_cover"
    assert scoring["evidence_caps"]["max_score_if_no_full_text"] == 74


def test_schema_files_define_full_text_boundary() -> None:
    artifacts = read_yaml("runtime/schemas/artifacts.yaml")
    layout = read_yaml("runtime/schemas/state_layout.yaml")
    assert "article_prefetch" in artifacts["artifacts"]
    article = artifacts["artifacts"]["article_prefetch"]
    assert article["producer"] == "runner/tools/fetch_articles.py"
    assert article["input_boundary"] == "current_run_shortlist_only"
    assert layout["collections"]["articles"]["allowed_producer"] == "runner/tools/fetch_articles.py"
```

- [ ] **Step 2: Run the config test to verify it fails before files exist**

Run:

```bash
python3 -m pytest runner/tests/test_runtime_config.py -q
```

Expected: FAIL with `missing required file: runtime/manifest.yaml`.

- [ ] **Step 3: Create runner dependency file**

Create `runner/requirements.txt`:

```text
requests>=2.32,<3
feedparser>=6.0.11,<7
python-dateutil>=2.9,<3
PyYAML>=6,<7
pypdf>=4,<6
playwright>=1.59,<2
pytest>=8,<9
```

- [ ] **Step 4: Create runtime manifest**

Create `runtime/manifest.yaml`:

```yaml
version: 1
runtime_source_of_truth: true
supported_jobs:
  - weekday
  - weekly

files:
  schedules: runtime/schedules.yaml
  sources:
    weekday: runtime/sources/weekday.yaml
    weekly: runtime/sources/weekly.yaml
  judgment:
    industry_filter: runtime/judgment/industry_filter.yaml
    discovery_rules: runtime/judgment/discovery_rules.yaml
    scoring_profile: runtime/judgment/scoring_profile.yaml
  prompts:
    shared: runtime/prompts/shared.md
    weekday_discovery: runtime/prompts/weekday_discovery.md
    weekday_finish: runtime/prompts/weekday_finish.md
    weekly_digest: runtime/prompts/weekly_digest.md
  adapters:
    source_map: runtime/adapters/source_map.yaml
    directory: runtime/adapters
  schemas:
    artifacts: runtime/schemas/artifacts.yaml
    state_layout: runtime/schemas/state_layout.yaml
  runner:
    entrypoint: runner/run.sh
    tools:
      fetch_sources: runner/tools/fetch_sources.py
      fetch_articles: runner/tools/fetch_articles.py
      materialize_digest: runner/tools/materialize_digest.py
      send_telegram: runner/tools/send_telegram.py
      validate_runtime: runner/tools/validate_runtime.py

state_root: .state
sample_artifacts:
  weekday_digest: samples/weekday-digest.md
  weekly_digest: samples/weekly-digest.md
  run_report: samples/run-report.json
```

- [ ] **Step 5: Create schedules**

Create `runtime/schedules.yaml`:

```yaml
version: 1

jobs:
  weekday:
    enabled: true
    days: [MON, TUE, WED, THU, FRI]
    time: "09:00"
    source_profile: weekday
    delivery_profile: telegram_digest
  weekly:
    enabled: true
    days: [FRI]
    time: "17:00"
    source_profile: weekly
    delivery_profile: telegram_weekly_digest

delivery_profiles:
  telegram_digest:
    enabled: true
    bot_token_env: TELEGRAM_BOT_TOKEN
    chat_id_env: TELEGRAM_CHAT_ID
    message_thread_id_env: TELEGRAM_MESSAGE_THREAD_ID
    parse_mode: HTML
    disable_web_page_preview: false
    split_long_messages: true
    max_message_length: 3800
    title_template: ""
    link_preview:
      enabled: true
      url_mode: first_markdown_link
      prefer_large_media: true
      show_above_text: true
      only_first_part: true
  telegram_weekly_digest:
    enabled: true
    bot_token_env: TELEGRAM_BOT_TOKEN
    chat_id_env: TELEGRAM_CHAT_ID
    message_thread_id_env: TELEGRAM_MESSAGE_THREAD_ID
    parse_mode: HTML
    disable_web_page_preview: true
    split_long_messages: true
    max_message_length: 3800
    title_template: "PropTech Weekly | {date}"
```

- [ ] **Step 6: Create source profile files by migrating current source groups**

Run:

```bash
mkdir -p runtime/sources
cp config/runtime/source-groups/daily_core.yaml runtime/sources/weekday.yaml
cp config/runtime/source-groups/weekly_context.yaml runtime/sources/weekly.yaml
```

Then edit the first metadata block in `runtime/sources/weekday.yaml` to:

```yaml
source_profile: weekday
description: "High-signal weekday monitoring for real estate marketplace moves"
lookback_hours: 36
max_items_per_source: 8
```

Edit the first metadata block in `runtime/sources/weekly.yaml` to:

```yaml
source_profile: weekly
description: "Weekly context monitoring for weaker real estate marketplace signals"
lookback_hours: 168
max_items_per_source: 6
```

Keep the existing `sources:` arrays from the copied files.

- [ ] **Step 7: Create industry filter**

Create `runtime/judgment/industry_filter.yaml`:

```yaml
profile_id: real_estate_marketplaces
description: "Eligibility gate for real estate marketplace and proptech signals before scoring."

pass_topics:
  - property_portals
  - residential_real_estate
  - rentals
  - new_developments
  - mortgage_journey
  - agent_broker_tools
  - listing_quality
  - lead_quality
  - home_search
  - valuation
  - proptech_infrastructure
  - marketplace_monetization_with_property_angle

reject_topics:
  - automotive_classifieds
  - jobs_classifieds
  - travel
  - general_ecommerce
  - retail_media_without_property_angle
  - payments_without_property_angle
  - logistics_without_property_angle
  - horizontal_marketplace_without_property_angle

rule:
  require_at_least_one_pass_topic: true
  reject_if_only_reject_topics: true
  uncertain_policy: reject_from_daily_allow_weekly_review
  evidence_required:
    - title
    - snippet_or_listing_metadata

broad_source_overrides:
  aim_group_real_estate_intelligence:
    required_markers:
      - real estate
      - property
      - housing
      - homes
      - rentals
      - agent
      - broker
      - portal
      - listings
      - mortgage
    reject_sections:
      - automotive
      - recruitment
      - general classifieds
      - marketplace news without property angle
```

- [ ] **Step 8: Create discovery rules**

Create `runtime/judgment/discovery_rules.yaml`:

```yaml
version: 1
purpose: "Decide whether an industry-relevant item is worth current-run full-text fetch."

allowed_inputs:
  - title
  - snippet
  - listing_metadata
  - source_metadata
  - url_markers
  - adapter_notes

forbidden_inputs:
  - full_article_text
  - article_file
  - historical_digest_archive

shortlist_triggers:
  high:
    - competitor_product_launch
    - marketplace_monetization_change
    - portal_traffic_or_share_shift
    - agent_or_developer_tooling
    - buyer_or_renter_search_experience
    - listing_quality_or_fraud_signal
    - regulatory_or_platform_policy_change
  medium:
    - market_data_with_platform_implication
    - funding_or_ma_for_relevant_proptech
    - app_store_update_with_relevant_feature
    - expert_analysis_on_portal_strategy
  reject:
    - generic_housing_price_report_without_platform_angle
    - corporate_award_or_event_promo
    - executive_quote_without_action
    - non_real_estate_vertical
    - duplicate_or_minor_followup

triage_decisions:
  shortlist: "Fetch full text in runner/tools/fetch_articles.py."
  maybe_weekly: "Do not fetch for weekday unless weekly context rules request it."
  reject: "Do not fetch full text."

limits:
  weekday_max_shortlist: 12
  weekly_context_max_shortlist: 12
```

- [ ] **Step 9: Create scoring profile**

Create `runtime/judgment/scoring_profile.yaml`:

```yaml
version: 1
profile_id: avito_real_estate_strategy
score_range: [0, 100]

dimensions:
  strategic_relevance:
    weight: 30
    high:
      - affects_real_estate_marketplace_monetization
      - changes_lead_generation_or_lead_quality
      - shifts_agent_developer_or_seller_tooling
      - impacts_search_recommendations_ai_assistants_or_listing_discovery
      - changes_buyer_or_renter_transaction_journey
      - creates_competitor_advantage_for_relevant_portals
    medium:
      - adjacent_proptech_behavior_with_possible_transfer
      - regional_market_pattern_with_possible_transfer
      - product_experiment_without_clear_commercial_impact
    low:
      - generic_company_pr
      - local_housing_data_without_marketplace_implication
      - funding_or_hiring_news_without_product_or_business_signal
  market_impact:
    weight: 25
  novelty:
    weight: 15
  evidence_quality:
    weight: 15
  urgency:
    weight: 15

evidence_caps:
  max_score_if_no_full_text: 74
  max_score_if_only_paywall_stub: 59
  max_score_if_source_is_unresolved: 59

digest_selection:
  max_weekday_cards: 5
  max_weekly_trends: 5
  bands:
    90_100:
      label: must_cover
      daily_policy: must_cover
      weekly_policy: must_include_or_reference
    75_89:
      label: strong_signal
      daily_policy: daily_candidate
      weekly_policy: include_if_not_redundant
    60_74:
      label: watch
      daily_policy: weekly_or_context
      weekly_policy: include_if_theme_supported
    below_60:
      label: ignore_or_log
      daily_policy: suppress
      weekly_policy: suppress_unless_operator_selected
```

- [ ] **Step 10: Create compact schemas**

Create `runtime/schemas/state_layout.yaml`:

```yaml
version: 1
root_dir: .state

collections:
  codex_runs:
    path_template: .state/codex-runs/{run_id}-{artifact}.json
  raw:
    path_template: .state/raw/{run_date}/{run_id}.json
  shortlists:
    path_template: .state/shortlists/{run_date}/{run_id}.json
  articles:
    path_template: .state/articles/{published_month}/{published_date}_{slug}.md
    allowed_producer: runner/tools/fetch_articles.py
  enriched:
    path_template: .state/enriched/{run_date}/{run_id}.json
  briefs_daily:
    path_template: .state/briefs/daily/{digest_date}__{delivery_profile}.json
  briefs_weekly:
    path_template: .state/briefs/weekly/{week_id}__{delivery_profile}.json
  reports:
    path_template: .state/reports/{run_date}/{run_id}.json
  change_requests:
    path_template: .state/change-requests/{request_date}/{request_id}.json
```

Create `runtime/schemas/artifacts.yaml`:

```yaml
version: 1

artifacts:
  raw_candidate:
    producer: runtime/prompts/weekday_discovery.md
    required_fields: [run_id, source_id, url, canonical_url, title, discovered_at, fetch_strategy]
  shortlisted_item:
    producer: runtime/prompts/weekday_discovery.md
    consumer: runner/tools/fetch_articles.py
    required_fields:
      - run_id
      - source_id
      - url
      - canonical_url
      - title
      - triage_decision
      - provisional_priority
      - industry_filter
      - shortlist_reason
  article_prefetch:
    producer: runner/tools/fetch_articles.py
    input_boundary: current_run_shortlist_only
    allowed_article_body_path: .state/articles/
    required_fields:
      - run_id
      - shortlist_path
      - results
  finish_draft:
    producer: runtime/prompts/weekday_finish.md
    consumer: runner/tools/materialize_digest.py
    required_fields:
      - schema_version
      - run_id
      - run_date
      - delivery_profile
      - enriched_items
      - daily_brief
      - digest_markdown
      - qa_review
      - telegram_preview
  daily_brief:
    producer: runner/tools/materialize_digest.py
    consumer: runtime/prompts/weekly_digest.md
  weekly_brief:
    producer: runtime/prompts/weekly_digest.md
  run_report:
    producer: runner/run.sh
    required_fields:
      - run_id
      - job
      - status
      - source_status
      - article_status
      - digest_status
      - delivery_status
```

- [ ] **Step 11: Run config validation**

Run:

```bash
python3 -m pytest runner/tests/test_runtime_config.py -q
```

Expected: PASS.

- [ ] **Step 12: Commit runtime config and judgment layer**

Run:

```bash
git add runtime runner/requirements.txt runner/tests/test_runtime_config.py
git commit -m "Add minimal runtime config and judgment layer"
```

Expected: commit succeeds.

---

### Task 3: Create Runtime Prompts and Adapter Map

**Files:**
- Create: `runtime/prompts/shared.md`
- Create: `runtime/prompts/weekday_discovery.md`
- Create: `runtime/prompts/weekday_finish.md`
- Create: `runtime/prompts/weekly_digest.md`
- Create: `runtime/adapters/source_map.yaml`
- Create/Copy: `runtime/adapters/google_play_app_page.md`
- Create/Copy: `runtime/adapters/inman_public_partial_text.md`
- Create/Copy: `runtime/adapters/itunes_lookup_api.md`
- Create/Copy: `runtime/adapters/mike_delprete_library.md`
- Create/Copy: `runtime/adapters/onlinemarketplaces_family.md`
- Create/Copy: `runtime/adapters/rightmove_plc.md`
- Create/Copy: `runtime/adapters/similarweb_site_overview.md`
- Create/Copy: `runtime/adapters/zillow_newsroom_html.md`
- Create: `runner/tests/test_runtime_prompts.py`

- [ ] **Step 1: Write failing prompt and adapter tests**

Create `runner/tests/test_runtime_prompts.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import pathlib

import yaml


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def read_text(relative_path: str) -> str:
    path = REPO_ROOT / relative_path
    assert path.exists(), f"missing required file: {relative_path}"
    return path.read_text(encoding="utf-8")


def read_yaml(relative_path: str) -> dict:
    path = REPO_ROOT / relative_path
    assert path.exists(), f"missing required file: {relative_path}"
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    assert isinstance(data, dict)
    return data


def test_prompts_reference_new_runtime_files() -> None:
    discovery = read_text("runtime/prompts/weekday_discovery.md")
    finish = read_text("runtime/prompts/weekday_finish.md")
    weekly = read_text("runtime/prompts/weekly_digest.md")
    combined = "\n".join([discovery, finish, weekly])
    assert "runtime/judgment/industry_filter.yaml" in discovery
    assert "runtime/judgment/discovery_rules.yaml" in discovery
    assert "runtime/judgment/scoring_profile.yaml" in finish
    assert "runtime/judgment/scoring_profile.yaml" in weekly
    assert "cowork/" not in combined
    assert "config/runtime/" not in combined
    assert "ops/codex-cli/" not in combined


def test_discovery_prompt_forbids_full_text() -> None:
    discovery = read_text("runtime/prompts/weekday_discovery.md")
    assert "Do not fetch or read full article text" in discovery
    assert "triage_decision" in discovery
    assert "industry_filter" in discovery
    assert "reject_not_industry" in discovery


def test_finish_prompt_allows_full_text_only_through_manifest() -> None:
    finish = read_text("runtime/prompts/weekday_finish.md")
    assert "article prefetch manifest" in finish
    assert "current-run shortlisted URL" in finish
    assert ".state/articles/" in finish
    assert "Do not read article files that are not referenced by the manifest" in finish


def test_source_map_resolves_every_configured_source() -> None:
    source_map = read_yaml("runtime/adapters/source_map.yaml")
    weekday = read_yaml("runtime/sources/weekday.yaml")
    weekly = read_yaml("runtime/sources/weekly.yaml")
    source_ids = {source["id"] for source in weekday["sources"] + weekly["sources"]}
    mapped = set(source_map["sources"])
    assert source_ids <= mapped
    for source_id in source_ids:
        adapter = source_map["sources"][source_id]["adapter"]
        assert adapter == "none" or (REPO_ROOT / adapter).exists(), source_id
```

- [ ] **Step 2: Run prompt tests to verify they fail before files exist**

Run:

```bash
python3 -m pytest runner/tests/test_runtime_prompts.py -q
```

Expected: FAIL with `missing required file: runtime/prompts/weekday_discovery.md`.

- [ ] **Step 3: Create shared prompt**

Create `runtime/prompts/shared.md`:

```md
# Shared Runtime Brief

Purpose: identify global proptech and real estate marketplace signals that may
affect Avito Real Estate strategy, product, monetization, demand, supply, or
competitive position.

Use these runtime files as canonical context:

- `runtime/schedules.yaml`
- `runtime/sources/weekday.yaml` or `runtime/sources/weekly.yaml`
- `runtime/judgment/industry_filter.yaml`
- `runtime/judgment/discovery_rules.yaml`
- `runtime/judgment/scoring_profile.yaml`
- `runtime/adapters/source_map.yaml`
- `runtime/schemas/artifacts.yaml`
- `runtime/schemas/state_layout.yaml`

Do not edit repository source files during scheduled runs. If a persistent fix
is needed, write a change request artifact under `.state/change-requests/`.
```

- [ ] **Step 4: Create weekday discovery prompt**

Create `runtime/prompts/weekday_discovery.md`:

```md
# Weekday Discovery Prompt

Run discovery for `runner/run.sh weekday`.

Read:

- `runtime/prompts/shared.md`
- `runtime/sources/weekday.yaml`
- `runtime/judgment/industry_filter.yaml`
- `runtime/judgment/discovery_rules.yaml`
- `runtime/adapters/source_map.yaml`

Use runner source prefetch artifacts supplied in the generated prompt as local
evidence. Do not re-run static network fetches represented by those artifacts.

Do not fetch or read full article text. Discovery may use only title, snippet,
listing metadata, source metadata, URL markers, and adapter notes.

For every candidate, apply `runtime/judgment/industry_filter.yaml` before
shortlist rules. If the item fails the industry gate, set
`triage_decision = reject`, set `industry_filter.status = failed`, and include
`reject_not_industry` in the rejection reason. Such items must not enter the
shortlist.

For industry-relevant items, apply `runtime/judgment/discovery_rules.yaml` and
emit bounded shortlist artifacts with:

- `triage_decision`
- `provisional_priority`
- `industry_filter`
- `shortlist_reason`
- compact evidence from title/snippet/listing metadata only

Allowed writes:

- `.state/raw/{run_date}/`
- `.state/shortlists/{run_date}/`
- `.state/reports/{run_date}/`
- optional `.state/change-requests/{request_date}/`

Final response must include source status, raw shard path, shortlist shard path,
shortlisted count, rejected-not-industry count, and change request paths.
```

- [ ] **Step 5: Create weekday finish prompt**

Create `runtime/prompts/weekday_finish.md`:

```md
# Weekday Finish Prompt

Run enrichment, scoring, QA, and daily digest draft generation for
`runner/run.sh weekday`.

Read:

- `runtime/prompts/shared.md`
- `runtime/judgment/scoring_profile.yaml`
- `runtime/schemas/artifacts.yaml`
- current-run shortlist path from the generated prompt
- current-run article prefetch manifest from the generated prompt

Full text is available only through the article prefetch manifest. You may read
`.state/articles/` files only when the manifest entry matches a current-run
shortlisted URL or canonical URL. Do not read article files that are not
referenced by the manifest. Do not fetch more article URLs.

Apply `runtime/judgment/scoring_profile.yaml` after reading available article
text or snippet fallback evidence. Respect evidence caps, especially
`max_score_if_no_full_text`.

For `telegram_digest`, all human-facing digest prose must be Russian. Source
names, company names, product names, article titles, and URLs may remain in
their original language.

Write exactly one finish draft JSON to the finish draft path provided by the
generated prompt. Do not directly write final digest, daily brief, run report,
or Telegram delivery artifacts; `runner/tools/materialize_digest.py` owns
materialization.

The finish draft must include:

- `schema_version`
- `run_id`
- `run_date`
- `delivery_profile`
- `enriched_items`
- `daily_brief`
- `digest_markdown`
- `qa_review`
- `telegram_preview`
- `telegram_delivery`

The digest body must not include `.state/`, article file paths, full run IDs,
operator notes, or article bodies.
```

- [ ] **Step 6: Create weekly prompt**

Create `runtime/prompts/weekly_digest.md`:

```md
# Weekly Digest Prompt

Run weekly synthesis for `runner/run.sh weekly`.

Read:

- `runtime/prompts/shared.md`
- `runtime/sources/weekly.yaml`
- `runtime/judgment/industry_filter.yaml`
- `runtime/judgment/discovery_rules.yaml`
- `runtime/judgment/scoring_profile.yaml`
- compact daily briefs from `.state/briefs/daily/` for the target ISO week
- limited prior weekly briefs from `.state/briefs/weekly/`

Weekly should primarily synthesize compact daily briefs. Do not read the
historical markdown digest archive. Do not read broad `.state/articles/`.

If the weekly runner provides new weekly context source evidence, apply the same
industry and discovery rules before considering it. Full article text for
weekly-only context is allowed only if the generated prompt provides a
current-run article prefetch manifest for that weekly shortlist.

Write the weekly digest draft and compact weekly brief in the output paths
provided by the generated prompt. Preserve evidence limits in the final run
report.
```

- [ ] **Step 7: Create source adapter map**

Create `runtime/adapters/source_map.yaml`:

```yaml
version: 1
sources:
  aim_group_real_estate_intelligence:
    adapter: none
    note: baseline RSS
  onlinemarketplaces:
    adapter: runtime/adapters/onlinemarketplaces_family.md
    note: listing-style page in OnlineMarketplaces family
  mike_delprete:
    adapter: runtime/adapters/mike_delprete_library.md
    note: dated article library with public content caveats
  zillow_newsroom:
    adapter: runtime/adapters/zillow_newsroom_html.md
    note: Mediaroom RSS and newsroom caveats
  costar_homes:
    adapter: none
    note: baseline RSS
  redfin_news:
    adapter: none
    note: baseline RSS
  rea_group_media_releases:
    adapter: none
    note: baseline static HTML media releases page
  rightmove_plc:
    adapter: runtime/adapters/rightmove_plc.md
    note: static page and public RNS PDF anchors
  similarweb_global_real_estate:
    adapter: runtime/adapters/similarweb_site_overview.md
    note: public site overview pages
  property_portal_watch:
    adapter: runtime/adapters/onlinemarketplaces_family.md
    note: same publisher family and listing-style discovery
  inman_tech_innovation:
    adapter: runtime/adapters/inman_public_partial_text.md
    note: RSS discovery and public visible article text as snippet fallback
  similarweb_country_real_estate:
    adapter: runtime/adapters/similarweb_site_overview.md
    note: public site overview pages
  zillow_ios:
    adapter: runtime/adapters/itunes_lookup_api.md
    note: Apple lookup API
  zillow_android:
    adapter: runtime/adapters/google_play_app_page.md
    note: Google Play page scrape
  rightmove_ios:
    adapter: runtime/adapters/itunes_lookup_api.md
    note: Apple lookup API
  rightmove_android:
    adapter: runtime/adapters/google_play_app_page.md
    note: Google Play page scrape
```

- [ ] **Step 8: Copy retained adapter notes into the new runtime directory**

Run:

```bash
mkdir -p runtime/adapters
cp cowork/adapters/google_play_app_page.md runtime/adapters/google_play_app_page.md
cp cowork/adapters/inman_public_partial_text.md runtime/adapters/inman_public_partial_text.md
cp cowork/adapters/itunes_lookup_api.md runtime/adapters/itunes_lookup_api.md
cp cowork/adapters/mike_delprete_library.md runtime/adapters/mike_delprete_library.md
cp cowork/adapters/onlinemarketplaces_family.md runtime/adapters/onlinemarketplaces_family.md
cp cowork/adapters/rightmove_plc.md runtime/adapters/rightmove_plc.md
cp cowork/adapters/similarweb_site_overview.md runtime/adapters/similarweb_site_overview.md
cp cowork/adapters/zillow_newsroom_html.md runtime/adapters/zillow_newsroom_html.md
```

Then replace old path references inside copied adapter files:

```bash
perl -0pi -e 's#cowork/adapters/#runtime/adapters/#g; s#config/runtime/#runtime/#g' runtime/adapters/*.md
```

- [ ] **Step 9: Run prompt and adapter tests**

Run:

```bash
python3 -m pytest runner/tests/test_runtime_prompts.py -q
```

Expected: PASS.

- [ ] **Step 10: Commit runtime prompts and adapters**

Run:

```bash
git add runtime/prompts runtime/adapters runner/tests/test_runtime_prompts.py
git commit -m "Add runtime prompts and adapter map"
```

Expected: commit succeeds.

---

### Task 4: Build Runtime Validator

**Files:**
- Create: `runner/tools/common.py`
- Create: `runner/tools/validate_runtime.py`
- Create: `runner/tests/test_validate_runtime.py`

- [ ] **Step 1: Write failing validator tests**

Create `runner/tests/test_validate_runtime.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
VALIDATOR = REPO_ROOT / "runner/tools/validate_runtime.py"


def run_validator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(VALIDATOR), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_validator_config_check_passes() -> None:
    result = run_validator("--check", "config")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "passed"
    assert payload["check"] == "config"
    assert payload["supported_jobs"] == ["weekday", "weekly"]


def test_validator_rejects_old_runtime_references_in_prompts() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        prompt_dir = root / "runtime/prompts"
        prompt_dir.mkdir(parents=True)
        (prompt_dir / "weekday_discovery.md").write_text("Read cowork/shared/contracts.md\n", encoding="utf-8")
        result = subprocess.run(
            ["python3", str(VALIDATOR), "--check", "prompts", "--repo-root", str(root)],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    assert result.returncode == 1
    assert "old runtime path reference" in result.stderr


def test_validator_all_check_passes_after_samples_exist() -> None:
    result = run_validator("--check", "all")
    if result.returncode != 0:
        assert "missing sample" in result.stderr
    else:
        payload = json.loads(result.stdout)
        assert payload["status"] == "passed"
        assert payload["check"] == "all"
```

- [ ] **Step 2: Run validator tests to verify they fail before validator exists**

Run:

```bash
python3 -m pytest runner/tests/test_validate_runtime.py -q
```

Expected: FAIL because `runner/tools/validate_runtime.py` does not exist.

- [ ] **Step 3: Create common helper**

Create `runner/tools/common.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
from typing import Any

import yaml


def repo_root_from(path: str | None) -> pathlib.Path:
    if path:
        return pathlib.Path(path).resolve()
    return pathlib.Path(__file__).resolve().parents[2]


def read_yaml(path: pathlib.Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Create validator**

Create `runner/tools/validate_runtime.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from common import read_yaml, repo_root_from


OLD_PATH_MARKERS = ("cowork/", "config/runtime/", "ops/codex-cli/")


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def require_file(root: pathlib.Path, relative_path: str) -> pathlib.Path:
    path = root / relative_path
    if not path.exists():
        fail(f"missing required file: {relative_path}")
    return path


def check_config(root: pathlib.Path) -> dict[str, Any]:
    manifest = read_yaml(require_file(root, "runtime/manifest.yaml"))
    schedules = read_yaml(require_file(root, "runtime/schedules.yaml"))
    jobs = sorted(schedules.get("jobs", {}))
    if jobs != ["weekday", "weekly"]:
        fail(f"runtime/schedules.yaml must contain only weekday and weekly jobs, got {jobs}")
    if manifest.get("supported_jobs") != ["weekday", "weekly"]:
        fail("runtime/manifest.yaml supported_jobs must be ['weekday', 'weekly']")
    for relative_path in (
        "runtime/sources/weekday.yaml",
        "runtime/sources/weekly.yaml",
        "runtime/judgment/industry_filter.yaml",
        "runtime/judgment/discovery_rules.yaml",
        "runtime/judgment/scoring_profile.yaml",
        "runtime/schemas/artifacts.yaml",
        "runtime/schemas/state_layout.yaml",
    ):
        require_file(root, relative_path)
    return {"supported_jobs": manifest["supported_jobs"]}


def check_prompts(root: pathlib.Path) -> dict[str, Any]:
    prompt_dir = require_file(root, "runtime/prompts")
    checked: list[str] = []
    for path in sorted(prompt_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for marker in OLD_PATH_MARKERS:
            if marker in text:
                fail(f"old runtime path reference in {path.relative_to(root)}: {marker}")
        checked.append(str(path.relative_to(root)))
    expected = {
        "runtime/prompts/shared.md",
        "runtime/prompts/weekday_discovery.md",
        "runtime/prompts/weekday_finish.md",
        "runtime/prompts/weekly_digest.md",
    }
    if set(checked) != expected:
        fail(f"prompt set mismatch: {checked}")
    return {"prompts": checked}


def check_adapters(root: pathlib.Path) -> dict[str, Any]:
    source_map = read_yaml(require_file(root, "runtime/adapters/source_map.yaml"))
    weekday = read_yaml(require_file(root, "runtime/sources/weekday.yaml"))
    weekly = read_yaml(require_file(root, "runtime/sources/weekly.yaml"))
    configured_ids = {source["id"] for source in weekday["sources"] + weekly["sources"]}
    mapped_ids = set(source_map.get("sources", {}))
    missing = sorted(configured_ids - mapped_ids)
    if missing:
        fail(f"missing source adapter mappings: {missing}")
    for source_id in sorted(configured_ids):
        adapter = source_map["sources"][source_id]["adapter"]
        if adapter != "none":
            require_file(root, adapter)
    return {"source_count": len(configured_ids)}


def check_schemas(root: pathlib.Path) -> dict[str, Any]:
    artifacts = read_yaml(require_file(root, "runtime/schemas/artifacts.yaml"))
    layout = read_yaml(require_file(root, "runtime/schemas/state_layout.yaml"))
    article = artifacts["artifacts"]["article_prefetch"]
    if article["input_boundary"] != "current_run_shortlist_only":
        fail("article_prefetch input_boundary must be current_run_shortlist_only")
    if layout["collections"]["articles"]["allowed_producer"] != "runner/tools/fetch_articles.py":
        fail("articles collection must be produced only by fetch_articles.py")
    return {"artifact_count": len(artifacts["artifacts"])}


def check_samples(root: pathlib.Path) -> dict[str, Any]:
    sample_paths = [
        "samples/weekday-digest.md",
        "samples/weekly-digest.md",
        "samples/run-report.json",
    ]
    for relative_path in sample_paths:
        require_file(root, relative_path)
    report = json.loads((root / "samples/run-report.json").read_text(encoding="utf-8"))
    for key in ("run_id", "job", "status", "source_status", "digest_status", "delivery_status"):
        if key not in report:
            fail(f"samples/run-report.json missing key: {key}")
    return {"samples": sample_paths}


def check_docs(root: pathlib.Path) -> dict[str, Any]:
    doc_paths = [
        "README.md",
        "AGENTS.md",
        "docs/operations.md",
        "docs/design.md",
        "COMPLETION_AUDIT.md",
    ]
    existing = []
    for relative_path in doc_paths:
        path = root / relative_path
        if path.exists():
            text = path.read_text(encoding="utf-8")
            for marker in OLD_PATH_MARKERS:
                if marker in text:
                    fail(f"old runtime path reference in {relative_path}: {marker}")
            existing.append(relative_path)
    required_before_cleanup = ["docs/operations.md", "docs/design.md"]
    for relative_path in required_before_cleanup:
        require_file(root, relative_path)
    return {"docs_checked": existing}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", choices=["config", "prompts", "adapters", "schemas", "samples", "docs", "all"], required=True)
    parser.add_argument("--repo-root")
    args = parser.parse_args()
    root = repo_root_from(args.repo_root)
    results: dict[str, Any] = {}
    if args.check in ("config", "all"):
        results.update(check_config(root))
    if args.check in ("prompts", "all"):
        results.update(check_prompts(root))
    if args.check in ("adapters", "all"):
        results.update(check_adapters(root))
    if args.check in ("schemas", "all"):
        results.update(check_schemas(root))
    if args.check in ("samples", "all"):
        results.update(check_samples(root))
    if args.check in ("docs", "all"):
        results.update(check_docs(root))
    print(json.dumps({"status": "passed", "check": args.check, **results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run validator checks that do not require samples**

Run:

```bash
python3 runner/tools/validate_runtime.py --check config
python3 runner/tools/validate_runtime.py --check prompts
python3 runner/tools/validate_runtime.py --check adapters
python3 runner/tools/validate_runtime.py --check schemas
python3 -m pytest runner/tests/test_validate_runtime.py::test_validator_config_check_passes -q
python3 -m pytest runner/tests/test_validate_runtime.py::test_validator_rejects_old_runtime_references_in_prompts -q
```

Expected: every command passes.

- [ ] **Step 6: Commit validator**

Run:

```bash
git add runner/tools/common.py runner/tools/validate_runtime.py runner/tests/test_validate_runtime.py
git commit -m "Add runtime validation gate"
```

Expected: commit succeeds.

---

### Task 5: Build Server Runner Shell

**Files:**
- Create: `runner/run.sh`
- Create: `runner/tests/test_runner_shell.py`
- Modify: `.env.example`

- [ ] **Step 1: Write failing shell tests**

Create `runner/tests/test_runner_shell.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "runner/run.sh"


def run_runner(*args: str, env_file: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CODEX_BIN"] = "false"
    if env_file:
        env["PROPMON_ENV_FILE"] = str(env_file)
    return subprocess.run(
        ["bash", str(RUNNER), *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_self_test_weekday_reports_new_paths() -> None:
    result = run_runner("--self-test", "weekday")
    assert result.returncode == 0
    assert "Runner self-test passed: weekday" in result.stdout
    assert "runtime/prompts/weekday_discovery.md" in result.stdout
    assert "runner/tools/fetch_sources.py" in result.stdout
    assert "runner/tools/fetch_articles.py" in result.stdout


def test_self_test_weekly_reports_new_paths() -> None:
    result = run_runner("--self-test", "weekly")
    assert result.returncode == 0
    assert "Runner self-test passed: weekly" in result.stdout
    assert "runtime/prompts/weekly_digest.md" in result.stdout
    assert "runner/tools/send_telegram.py" in result.stdout


def test_runner_rejects_unsupported_job() -> None:
    result = run_runner("--self-test", "breaking_alert")
    assert result.returncode == 2
    assert "Usage:" in result.stderr


def test_env_loader_rejects_command_substitution() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        marker = pathlib.Path(tmpdir) / "side-effect"
        env_file = pathlib.Path(tmpdir) / ".env.bad"
        env_file.write_text(f"HTTP_USER_AGENT='safe'\nBAD=$(touch {marker})\n", encoding="utf-8")
        result = run_runner("--self-test", "weekday", env_file=env_file)
    assert result.returncode == 2
    assert "Command substitution is not allowed" in result.stderr
    assert not marker.exists()
```

- [ ] **Step 2: Run shell tests to verify they fail before runner exists**

Run:

```bash
python3 -m pytest runner/tests/test_runner_shell.py -q
```

Expected: FAIL because `runner/run.sh` does not exist.

- [ ] **Step 3: Create runner shell**

Create `runner/run.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s [--self-test] {weekday|weekly}\n' "$0" >&2
}

SELF_TEST=0
if [ "${1:-}" = "--self-test" ]; then
  SELF_TEST=1
  shift
fi

if [ "$#" -ne 1 ]; then
  usage
  exit 2
fi

JOB="$1"
case "$JOB" in
  weekday|weekly) ;;
  *)
    usage
    exit 2
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_ROOT="$REPO_ROOT/.state/codex-runs"
RUN_DATE="$(date -u '+%Y-%m-%d')"
RUN_ID="$(date -u '+%Y%m%dT%H%M%SZ')-$JOB"
LOCK_DIR="$RUN_ROOT/$JOB.lock"
CODEX_BIN="${CODEX_BIN:-codex}"
ENV_FILE="${PROPMON_ENV_FILE:-$REPO_ROOT/.env}"

FETCH_SOURCES="$REPO_ROOT/runner/tools/fetch_sources.py"
FETCH_ARTICLES="$REPO_ROOT/runner/tools/fetch_articles.py"
MATERIALIZE="$REPO_ROOT/runner/tools/materialize_digest.py"
SEND_TELEGRAM="$REPO_ROOT/runner/tools/send_telegram.py"
VALIDATE="$REPO_ROOT/runner/tools/validate_runtime.py"

validate_env_file() {
  local env_file="$1"
  local line line_no key value
  line_no=0
  while IFS= read -r line || [ -n "$line" ]; do
    line_no=$((line_no + 1))
    case "$line" in
      ""|\#*) continue ;;
      export\ *) line="${line#export }" ;;
    esac
    if [[ "$line" != *=* ]]; then
      printf 'Invalid environment file: %s line %s\n' "$env_file" "$line_no" >&2
      exit 2
    fi
    key="${line%%=*}"
    value="${line#*=}"
    if ! [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      printf 'Invalid environment variable name: %s line %s\n' "$env_file" "$line_no" >&2
      exit 2
    fi
    case "$value" in
      *'$('*|*'`'*)
        printf 'Command substitution is not allowed in environment files: %s line %s\n' "$env_file" "$line_no" >&2
        exit 2
        ;;
    esac
    if [[ "$value" =~ [[:space:]\#\$\"\'\(\)] ]]; then
      if [[ ! "$value" =~ ^\'([^\'\\]|\\.)*\'$ ]]; then
        printf 'Values with spaces, parentheses, #, $, or quotes must be single-quoted: %s line %s\n' "$env_file" "$line_no" >&2
        exit 2
      fi
    fi
  done < "$env_file"
}

load_env_file() {
  local env_file="$1"
  local line key value
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ""|\#*) continue ;;
      export\ *) line="${line#export }" ;;
    esac
    key="${line%%=*}"
    value="${line#*=}"
    if [[ "$value" =~ ^\'([^\'\\]|\\.)*\'$ ]]; then
      value="${value:1:${#value}-2}"
    fi
    printf -v "$key" '%s' "$value"
    export "$key"
  done < "$env_file"
}

if [ -n "${PROPMON_ENV_FILE:-}" ] && [ ! -f "$ENV_FILE" ]; then
  printf 'Environment file not found: %s\n' "$ENV_FILE" >&2
  exit 2
fi
if [ -f "$ENV_FILE" ]; then
  validate_env_file "$ENV_FILE"
  load_env_file "$ENV_FILE"
fi

if [ "$SELF_TEST" = "1" ]; then
  python3 "$VALIDATE" --check config >/dev/null
  printf 'Runner self-test passed: %s\n' "$JOB"
  printf 'Runtime manifest: %s\n' "$REPO_ROOT/runtime/manifest.yaml"
  printf 'Schedules: %s\n' "$REPO_ROOT/runtime/schedules.yaml"
  if [ "$JOB" = "weekday" ]; then
    printf 'Discovery prompt: %s\n' "$REPO_ROOT/runtime/prompts/weekday_discovery.md"
    printf 'Finish prompt: %s\n' "$REPO_ROOT/runtime/prompts/weekday_finish.md"
    printf 'Source fetcher: %s\n' "$FETCH_SOURCES"
    printf 'Article fetcher: %s\n' "$FETCH_ARTICLES"
    printf 'Materializer: %s\n' "$MATERIALIZE"
  else
    printf 'Weekly prompt: %s\n' "$REPO_ROOT/runtime/prompts/weekly_digest.md"
  fi
  printf 'Telegram sender: %s\n' "$SEND_TELEGRAM"
  printf 'Validator: %s\n' "$VALIDATE"
  exit 0
fi

mkdir -p "$RUN_ROOT"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  printf 'Another %s run appears to be active: %s\n' "$JOB" "$LOCK_DIR" >&2
  exit 10
fi
cleanup() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cd "$REPO_ROOT"
if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
  . "$REPO_ROOT/.venv/bin/activate"
fi

printf 'Starting PropTech Monitor run: %s (%s)\n' "$JOB" "$RUN_ID"
python3 "$VALIDATE" --check config >/dev/null

if [ "$JOB" = "weekday" ]; then
  printf 'Weekday execution is enabled after Task 6 completes: %s\n' "$RUN_ID" >&2
  exit 2
fi

printf 'Weekly execution is enabled after Task 8 completes: %s\n' "$RUN_ID" >&2
exit 2
```

- [ ] **Step 4: Make runner executable**

Run:

```bash
chmod +x runner/run.sh
```

Expected: no output.

- [ ] **Step 5: Update `.env.example`**

Replace `.env.example` content with:

```text
# Telegram delivery
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_MESSAGE_THREAD_ID=''

# Fetch
HTTP_USER_AGENT='PropTechMonitor/1.0 (+team@example.com)'
REQUEST_TIMEOUT_SECONDS=20
```

- [ ] **Step 6: Run shell tests**

Run:

```bash
python3 -m pytest runner/tests/test_runner_shell.py -q
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
```

Expected: PASS and both self-tests print `Runner self-test passed`.

- [ ] **Step 7: Commit shell runner**

Run:

```bash
git add runner/run.sh runner/tests/test_runner_shell.py .env.example
git commit -m "Add minimal weekday weekly runner shell"
```

Expected: commit succeeds.

---

### Task 6: Migrate Source and Article Fetch Helpers

**Files:**
- Create: `runner/tools/fetch_sources.py`
- Create: `runner/tools/fetch_articles.py`
- Create: `runner/tests/test_fetch_sources.py`
- Create: `runner/tests/test_fetch_articles.py`
- Modify: `runner/run.sh`

- [ ] **Step 1: Copy current helper implementations into new runner paths**

Run:

```bash
cp tools/source_discovery_prefetch.py runner/tools/fetch_sources.py
cp tools/shortlist_article_prefetch.py runner/tools/fetch_articles.py
```

Then edit imports and path constants in both copied files:

- replace references to `config/runtime/schedule_bindings.yaml` with `runtime/schedules.yaml`;
- replace references to `config/runtime/source-groups/daily_core.yaml` with `runtime/sources/weekday.yaml`;
- replace references to `config/runtime/source-groups/weekly_context.yaml` with `runtime/sources/weekly.yaml`;
- replace references to `tools/rss_fetch.py`, `tools/browser_fetch.py`, `tools/article_fetch.py`, and `tools/pdf_extract.py` with copied or inline helper functions inside the new runner files;
- keep output under `.state/codex-runs/`;
- keep article bodies under `.state/articles/`.

- [ ] **Step 2: Write source fetch tests**

Create `runner/tests/test_fetch_sources.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FETCH_SOURCES = REPO_ROOT / "runner/tools/fetch_sources.py"


def test_fetch_sources_self_test_returns_runtime_paths() -> None:
    result = subprocess.run(
        ["python3", str(FETCH_SOURCES), "--job", "weekday", "--run-id", "20260505T090000Z-weekday", "--repo-root", str(REPO_ROOT), "--self-test"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "passed"
    assert payload["job"] == "weekday"
    assert payload["source_profile_path"] == "runtime/sources/weekday.yaml"


def test_fetch_sources_rejects_breaking_alert() -> None:
    result = subprocess.run(
        ["python3", str(FETCH_SOURCES), "--job", "breaking_alert", "--run-id", "x", "--repo-root", str(REPO_ROOT), "--self-test"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
```

- [ ] **Step 3: Write article fetch boundary tests**

Create `runner/tests/test_fetch_articles.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FETCH_ARTICLES = REPO_ROOT / "runner/tools/fetch_articles.py"


def write_json(path: pathlib.Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_fetch_articles_self_test_enforces_shortlist_boundary() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        shortlist = root / ".state/shortlists/2026-05-05/shortlist.json"
        write_json(
            shortlist,
            [
                {
                    "run_id": "monitor_sources__20260505T090000Z__weekday",
                    "source_id": "example",
                    "url": "https://example.test/story",
                    "canonical_url": "https://example.test/story",
                    "title": "Portal feature",
                    "triage_decision": "shortlist",
                    "provisional_priority": "high",
                    "industry_filter": {"status": "passed"},
                    "shortlist_reason": "Relevant portal product signal.",
                }
            ],
        )
        result = subprocess.run(
            [
                "python3",
                str(FETCH_ARTICLES),
                "--repo-root",
                str(root),
                "--run-id",
                "20260505T091000Z-weekday",
                "--shortlist-path",
                str(shortlist),
                "--self-test",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "passed"
    assert payload["shortlisted_count"] == 1
    assert payload["boundary"] == "current_run_shortlist_only"
```

- [ ] **Step 4: Add self-test flags to copied fetch helpers**

In `runner/tools/fetch_sources.py`, add an argparse option:

```python
parser.add_argument("--self-test", action="store_true")
```

When `--self-test` is set, return:

```python
{
    "status": "passed",
    "job": args.job,
    "source_profile_path": "runtime/sources/weekday.yaml" if args.job == "weekday" else "runtime/sources/weekly.yaml",
}
```

In `runner/tools/fetch_articles.py`, add an argparse option:

```python
parser.add_argument("--self-test", action="store_true")
```

When `--self-test` is set, read the shortlist JSON, count entries where
`triage_decision == "shortlist"`, and return:

```python
{
    "status": "passed",
    "shortlisted_count": shortlisted_count,
    "boundary": "current_run_shortlist_only",
}
```

- [ ] **Step 5: Wire weekday runner through source and article stages**

Modify the weekday branch in `runner/run.sh` to call:

```bash
SOURCE_SUMMARY="$RUN_ROOT/$RUN_ID-source-summary.json"
SHORTLIST_PATH="$REPO_ROOT/.state/shortlists/$RUN_DATE/weekday-shortlist.json"
ARTICLE_SUMMARY="$RUN_ROOT/$RUN_ID-article-summary.json"

python3 "$FETCH_SOURCES" \
  --job weekday \
  --run-id "$RUN_ID" \
  --repo-root "$REPO_ROOT" \
  --pretty > "$SOURCE_SUMMARY"

printf 'Source summary: %s\n' "$SOURCE_SUMMARY"

if [ ! -f "$SHORTLIST_PATH" ]; then
  printf 'Shortlist not found after discovery stage: %s\n' "$SHORTLIST_PATH" >&2
  exit 20
fi

python3 "$FETCH_ARTICLES" \
  --repo-root "$REPO_ROOT" \
  --run-id "$RUN_ID" \
  --shortlist-path "$SHORTLIST_PATH" \
  --pretty > "$ARTICLE_SUMMARY"

printf 'Article summary: %s\n' "$ARTICLE_SUMMARY"
printf 'Weekday finish execution is enabled after Task 7 completes: %s\n' "$RUN_ID" >&2
exit 2
```

- [ ] **Step 6: Run fetch tests and shell self-tests**

Run:

```bash
python3 -m pytest runner/tests/test_fetch_sources.py -q
python3 -m pytest runner/tests/test_fetch_articles.py -q
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
```

Expected: PASS.

- [ ] **Step 7: Commit fetch helper migration**

Run:

```bash
git add runner/tools/fetch_sources.py runner/tools/fetch_articles.py runner/tests/test_fetch_sources.py runner/tests/test_fetch_articles.py runner/run.sh
git commit -m "Migrate source and article fetch helpers"
```

Expected: commit succeeds.

---

### Task 7: Migrate Materializer and Telegram Sender

**Files:**
- Create: `runner/tools/materialize_digest.py`
- Create: `runner/tools/send_telegram.py`
- Create: `runner/tests/test_materialize_digest.py`
- Create: `runner/tests/test_send_telegram.py`
- Modify: `runner/run.sh`

- [ ] **Step 1: Copy current materializer and delivery code**

Run:

```bash
cp tools/stage_c_finish.py runner/tools/materialize_digest.py
cp tools/telegram_send.py runner/tools/send_telegram.py
```

Then edit both copied files:

- replace `config/runtime/schedule_bindings.yaml` with `runtime/schedules.yaml`;
- replace `telegram_weekly_digest` and `telegram_digest` profile loading to read `delivery_profiles` from `runtime/schedules.yaml`;
- replace old path references in help text and diagnostics;
- keep daily digest output under `.state/digests/` during new-run validation, then materialize curated public copies only when samples are created.

- [ ] **Step 2: Write materializer tests**

Create `runner/tests/test_materialize_digest.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MATERIALIZE = REPO_ROOT / "runner/tools/materialize_digest.py"


def write_json(path: pathlib.Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_materializer_rejects_digest_with_state_path_leak() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        draft = root / "draft.json"
        write_json(
            draft,
            {
                "schema_version": 1,
                "run_id": "20260505T091500Z-weekday",
                "run_date": "2026-05-05",
                "delivery_profile": "telegram_digest",
                "enriched_items": [],
                "daily_brief": {"markdown_path": ".state/digests/2026-05-05-daily-digest.md"},
                "digest_markdown": "# PropTech Monitor Daily | 5 мая 2026\n\n.state/articles/leak.md\n",
                "qa_review": {"status": "validated", "critical_findings_count": 0},
                "telegram_preview": {"status": "unavailable", "preview_url": None},
                "telegram_delivery": {"status": "not_configured", "delivered": False},
            },
        )
        result = subprocess.run(
            ["python3", str(MATERIALIZE), "--repo-root", str(root), "--draft-path", str(draft), "--self-test"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    assert result.returncode == 1
    assert "digest body leaks runtime path" in result.stderr
```

- [ ] **Step 3: Write Telegram sender tests**

Create `runner/tests/test_send_telegram.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SENDER = REPO_ROOT / "runner/tools/send_telegram.py"


def test_send_telegram_dry_run_reports_not_configured_without_secrets() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        digest = pathlib.Path(tmpdir) / "digest.md"
        digest.write_text("# PropTech Monitor Daily | 5 мая 2026\n\nТест.\n", encoding="utf-8")
        result = subprocess.run(
            ["python3", str(SENDER), "--profile", "telegram_digest", "--dry-run", "--input", str(digest)],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] in {"dry_run", "not_configured"}
    assert "TELEGRAM_BOT_TOKEN" not in result.stdout
```

- [ ] **Step 4: Add materializer self-test boundary**

In `runner/tools/materialize_digest.py`, add `--self-test`. In self-test mode, read `--draft-path` and fail with exit code `1` if `digest_markdown` contains any of:

```python
FORBIDDEN_DIGEST_MARKERS = (".state/", "article_file", "codex-runs", "run_id")
```

The error text must include:

```text
digest body leaks runtime path
```

- [ ] **Step 5: Add sender dry-run input option**

In `runner/tools/send_telegram.py`, support:

```text
--profile telegram_digest
--profile telegram_weekly_digest
--input path/to/digest.md
--dry-run
```

Dry-run must print a JSON object:

```json
{
  "status": "dry_run",
  "profile": "telegram_digest",
  "parts": 1,
  "delivered": false
}
```

If Telegram env is missing in non-dry-run mode, print:

```json
{
  "status": "not_configured",
  "profile": "telegram_digest",
  "delivered": false
}
```

- [ ] **Step 6: Wire weekday finish materialization and delivery**

Modify the weekday branch in `runner/run.sh` after article fetch to use:

```bash
FINISH_DRAFT="$RUN_ROOT/$RUN_ID-finish-draft.json"
MATERIALIZE_SUMMARY="$RUN_ROOT/$RUN_ID-materialize-summary.json"
DELIVERY_REPORT="$RUN_ROOT/$RUN_ID-delivery-report.json"

if [ ! -f "$FINISH_DRAFT" ]; then
  printf 'Finish draft not found: %s\n' "$FINISH_DRAFT" >&2
  exit 21
fi

python3 "$MATERIALIZE" \
  --repo-root "$REPO_ROOT" \
  --draft-path "$FINISH_DRAFT" \
  --pretty > "$MATERIALIZE_SUMMARY"

DIGEST_PATH="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["digest_path"])' "$MATERIALIZE_SUMMARY")"

python3 "$SEND_TELEGRAM" \
  --profile telegram_digest \
  --input "$DIGEST_PATH" \
  --report-path "$DELIVERY_REPORT" > "$RUN_ROOT/$RUN_ID-send-stdout.json"

printf 'Materialize summary: %s\n' "$MATERIALIZE_SUMMARY"
printf 'Delivery report: %s\n' "$DELIVERY_REPORT"
```

- [ ] **Step 7: Run materializer and sender tests**

Run:

```bash
python3 -m pytest runner/tests/test_materialize_digest.py -q
python3 -m pytest runner/tests/test_send_telegram.py -q
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
```

Expected: PASS.

- [ ] **Step 8: Commit materializer and sender**

Run:

```bash
git add runner/tools/materialize_digest.py runner/tools/send_telegram.py runner/tests/test_materialize_digest.py runner/tests/test_send_telegram.py runner/run.sh
git commit -m "Add materialization and telegram delivery tools"
```

Expected: commit succeeds.

---

### Task 8: Add Samples, Documentation, and Weekly Path

**Files:**
- Create: `samples/weekday-digest.md`
- Create: `samples/weekly-digest.md`
- Create: `samples/run-report.json`
- Create: `docs/operations.md`
- Create: `docs/design.md`
- Modify: `runner/run.sh`
- Modify: `runner/tests/test_validate_runtime.py`

- [ ] **Step 1: Copy curated digest samples**

Run:

```bash
mkdir -p samples
cp digests/2026-05-04-daily-digest.md samples/weekday-digest.md
cp digests/2026-W17-weekly-digest.md samples/weekly-digest.md
```

If either source file is missing, use the newest tracked `*-daily-digest.md` and newest tracked `*-weekly-digest.md` from `digests/`.

- [ ] **Step 2: Create sample run report**

Create `samples/run-report.json`:

```json
{
  "run_id": "sample-weekday-2026-05-04",
  "job": "weekday",
  "status": "completed",
  "source_status": "completed",
  "article_status": "partial_success",
  "digest_status": "canonical_digest",
  "delivery_status": "dry_run",
  "artifacts": {
    "digest": "samples/weekday-digest.md",
    "brief": ".state/briefs/daily/2026-05-04__telegram_digest.json"
  }
}
```

- [ ] **Step 3: Create operations doc**

Create `docs/operations.md` with setup, server launch, validation, delivery,
full-text safety, and troubleshooting sections:

````md
# Operations

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r runner/requirements.txt
python3 -m playwright install chromium
```

Create `.env` from `.env.example`. Keep `.env` untracked.

## Self-Tests

```bash
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
python3 runner/tools/validate_runtime.py --check all
python3 -m pytest runner/tests
```

## Manual Runs

```bash
runner/run.sh weekday
runner/run.sh weekly
```

## Cron

```cron
0 9 * * 1-5 cd /opt/proptech-monitor && runner/run.sh weekday
0 17 * * 5 cd /opt/proptech-monitor && runner/run.sh weekly
```

## Full-Text Boundary

Full article text is fetched only by `runner/tools/fetch_articles.py`, only
after discovery writes a current-run shortlist. Discovery and weekly synthesis
must not read broad `.state/articles/` content.

## Delivery States

- `dry_run`: Telegram path was validated without sending.
- `not_configured`: required Telegram environment variables are missing.
- `delivered`: Telegram API accepted the message.
- `delivery_failed_http`: Telegram endpoint returned an HTTP transport error.
- `delivery_failed_api`: Telegram API returned an application-level error.
- `delivery_failed_unknown`: delivery failed outside known classes.

## Troubleshooting

1. Run `runner/run.sh --self-test weekday` and
   `runner/run.sh --self-test weekly`.
2. Run `python3 runner/tools/validate_runtime.py --check all`.
3. Check `.state/codex-runs/` for the latest run summaries.
4. If source fetching is partial, inspect the source summary before rerunning
   article fetch.
5. If Telegram delivery fails, rerun only delivery using the materialized digest
   path from the run report.
````

- [ ] **Step 4: Create design doc copy**

Run:

```bash
cp docs/superpowers/specs/2026-05-05-weekday-weekly-runtime-rebuild-design.md docs/design.md
```

- [ ] **Step 5: Wire weekly self-contained materialization**

Modify the weekly branch in `runner/run.sh` to:

```bash
WEEKLY_DRAFT="$RUN_ROOT/$RUN_ID-weekly-draft.json"
WEEKLY_DIGEST="$REPO_ROOT/.state/digests/$RUN_ID-weekly-digest.md"
DELIVERY_REPORT="$RUN_ROOT/$RUN_ID-delivery-report.json"

if [ ! -f "$WEEKLY_DRAFT" ]; then
  printf 'Weekly draft not found: %s\n' "$WEEKLY_DRAFT" >&2
  exit 22
fi

python3 "$MATERIALIZE" \
  --repo-root "$REPO_ROOT" \
  --draft-path "$WEEKLY_DRAFT" \
  --pretty > "$RUN_ROOT/$RUN_ID-weekly-materialize-summary.json"

python3 "$SEND_TELEGRAM" \
  --profile telegram_weekly_digest \
  --input "$WEEKLY_DIGEST" \
  --report-path "$DELIVERY_REPORT" > "$RUN_ROOT/$RUN_ID-send-stdout.json"

printf 'Weekly delivery report: %s\n' "$DELIVERY_REPORT"
```

- [ ] **Step 6: Run full validation including samples**

Run:

```bash
python3 runner/tools/validate_runtime.py --check samples
python3 runner/tools/validate_runtime.py --check docs
python3 runner/tools/validate_runtime.py --check all
python3 -m pytest runner/tests -q
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
```

Expected: PASS.

- [ ] **Step 7: Commit samples, docs, and weekly path**

Run:

```bash
git add samples docs/operations.md docs/design.md runner/run.sh runner/tests/test_validate_runtime.py
git commit -m "Add samples operations docs and weekly path"
```

Expected: commit succeeds.

---

### Task 9: Remove Legacy Runtime Surfaces

**Files:**
- Delete: `benchmark/`
- Delete: `prompts/`
- Delete: `cowork/`
- Delete: `config/runtime/`
- Delete: `ops/codex-cli/`
- Delete: `tools/`
- Delete: `.auto-memory/`
- Delete: `digests/`
- Review/Delete: old docs under `docs/plans/`, `docs/run-reviews/`, and obsolete root audits
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `.gitignore`
- Modify: `PLANS.md`

- [ ] **Step 1: Confirm new runtime checks pass before deletion**

Run:

```bash
python3 runner/tools/validate_runtime.py --check all
python3 -m pytest runner/tests -q
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
```

Expected: PASS.

- [ ] **Step 2: Remove legacy tracked directories**

Run:

```bash
git rm -r benchmark prompts cowork config/runtime ops/codex-cli tools .auto-memory digests
```

Expected: files are staged for deletion.

- [ ] **Step 3: Remove obsolete docs that describe old runtime surfaces**

Run:

```bash
git rm -r docs/plans docs/run-reviews
git rm docs/agent-spec.md docs/benchmark-design.md docs/cowork-onboarding.md docs/daily-digest-mechanism-review.md docs/launch-rerun-dry-run.md docs/llm-jtbd-analysis.md docs/mode-catalog.md docs/rss-api-audit.md docs/runner-live-scrape-test-report.md docs/runtime-architecture.md docs/codex-cli-server-launch.md
```

Expected: old human-history docs are staged for deletion. Keep `docs/design.md`, `docs/operations.md`, `docs/superpowers/specs/2026-05-05-weekday-weekly-runtime-rebuild-design.md`, and this implementation plan.

- [ ] **Step 4: Replace README**

Replace `README.md` with the compact operator entry point:

````md
# PropTech Monitor

Compact runtime for two server jobs:

- weekday daily digest
- weekly digest

## Run

```bash
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
runner/run.sh weekday
runner/run.sh weekly
```

## Runtime Source of Truth

- `runtime/manifest.yaml`
- `runtime/schedules.yaml`
- `runtime/sources/`
- `runtime/judgment/`
- `runtime/prompts/`
- `runtime/adapters/`
- `runtime/schemas/`

## Operations

See `docs/operations.md`.
````

- [ ] **Step 5: Replace AGENTS.md with compact repo rules**

Replace `AGENTS.md` with compact repo rules for future Codex work:

```md
# AGENTS.md

This repository is a compact runtime package for `weekday` and `weekly` PropTech
Monitor jobs.

Behavior changes include prompt, config, judgment, runner, source adapter,
schema, state, digest, delivery, and validation changes.

For substantial changes:

- update `PLANS.md` or the relevant plan under `docs/superpowers/plans/`;
- keep edits milestone-scoped;
- preserve server self-tests;
- run relevant validation before claiming completion.

Runtime source of truth:

- `runtime/`
- `runner/`
- `docs/operations.md`

Scheduled runs may write local artifacts under `.state/`. Scheduled runs must
not edit runtime source files. Persistent runtime fixes should be made through
git changes in this repository.

Full article text may be fetched only by `runner/tools/fetch_articles.py` after
discovery writes a current-run shortlist.
```

- [ ] **Step 6: Update `.gitignore`**

Replace `.gitignore` with:

```text
.DS_Store
.env
.state/
.state-*/
.venv/
__pycache__/
*.pyc
*.log
.idea/
.vscode/
```

- [ ] **Step 7: Update PLANS.md to only reference the active rebuild**

Replace `PLANS.md` with:

```md
# Active Plans Index

| Title | Status | Path | Notes |
| --- | --- | --- | --- |
| Weekday Weekly Runtime Rebuild | active | `docs/superpowers/plans/2026-05-05-weekday-weekly-runtime-rebuild.md` | Hard rebuild into compact `runtime/` + `runner/` package for weekday and weekly digest server jobs only. |
```

- [ ] **Step 8: Scan for forbidden old path references**

Run:

```bash
rg -n "cowork/|config/runtime/|ops/codex-cli|benchmark/|stakeholder_fanout|breaking_alert|telegram_alert|daily_core|weekly_context" .
```

Expected: no matches outside this plan and the approved design spec. If matches appear in runtime, runner, README, AGENTS, or operations docs, update those files to new terminology.

- [ ] **Step 9: Run validation after legacy deletion**

Run:

```bash
python3 runner/tools/validate_runtime.py --check all
python3 -m pytest runner/tests -q
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
```

Expected: PASS.

- [ ] **Step 10: Commit legacy removal**

Run:

```bash
git add README.md AGENTS.md .gitignore PLANS.md
git commit -m "Remove legacy runtime surfaces"
```

Expected: commit succeeds with large deletion diff and passing checks recorded in commit notes or final milestone report.

---

### Task 10: Completion Audit, Documentation Audit, and Final Verification

**Files:**
- Create/Replace: `COMPLETION_AUDIT.md`
- Modify: `PLANS.md`

- [ ] **Step 1: Write completion audit**

Replace `COMPLETION_AUDIT.md` with:

```md
# Completion Audit: Weekday Weekly Runtime Rebuild

## Original Requirements

- Keep only what is needed to run weekday and weekly digests through Codex.
- Preserve server/cron launch.
- Use the old repository as a prototype, but rebuild cleanly.
- Remove legacy previous runs and development artifacts.
- Keep one or two examples.
- Make hot filters configurable through a general industry filter and thematic rules.
- Add precise strategic relevance scoring for Avito Real Estate.
- Clarify where full text appears.

## Implemented Requirements

- `runtime/` is the new runtime source of truth.
- `runner/run.sh weekday` and `runner/run.sh weekly` are the only launch jobs.
- `runtime/judgment/industry_filter.yaml`, `discovery_rules.yaml`, and `scoring_profile.yaml` define filtering and scoring.
- Full text is fetched only through `runner/tools/fetch_articles.py` after shortlist.
- Server self-tests exist for weekday and weekly.
- Runtime validation exists in `runner/tools/validate_runtime.py`.
- Curated samples live under `samples/`.
- Legacy benchmark, old prompts, old runtime config, old ops wrapper, old tools, old digest archive, and old memory files were removed.

## Partially Implemented Requirements

- Live Telegram delivery depends on configured `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
- Live source quality depends on external source availability and Playwright browser installation.

## Missing Requirements

- None known at audit time.

## Verification

```bash
python3 runner/tools/validate_runtime.py --check all
python3 -m pytest runner/tests -q
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
```

## Compatibility Caveats

- Old `cowork/`, `config/runtime/`, `ops/codex-cli/`, root `tools/`, historical
  `digests/`, benchmark datasets, breaking alert, and stakeholder fanout paths
  are intentionally not preserved.
- Existing local `.state/` artifacts from old runs are not guaranteed to match
  the rebuilt schemas.
```

- [ ] **Step 2: Mark plan complete in PLANS.md**

Edit the row in `PLANS.md`:

```md
| Weekday Weekly Runtime Rebuild | completed | `docs/superpowers/plans/2026-05-05-weekday-weekly-runtime-rebuild.md` | Hard rebuild into compact `runtime/` + `runner/` package for weekday and weekly digest server jobs only. |
```

- [ ] **Step 3: Run final verification**

Run:

```bash
python3 runner/tools/validate_runtime.py --check docs
python3 runner/tools/validate_runtime.py --check all
python3 -m pytest runner/tests -q
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
git status --short
```

Expected:

- validation passes;
- documentation validation passes;
- tests pass;
- both self-tests pass;
- `git status --short` shows only `COMPLETION_AUDIT.md` and `PLANS.md` modified.

- [ ] **Step 4: Commit completion audit**

Run:

```bash
git add COMPLETION_AUDIT.md PLANS.md
git commit -m "Add rebuild completion audit"
```

Expected: commit succeeds.

---

## Self-Review Checklist

- Spec coverage: Tasks 2-10 cover target structure, server launch, judgment layer, full-text boundary, error handling, validation, samples, required documentation, legacy removal, and completion audit.
- Red-flag scan: the plan contains no open markers or unspecified file names.
- Type consistency: planned artifact names are stable: `weekday`, `weekly`, `industry_filter`, `discovery_rules`, `scoring_profile`, `article_prefetch`, `finish_draft`, `daily_brief`, `weekly_brief`, and `run_report`.
- Remaining implementation risk: Tasks 6 and 7 intentionally migrate existing helper code before reducing it. This keeps behavior reviewable while the path layout changes.
