# Minimum Refactor Dry-Run Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the refactored weekday/weekly runtime minimally runnable for offline dry-run readiness checks without completing the full hard rebuild.

**Architecture:** Add a compact `runtime/` contract and a thin `runner/run.sh` facade over the already working `ops/codex-cli/run_schedule.sh` wrapper. The minimum does not delete legacy paths; it proves the new entrypoint, config footprint, validation, and offline dry-run report are wired before any live Codex or Telegram execution.

**Tech Stack:** Bash, Python 3, PyYAML, pytest, existing `ops/codex-cli/run_schedule.sh` and existing root `tools/` helpers.

---

## Scope Boundary

This plan is intentionally smaller than `docs/superpowers/plans/2026-05-05-weekday-weekly-runtime-rebuild.md`.

The minimum dry-run-ready refactor means:

- `runner/run.sh --self-test weekday` passes offline.
- `runner/run.sh --self-test weekly` passes offline.
- `runner/run.sh --dry-run weekday` writes a local `offline_wiring_ready` report without live Codex, live source fetch, or Telegram send.
- `runner/run.sh --dry-run weekly` writes a local `offline_wiring_ready` report without live Codex, live source fetch, or Telegram send.
- `python3 runner/tools/validate_runtime.py --check all` passes.
- `python3 runner/tools/validate_runtime.py --check docs` passes after the operator docs milestone.
- `python3 -m pytest runner/tests -q` passes.
- The runtime footprint contains only weekday and weekly jobs; `breaking_alert` is not exposed through the new runner.

The minimum does not mean production cutover, live source quality, Telegram delivery, historical cleanup, or deletion of old runtime assets.

## File Structure

Create:

- `runtime/manifest.yaml` — compact runtime entrypoint listing supported jobs, schedules, source profiles, prompts, schemas, and validation expectations.
- `runtime/schedules.yaml` — weekday and weekly schedule bindings only.
- `runtime/sources/weekday.yaml` — copy/minimize the current `daily_core` source profile under the new refactor path.
- `runtime/sources/weekly.yaml` — copy/minimize the current weekly source profile under the new refactor path.
- `runtime/judgment/industry_filter.yaml` — small editable industry inclusion/exclusion contract.
- `runtime/judgment/discovery_rules.yaml` — small editable shortlist policy contract.
- `runtime/judgment/scoring_profile.yaml` — small editable Avito Real Estate scoring contract.
- `runtime/prompts/shared.md` — shared runtime constraints for the new runner.
- `runtime/prompts/weekday_discovery.md` — lightweight wrapper prompt that points to the existing weekday discovery behavior.
- `runtime/prompts/weekday_finish.md` — lightweight wrapper prompt that points to the existing weekday finish behavior.
- `runtime/prompts/weekly_digest.md` — lightweight wrapper prompt that points to the existing weekly behavior.
- `runtime/schemas/artifacts.yaml` — minimum schema notes for readiness reports and runner handoff artifacts.
- `runtime/schemas/state_layout.yaml` — minimum state layout contract for `.state/refactor-dry-runs/` and existing legacy handoff paths.
- `runner/requirements.txt` — runner-specific Python dependency list with `PyYAML`.
- `runner/run.sh` — new refactored entrypoint for `weekday` and `weekly`.
- `runner/tools/common.py` — shared path/YAML helpers for runner tools.
- `runner/tools/validate_runtime.py` — offline runtime validator.
- `runner/tests/test_validate_runtime.py` — validator tests.
- `runner/tests/test_runner_shell.py` — runner facade tests.
- `docs/operations.md` — minimum operator commands for self-test, offline dry-run, and live handoff.

Modify:

- `PLANS.md` — mark this minimum plan as active and keep the full hard rebuild as separate planned work.
- `COMPLETION_AUDIT.md` — add a current audit section for minimum dry-run readiness only after verification passes.

Do not modify in this plan:

- `ops/codex-cli/run_schedule.sh`
- existing `tools/*.py`
- existing `config/runtime/**`
- existing `cowork/**`
- historical `digests/**`
- benchmark datasets

## Milestones

| Milestone | Goal | Scope | Dependencies | Risks | Acceptance criteria | Verification | Non-goals |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MDR-M0 | Protect the existing dirty worktree before implementation | Inspect `git status --short`; classify unrelated dirty files; record what must not be staged or committed | Current branch state | Existing benchmark/digest artifacts can be accidentally swept into commits | Implementer has an explicit do-not-stage list before editing; milestone reports include dirty worktree caveat | `git status --short`; `git diff --name-only`; manual staging review before every commit | No cleanup or revert of unrelated files |
| MDR-M1 | Create the compact runtime skeleton and validator | Add `runtime/**`, `runner/tools/common.py`, `runner/tools/validate_runtime.py`, validator tests, and `runner/requirements.txt` | Existing `config/runtime/schedule_bindings.yaml`, `config/runtime/source-groups/*`, and current plan/spec requirements | Validator can become too broad; copied source profile can drift from legacy source groups | `runtime/manifest.yaml` exists; schedules expose only `weekday` and `weekly`; all manifest paths exist; validator rejects `breaking_alert`; `python3 runner/tools/validate_runtime.py --check all` passes | `python3 -m pytest runner/tests/test_validate_runtime.py -q`; `python3 runner/tools/validate_runtime.py --check all` | No live source fetch; no prompt behavior rewrite; no deletion of old runtime paths |
| MDR-M2 | Add the refactored runner facade and offline dry-run report | Add `runner/run.sh` and shell tests; map `weekday` to `weekday_digest` and `weekly` to `weekly_digest`; support `--self-test` and `--dry-run` | MDR-M1; existing `ops/codex-cli/run_schedule.sh` self-test mode | A facade may look like full cutover even though it delegates to legacy wrapper; dry-run could accidentally call live Codex | `runner/run.sh --self-test weekday` and weekly pass; `runner/run.sh --dry-run weekday` and weekly write `.state/refactor-dry-runs/*.json`; `breaking_alert` is rejected; dry-run does not invoke live Codex or Telegram | `python3 -m pytest runner/tests/test_runner_shell.py -q`; `runner/run.sh --self-test weekday`; `runner/run.sh --self-test weekly`; `runner/run.sh --dry-run weekday`; `runner/run.sh --dry-run weekly` | No production cron change; no live Telegram delivery; no full weekly synthesis redesign |
| MDR-M3 | Add operator docs and completion audit for the minimum | Add `docs/operations.md`; update `PLANS.md`; update `COMPLETION_AUDIT.md` after checks pass | MDR-M1, MDR-M2 | Documentation could overclaim full rebuild readiness; dirty worktree artifacts could hide review scope | Docs clearly distinguish minimum dry-run readiness from full refactor completion; audit lists implemented, partial, missing, and follow-up requirements; final status is evidence-based | `python3 runner/tools/validate_runtime.py --check docs`; `git diff --check`; full command set from final verification | No claim that full hard rebuild is complete; no cleanup of unrelated benchmark/digest artifacts |

## Coverage Matrix

| Requirement | Milestone |
| --- | --- |
| Avoid staging unrelated dirty benchmark/digest artifacts | MDR-M0 |
| Provide a runnable refactored entrypoint | MDR-M2 |
| Keep only weekday and weekly exposed in new runner | MDR-M1, MDR-M2 |
| Make dry-run possible before live execution | MDR-M2 |
| Avoid live Codex, live source fetch, and Telegram in offline dry-run | MDR-M2 |
| Add compact runtime footprint under `runtime/` | MDR-M1 |
| Validate that runtime paths and contracts exist | MDR-M1 |
| Preserve current working wrapper behavior instead of rewriting all internals | MDR-M2 |
| Document operator commands and boundaries | MDR-M3 |
| Do not claim full rebuild/cutover | MDR-M3 |
| Keep legacy files untouched during the minimum | MDR-M1, MDR-M2, MDR-M3 |

## Current Milestone Acceptance Criteria

Current implementation should start with MDR-M0 preflight, then MDR-M1 only.

- Dirty worktree state is recorded before implementation.
- Unrelated existing changes are explicitly excluded from staging and commits.
- `runtime/manifest.yaml`, `runtime/schedules.yaml`, source profiles, judgment files, prompts, and schemas are created.
- `runner/tools/validate_runtime.py` supports `--check config`, `--check prompts`, `--check schemas`, `--check docs`, and `--check all`.
- During MDR-M1, `--check all` means runtime artifact checks only: config, prompts, and schemas. Docs are checked separately in MDR-M3 with `--check docs`.
- `runner/tests/test_validate_runtime.py` covers pass and fail cases.
- No `runner/run.sh` work is started until MDR-M1 is complete.
- `PLANS.md` remains the active-plan index and records that this is a minimum readiness plan, not the full rebuild.

## Task 0: Worktree Preflight

**Files:**

- No files are created or modified in this task.

- [ ] **Step 1: Inspect dirty state**

Run:

```bash
git status --short
git diff --name-only
```

Expected: record the existing unrelated dirty files before implementation. At the time this plan was written, known unrelated files included benchmark request-retrieval artifacts and generated digest files; do not assume the list is still identical.

- [ ] **Step 2: Record do-not-stage paths in the milestone report**

The milestone report must include a short list like:

```text
Do not stage during MDR work:
- benchmark/datasets/request-article-retrieval/inputs.jsonl
- benchmark/datasets/request-article-retrieval/avito-*
- benchmark/datasets/request-article-retrieval/inputs.fulltext.*
- benchmark/datasets/request-article-synthesis/request-article-synthesis.zip
- digests/2026-05-*-daily-digest.md
```

If any of these files are intentionally needed for MDR work, stop and update this plan before staging them.

- [ ] **Step 3: Use path-limited staging only**

For every commit in this plan, stage only the paths listed in that task's commit command. Do not use `git add .`.

## Task 1: Runtime Skeleton And Validator

**Files:**

- Create: `runtime/manifest.yaml`
- Create: `runtime/schedules.yaml`
- Create: `runtime/sources/weekday.yaml`
- Create: `runtime/sources/weekly.yaml`
- Create: `runtime/judgment/industry_filter.yaml`
- Create: `runtime/judgment/discovery_rules.yaml`
- Create: `runtime/judgment/scoring_profile.yaml`
- Create: `runtime/prompts/shared.md`
- Create: `runtime/prompts/weekday_discovery.md`
- Create: `runtime/prompts/weekday_finish.md`
- Create: `runtime/prompts/weekly_digest.md`
- Create: `runtime/schemas/artifacts.yaml`
- Create: `runtime/schemas/state_layout.yaml`
- Create: `runner/requirements.txt`
- Create: `runner/tools/common.py`
- Create: `runner/tools/validate_runtime.py`
- Create: `runner/tests/test_validate_runtime.py`

- [ ] **Step 1: Write failing validator tests**

Create `runner/tests/test_validate_runtime.py`:

```python
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
VALIDATOR = REPO_ROOT / "runner/tools/validate_runtime.py"


def run_validator(*args: str, cwd: pathlib.Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_validator_all_passes_for_minimum_runtime() -> None:
    result = run_validator("--check", "all")

    assert result.returncode == 0, result.stderr
    assert "PASS all" in result.stdout


def test_validator_rejects_breaking_alert_in_new_schedule() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        (root / "runtime").mkdir()
        (root / "runtime/manifest.yaml").write_text("jobs: {}\n", encoding="utf-8")
        (root / "runtime/schedules.yaml").write_text(
            "jobs:\n"
            "  weekday:\n"
            "    legacy_schedule_id: weekday_digest\n"
            "  weekly:\n"
            "    legacy_schedule_id: weekly_digest\n"
            "  breaking_alert:\n"
            "    legacy_schedule_id: breaking_alert\n",
            encoding="utf-8",
        )

        result = run_validator("--check", "config", "--repo-root", str(root))

    assert result.returncode != 0
    assert "unsupported job exposed: breaking_alert" in result.stderr


def test_validator_rejects_missing_manifest_paths() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        (root / "runtime").mkdir()
        (root / "runtime/prompts").mkdir()
        (root / "runtime/sources").mkdir()
        (root / "ops/codex-cli").mkdir(parents=True)
        (root / "runtime/prompts/shared.md").write_text("shared runtime\n", encoding="utf-8")
        (root / "runtime/prompts/weekly_digest.md").write_text("weekly runtime\n", encoding="utf-8")
        (root / "runtime/sources/weekday.yaml").write_text("sources: []\n", encoding="utf-8")
        (root / "runtime/sources/weekly.yaml").write_text("sources: []\n", encoding="utf-8")
        (root / "ops/codex-cli/run_schedule.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        (root / "runtime/manifest.yaml").write_text(
            "jobs:\n"
            "  weekday:\n"
            "    schedule: runtime/schedules.yaml\n"
            "    source_profile: runtime/sources/weekday.yaml\n"
            "    shared_prompt: runtime/prompts/shared.md\n"
            "    prompt: runtime/prompts/missing.md\n"
            "    legacy_wrapper: ops/codex-cli/run_schedule.sh\n"
            "  weekly:\n"
            "    schedule: runtime/schedules.yaml\n"
            "    source_profile: runtime/sources/weekly.yaml\n"
            "    shared_prompt: runtime/prompts/shared.md\n"
            "    prompt: runtime/prompts/weekly_digest.md\n"
            "    legacy_wrapper: ops/codex-cli/run_schedule.sh\n",
            encoding="utf-8",
        )
        (root / "runtime/schedules.yaml").write_text(
            "jobs:\n"
            "  weekday:\n"
            "    legacy_schedule_id: weekday_digest\n"
            "    source_profile: runtime/sources/weekday.yaml\n"
            "  weekly:\n"
            "    legacy_schedule_id: weekly_digest\n"
            "    source_profile: runtime/sources/weekly.yaml\n",
            encoding="utf-8",
        )

        result = run_validator("--check", "config", "--repo-root", str(root))

    assert result.returncode != 0
    assert "missing manifest path" in result.stderr


def test_validator_rejects_weekday_source_profile_drift() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        (root / "runtime").mkdir()
        (root / "runtime/prompts").mkdir()
        (root / "runtime/sources").mkdir()
        (root / "ops/codex-cli").mkdir(parents=True)
        for prompt in ("shared.md", "weekday_discovery.md", "weekly_digest.md"):
            (root / "runtime/prompts" / prompt).write_text("runtime prompt\n", encoding="utf-8")
        (root / "ops/codex-cli/run_schedule.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        (root / "runtime/manifest.yaml").write_text(
            "jobs:\n"
            "  weekday:\n"
            "    schedule: runtime/schedules.yaml\n"
            "    source_profile: runtime/sources/weekday.yaml\n"
            "    shared_prompt: runtime/prompts/shared.md\n"
            "    prompt: runtime/prompts/weekday_discovery.md\n"
            "    legacy_wrapper: ops/codex-cli/run_schedule.sh\n"
            "  weekly:\n"
            "    schedule: runtime/schedules.yaml\n"
            "    source_profile: runtime/sources/weekly.yaml\n"
            "    shared_prompt: runtime/prompts/shared.md\n"
            "    prompt: runtime/prompts/weekly_digest.md\n"
            "    legacy_wrapper: ops/codex-cli/run_schedule.sh\n",
            encoding="utf-8",
        )
        (root / "runtime/schedules.yaml").write_text(
            "jobs:\n"
            "  weekday:\n"
            "    legacy_schedule_id: weekday_digest\n"
            "    source_profile: runtime/sources/weekday.yaml\n"
            "  weekly:\n"
            "    legacy_schedule_id: weekly_digest\n"
            "    source_profile: runtime/sources/weekly.yaml\n",
            encoding="utf-8",
        )
        (root / "runtime/sources/weekday.yaml").write_text(
            "sources:\n"
            "  - id: aim_group_real_estate_intelligence\n",
            encoding="utf-8",
        )
        (root / "runtime/sources/weekly.yaml").write_text("sources: []\n", encoding="utf-8")

        result = run_validator("--check", "config", "--repo-root", str(root))

    assert result.returncode != 0
    assert "weekday source profile missing source_id" in result.stderr
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python3 -m pytest runner/tests/test_validate_runtime.py -q
```

Expected: FAIL because `runner/tools/validate_runtime.py` and the minimum runtime files do not exist.

- [ ] **Step 3: Add minimum runtime files**

Create `runtime/schedules.yaml`:

```yaml
jobs:
  weekday:
    enabled: true
    legacy_schedule_id: weekday_digest
    days: [MON, TUE, WED, THU, FRI]
    time: "09:00"
    source_profile: runtime/sources/weekday.yaml
    delivery_profile: telegram_digest
    dry_run_report_dir: .state/refactor-dry-runs
  weekly:
    enabled: true
    legacy_schedule_id: weekly_digest
    days: [FRI]
    time: "17:00"
    source_profile: runtime/sources/weekly.yaml
    delivery_profile: telegram_weekly_digest
    dry_run_report_dir: .state/refactor-dry-runs
delivery_profiles:
  telegram_digest:
    mode: dry_run_safe
    legacy_profile: telegram_digest
  telegram_weekly_digest:
    mode: dry_run_safe
    legacy_profile: telegram_weekly_digest
```

Create `runtime/manifest.yaml`:

```yaml
schema_version: 1
supported_jobs: [weekday, weekly]
jobs:
  weekday:
    schedule: runtime/schedules.yaml
    source_profile: runtime/sources/weekday.yaml
    shared_prompt: runtime/prompts/shared.md
    prompt: runtime/prompts/weekday_discovery.md
    finish_prompt: runtime/prompts/weekday_finish.md
    legacy_wrapper: ops/codex-cli/run_schedule.sh
    legacy_schedule_id: weekday_digest
  weekly:
    schedule: runtime/schedules.yaml
    source_profile: runtime/sources/weekly.yaml
    shared_prompt: runtime/prompts/shared.md
    prompt: runtime/prompts/weekly_digest.md
    legacy_wrapper: ops/codex-cli/run_schedule.sh
    legacy_schedule_id: weekly_digest
judgment:
  industry_filter: runtime/judgment/industry_filter.yaml
  discovery_rules: runtime/judgment/discovery_rules.yaml
  scoring_profile: runtime/judgment/scoring_profile.yaml
schemas:
  artifacts: runtime/schemas/artifacts.yaml
  state_layout: runtime/schemas/state_layout.yaml
validation:
  required_checks: [config, prompts, schemas]
```

Create `runtime/sources/weekday.yaml` by copying the current source IDs from `config/runtime/source-groups/daily_core.yaml` and preserving each `id`, `source_name`, `fetch_strategy`, `rss_feed` when present, `itunes_api_url` when present, and `landing_urls`.

The weekday profile must include exactly these source IDs unless `config/runtime/source-groups/daily_core.yaml` has intentionally changed and this plan is updated first:

```text
aim_group_real_estate_intelligence
onlinemarketplaces
mike_delprete
zillow_newsroom
costar_homes
redfin_news
rea_group_media_releases
inman_tech_innovation
rightmove_plc
similarweb_global_real_estate
```

Create `runtime/sources/weekly.yaml` by combining the current source IDs from `config/runtime/source-groups/daily_core.yaml` and `config/runtime/source-groups/weekly_context.yaml`, preserving the same fields.

The weekly profile must include all weekday source IDs plus exactly these weekly-context source IDs:

```text
property_portal_watch
similarweb_country_real_estate
zillow_ios
zillow_android
rightmove_ios
rightmove_android
```

Create `runtime/judgment/industry_filter.yaml`:

```yaml
schema_version: 1
profile: real_estate_marketplaces
include_when:
  - real_estate_marketplace
  - property_portal
  - rental_marketplace
  - listing_supply
  - real_estate_ai_search
exclude_when_only:
  - automotive_marketplace
  - jobs_marketplace
  - travel_marketplace
  - ecommerce
  - retail_media
decision_labels:
  accept: accept_industry
  reject: reject_not_industry
```

Create `runtime/judgment/discovery_rules.yaml`:

```yaml
schema_version: 1
shortlist_bounds:
  weekday_max_items: 12
  weekly_max_items: 20
decisions: [shortlist, reject, maybe_weekly]
priority_labels: [high, medium, low]
shortlist_topics:
  - portal_competition
  - monetization
  - seller_or_landlord_supply
  - renter_or_buyer_journey
  - ai_search_or_matching
  - lead_quality
required_output_fields:
  - triage_decision
  - provisional_priority
  - industry_filter
  - matched_topics
  - shortlist_reason
```

Create `runtime/judgment/scoring_profile.yaml`:

```yaml
schema_version: 1
score_range: [0, 100]
dimensions:
  strategic_relevance: 40
  market_impact: 20
  novelty: 15
  evidence_quality: 15
  urgency: 10
selection_bands:
  must_cover: [90, 100]
  strong_daily_candidate: [75, 89]
  weekly_context_candidate: [60, 74]
  reject_or_log_only: [0, 59]
evidence_caps:
  snippet_fallback_max_score: 74
  paywall_stub_max_score: 60
```

Create the prompt files with compact text:

```md
# Shared Runtime Rules

Use `runtime/` as the refactored runtime contract. Full article text may appear only after shortlist through the article-fetch stage. The minimum dry-run path validates wiring and does not claim live source or delivery success.
```

```md
# Weekday Discovery Prompt

Use the existing weekday discovery behavior from `ops/codex-cli/prompts/weekday_digest_discovery.md`. Apply `runtime/judgment/industry_filter.yaml` before `runtime/judgment/discovery_rules.yaml`.
```

```md
# Weekday Finish Prompt

Use the existing weekday finish behavior from `ops/codex-cli/prompts/weekday_digest_finish.md`. Apply `runtime/judgment/scoring_profile.yaml` after article prefetch evidence is available.
```

```md
# Weekly Digest Prompt

Use the existing weekly behavior from `ops/codex-cli/prompts/weekly_digest.md`. Synthesize week and month context rather than ranking daily items only by score.
```

Create `runtime/schemas/artifacts.yaml`:

```yaml
schema_version: 1
dry_run_report:
  required_fields:
    - schema_version
    - run_id
    - job
    - status
    - runtime_manifest
    - legacy_wrapper
    - legacy_schedule_id
    - live_codex_invoked
    - live_source_fetch_invoked
    - telegram_invoked
    - runtime_prompts_consumed_by_live_run
```

Create `runtime/schemas/state_layout.yaml`:

```yaml
schema_version: 1
paths:
  dry_run_reports: .state/refactor-dry-runs
  legacy_codex_runs: .state/codex-runs
  legacy_shortlists: .state/shortlists
compatibility:
  old_state_readers_preserved: true
  new_dry_run_reports_are_additive: true
```

Create `runner/requirements.txt`:

```text
PyYAML>=6,<7
pytest>=8,<9
```

- [ ] **Step 4: Add validator implementation**

Create `runner/tools/common.py`:

```python
from __future__ import annotations

import pathlib
from typing import Any

import yaml


def repo_root_from(path: str | None) -> pathlib.Path:
    if path:
        return pathlib.Path(path).resolve()
    return pathlib.Path(__file__).resolve().parents[2]


def read_yaml(path: pathlib.Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be an object: {path}")
    return data
```

Create `runner/tools/validate_runtime.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any

from common import read_yaml, repo_root_from


SUPPORTED_CHECKS = {"config", "prompts", "schemas", "docs", "all"}
SUPPORTED_JOBS = {"weekday", "weekly"}
EXPECTED_WEEKDAY_SOURCES = {
    "aim_group_real_estate_intelligence",
    "onlinemarketplaces",
    "mike_delprete",
    "zillow_newsroom",
    "costar_homes",
    "redfin_news",
    "rea_group_media_releases",
    "inman_tech_innovation",
    "rightmove_plc",
    "similarweb_global_real_estate",
}
EXPECTED_WEEKLY_EXTRA_SOURCES = {
    "property_portal_watch",
    "similarweb_country_real_estate",
    "zillow_ios",
    "zillow_android",
    "rightmove_ios",
    "rightmove_android",
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def rel_path(repo_root: pathlib.Path, value: str) -> pathlib.Path:
    path = pathlib.Path(value)
    return path if path.is_absolute() else repo_root / path


def require_path(repo_root: pathlib.Path, value: str, label: str) -> None:
    path = rel_path(repo_root, value)
    if not path.exists():
        fail(f"missing {label}: {value}")


def load_manifest(repo_root: pathlib.Path) -> dict[str, Any]:
    manifest_path = repo_root / "runtime/manifest.yaml"
    if not manifest_path.exists():
        fail("missing runtime manifest: runtime/manifest.yaml")
    return read_yaml(manifest_path)


def source_ids(path: pathlib.Path) -> set[str]:
    payload = read_yaml(path)
    sources = payload.get("sources")
    if not isinstance(sources, list):
        fail(f"source profile must contain sources list: {path}")
    ids: set[str] = set()
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("id"), str):
            fail(f"source profile contains source without id: {path}")
        ids.add(source["id"])
    return ids


def validate_source_profile(repo_root: pathlib.Path, label: str, value: str, expected: set[str]) -> None:
    path = rel_path(repo_root, value)
    require_path(repo_root, value, "source profile")
    actual = source_ids(path)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        fail(f"{label} source profile missing source_id: {missing[0]}")
    if extra:
        fail(f"{label} source profile has unexpected source_id: {extra[0]}")


def check_config(repo_root: pathlib.Path) -> None:
    manifest = load_manifest(repo_root)
    schedules_path = repo_root / "runtime/schedules.yaml"
    if not schedules_path.exists():
        fail("missing runtime schedules: runtime/schedules.yaml")
    schedules = read_yaml(schedules_path)
    jobs = schedules.get("jobs")
    if not isinstance(jobs, dict):
        fail("runtime/schedules.yaml must contain jobs mapping")
    exposed = set(jobs)
    unsupported = sorted(exposed - SUPPORTED_JOBS)
    if unsupported:
        fail(f"unsupported job exposed: {unsupported[0]}")
    if exposed != SUPPORTED_JOBS:
        fail("runtime/schedules.yaml must expose exactly weekday and weekly")
    for job, expected_legacy in {"weekday": "weekday_digest", "weekly": "weekly_digest"}.items():
        legacy = jobs[job].get("legacy_schedule_id") if isinstance(jobs[job], dict) else None
        if legacy != expected_legacy:
            fail(f"{job} legacy_schedule_id must be {expected_legacy}")
        source_profile = jobs[job].get("source_profile") if isinstance(jobs[job], dict) else None
        if not isinstance(source_profile, str) or not source_profile:
            fail(f"{job} source_profile is required")
    manifest_jobs = manifest.get("jobs")
    if not isinstance(manifest_jobs, dict):
        fail("runtime/manifest.yaml must contain jobs mapping")
    if set(manifest_jobs) != SUPPORTED_JOBS:
        fail("runtime/manifest.yaml must expose exactly weekday and weekly")
    for job, config in manifest_jobs.items():
        if not isinstance(config, dict):
            fail(f"manifest job must be object: {job}")
        for key in ("schedule", "source_profile", "shared_prompt", "prompt", "legacy_wrapper"):
            value = config.get(key)
            if not isinstance(value, str) or not value:
                fail(f"manifest job {job} missing {key}")
            require_path(repo_root, value, "manifest path")
        finish_prompt = config.get("finish_prompt")
        if isinstance(finish_prompt, str):
            require_path(repo_root, finish_prompt, "manifest path")
    for job in ("weekday", "weekly"):
        source_profile = jobs[job]["source_profile"]
        expected_sources = EXPECTED_WEEKDAY_SOURCES
        if job == "weekly":
            expected_sources = EXPECTED_WEEKDAY_SOURCES | EXPECTED_WEEKLY_EXTRA_SOURCES
        validate_source_profile(repo_root, job, source_profile, expected_sources)


def check_prompts(repo_root: pathlib.Path) -> None:
    manifest = load_manifest(repo_root)
    for value in manifest.get("judgment", {}).values():
        if isinstance(value, str):
            require_path(repo_root, value, "judgment path")
    prompts = [
        "runtime/prompts/shared.md",
        "runtime/prompts/weekday_discovery.md",
        "runtime/prompts/weekday_finish.md",
        "runtime/prompts/weekly_digest.md",
    ]
    for prompt in prompts:
        require_path(repo_root, prompt, "prompt")
        text = rel_path(repo_root, prompt).read_text(encoding="utf-8")
        if "runtime/" not in text and "existing" not in text.lower():
            fail(f"prompt lacks runtime context: {prompt}")


def check_schemas(repo_root: pathlib.Path) -> None:
    manifest = load_manifest(repo_root)
    schemas = manifest.get("schemas")
    if not isinstance(schemas, dict):
        fail("runtime/manifest.yaml must contain schemas mapping")
    for value in schemas.values():
        if isinstance(value, str):
            require_path(repo_root, value, "schema path")


def check_docs(repo_root: pathlib.Path) -> None:
    operations = repo_root / "docs/operations.md"
    if not operations.exists():
        fail("missing docs/operations.md")
    text = operations.read_text(encoding="utf-8")
    for needle in (
        "runner/run.sh --self-test weekday",
        "runner/run.sh --dry-run weekday",
        "minimum dry-run readiness",
    ):
        if needle not in text:
            fail(f"docs/operations.md missing: {needle}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate minimum refactored runtime")
    parser.add_argument("--check", choices=sorted(SUPPORTED_CHECKS), default="all")
    parser.add_argument("--repo-root")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = repo_root_from(args.repo_root)
    checks = ["config", "prompts", "schemas"] if args.check == "all" else [args.check]
    try:
        for check in checks:
            if check == "config":
                check_config(repo_root)
            elif check == "prompts":
                check_prompts(repo_root)
            elif check == "schemas":
                check_schemas(repo_root)
            elif check == "docs":
                check_docs(repo_root)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"PASS {args.check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run MDR-M1 verification**

Run:

```bash
python3 -m pytest runner/tests/test_validate_runtime.py -q
python3 runner/tools/validate_runtime.py --check all
git diff --check
```

Expected: all pass.

- [ ] **Step 6: Commit MDR-M1**

Run:

```bash
git add runtime runner/requirements.txt runner/tools/common.py runner/tools/validate_runtime.py runner/tests/test_validate_runtime.py
git commit -m "Add minimum refactor runtime validator"
```

## Task 2: Runner Facade And Offline Dry-Run

**Files:**

- Create: `runner/run.sh`
- Create: `runner/tests/test_runner_shell.py`

- [ ] **Step 1: Write failing runner tests**

Create `runner/tests/test_runner_shell.py`:

```python
from __future__ import annotations

import json
import os
import pathlib
import subprocess


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "runner/run.sh"


def run_runner(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CODEX_BIN"] = "false"
    return subprocess.run(
        ["bash", str(RUNNER), *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_self_test_weekday_passes_without_live_codex() -> None:
    result = run_runner("--self-test", "weekday")

    assert result.returncode == 0, result.stderr
    assert "Refactor runner self-test passed: weekday" in result.stdout
    assert "legacy schedule: weekday_digest" in result.stdout


def test_self_test_weekly_passes_without_live_codex() -> None:
    result = run_runner("--self-test", "weekly")

    assert result.returncode == 0, result.stderr
    assert "Refactor runner self-test passed: weekly" in result.stdout
    assert "legacy schedule: weekly_digest" in result.stdout


def test_breaking_alert_is_not_supported() -> None:
    result = run_runner("--self-test", "breaking_alert")

    assert result.returncode == 2
    assert "Supported jobs: weekday, weekly" in result.stderr


def test_dry_run_writes_readiness_report_without_live_invocation() -> None:
    result = run_runner("--dry-run", "weekday")

    assert result.returncode == 0, result.stderr
    report_line = next(line for line in result.stdout.splitlines() if line.startswith("Dry-run report: "))
    report_path = REPO_ROOT / report_line.split(": ", 1)[1]
    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert payload["job"] == "weekday"
    assert payload["status"] == "offline_wiring_ready"
    assert payload["legacy_schedule_id"] == "weekday_digest"
    assert payload["live_codex_invoked"] is False
    assert payload["live_source_fetch_invoked"] is False
    assert payload["telegram_invoked"] is False
    assert payload["runtime_prompts_consumed_by_live_run"] is False
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
python3 -m pytest runner/tests/test_runner_shell.py -q
```

Expected: FAIL because `runner/run.sh` does not exist.

- [ ] **Step 3: Add runner facade**

Create `runner/run.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s [--self-test|--dry-run] {weekday|weekly}\n' "$0" >&2
  printf 'Supported jobs: weekday, weekly\n' >&2
}

MODE="run"
if [ "${1:-}" = "--self-test" ] || [ "${1:-}" = "--dry-run" ]; then
  MODE="${1#--}"
  shift
fi

if [ "$#" -ne 1 ]; then
  usage
  exit 2
fi

JOB="$1"
case "$JOB" in
  weekday)
    LEGACY_SCHEDULE_ID="weekday_digest"
    ;;
  weekly)
    LEGACY_SCHEDULE_ID="weekly_digest"
    ;;
  *)
    usage
    exit 2
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST="$REPO_ROOT/runtime/manifest.yaml"
VALIDATOR="$REPO_ROOT/runner/tools/validate_runtime.py"
LEGACY_WRAPPER="$REPO_ROOT/ops/codex-cli/run_schedule.sh"
DRY_RUN_DIR="$REPO_ROOT/.state/refactor-dry-runs"

python3 "$VALIDATOR" --check all --repo-root "$REPO_ROOT" >/dev/null

if [ "$MODE" = "self-test" ]; then
  CODEX_RUN_SCHEDULE_SELF_TEST=1 "$LEGACY_WRAPPER" "$LEGACY_SCHEDULE_ID" >/dev/null
  printf 'Refactor runner self-test passed: %s\n' "$JOB"
  printf 'runtime manifest: %s\n' "$MANIFEST"
  printf 'legacy wrapper: %s\n' "$LEGACY_WRAPPER"
  printf 'legacy schedule: %s\n' "$LEGACY_SCHEDULE_ID"
  exit 0
fi

if [ "$MODE" = "dry-run" ]; then
  mkdir -p "$DRY_RUN_DIR"
  RUN_ID="$(date -u '+%Y%m%dT%H%M%SZ')-$JOB-dry-run"
  REPORT="$DRY_RUN_DIR/$RUN_ID.json"
  CODEX_RUN_SCHEDULE_SELF_TEST=1 "$LEGACY_WRAPPER" "$LEGACY_SCHEDULE_ID" >/dev/null
  python3 - "$REPORT" "$RUN_ID" "$JOB" "$LEGACY_SCHEDULE_ID" <<'PY'
import json
import pathlib
import sys
from datetime import datetime, timezone

report, run_id, job, legacy_schedule_id = sys.argv[1:5]
payload = {
    "schema_version": 1,
    "run_id": run_id,
    "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "job": job,
    "status": "offline_wiring_ready",
    "runtime_manifest": "runtime/manifest.yaml",
    "legacy_wrapper": "ops/codex-cli/run_schedule.sh",
    "legacy_schedule_id": legacy_schedule_id,
    "live_codex_invoked": False,
    "live_source_fetch_invoked": False,
    "telegram_invoked": False,
    "runtime_prompts_consumed_by_live_run": False,
}
path = pathlib.Path(report)
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
  printf 'Refactor runner dry-run passed: %s\n' "$JOB"
  printf 'Dry-run report: %s\n' "${REPORT#$REPO_ROOT/}"
  exit 0
fi

exec "$LEGACY_WRAPPER" "$LEGACY_SCHEDULE_ID"
```

- [ ] **Step 4: Make runner executable**

Run:

```bash
chmod +x runner/run.sh
```

- [ ] **Step 5: Run MDR-M2 verification**

Run:

```bash
python3 -m pytest runner/tests/test_runner_shell.py -q
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
runner/run.sh --dry-run weekday
runner/run.sh --dry-run weekly
```

Expected: all pass; dry-run reports appear under `.state/refactor-dry-runs/`.

- [ ] **Step 6: Commit MDR-M2**

Run:

```bash
git add runner/run.sh runner/tests/test_runner_shell.py
git commit -m "Add minimum refactor runner dry-run"
```

Do not commit generated dry-run JSON reports. `.state/` is ignored and reports under `.state/refactor-dry-runs/` are local verification artifacts only.

## Task 3: Operator Docs And Minimum Audit

**Files:**

- Modify: `PLANS.md`
- Modify: `COMPLETION_AUDIT.md`
- Create: `docs/operations.md`

- [ ] **Step 1: Add operations doc**

Create `docs/operations.md`:

```md
# Operations

This document covers minimum dry-run readiness for the refactored weekday and weekly runner. It does not claim full runtime rebuild completion or production cutover.

## Offline Self-Tests

```bash
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
python3 runner/tools/validate_runtime.py --check all
python3 -m pytest runner/tests -q
```

## Offline Dry-Run

```bash
runner/run.sh --dry-run weekday
runner/run.sh --dry-run weekly
```

The offline dry-run validates runtime wiring and writes a local `offline_wiring_ready` report under `.state/refactor-dry-runs/`. It does not invoke live Codex, live source fetches, or Telegram delivery. In the minimum facade, the new `runtime/prompts/` files are validated as contracts but live runs still delegate to the existing legacy prompt wrapper.

## Live Handoff

```bash
runner/run.sh weekday
runner/run.sh weekly
```

The live commands delegate to the existing `ops/codex-cli/run_schedule.sh` wrapper using `weekday_digest` and `weekly_digest`. Use live commands only after offline self-tests and dry-runs pass.

## Boundaries

- New runner supports only `weekday` and `weekly`.
- `breaking_alert` remains out of scope for the refactored runner.
- Legacy `config/runtime/`, `cowork/`, `tools/`, and `ops/codex-cli/` remain in place for this minimum.
- `runtime_prompts_consumed_by_live_run` is expected to be `false` in offline reports until the full runtime migration replaces legacy prompt consumption.
- Full hard rebuild cleanup remains separate planned work.
```

- [ ] **Step 2: Update `PLANS.md`**

Before implementation starts, the active-plan row should read:

```md
| Minimum Refactor Dry-Run Readiness | active; MDR-M1 next | `docs/superpowers/plans/2026-05-14-minimum-refactor-dry-run-readiness.md` | Minimal `runtime/` + `runner/run.sh` facade that proves weekday/weekly self-tests and offline dry-run readiness without completing the full hard rebuild. |
```

After MDR-M3 verification passes, update the same row to:

```md
| Minimum Refactor Dry-Run Readiness | completed minimum; full rebuild still planned | `docs/superpowers/plans/2026-05-14-minimum-refactor-dry-run-readiness.md` | Minimal `runtime/` + `runner/run.sh` facade proves weekday/weekly self-tests and offline dry-run readiness without completing the full hard rebuild. |
```

Keep `Weekday Weekly Runtime Rebuild` as planned unless the full rebuild is separately implemented.

- [ ] **Step 3: Update `COMPLETION_AUDIT.md` after verification passes**

Prepend this section:

```md
## Current Audit: Minimum Refactor Dry-Run Readiness

Audit date: 2026-05-14

Scope: minimum offline readiness for the refactored weekday/weekly entrypoint. This audit does not claim full hard rebuild completion, production cutover, live source quality, or Telegram delivery.

### Implemented

- `runtime/` contains the minimum manifest, schedules, source profiles, judgment files, prompts, and schemas.
- `runner/run.sh` exposes only `weekday` and `weekly`.
- `runner/run.sh --self-test weekday` and `runner/run.sh --self-test weekly` pass offline.
- `runner/run.sh --dry-run weekday` and `runner/run.sh --dry-run weekly` write local `offline_wiring_ready` reports without invoking live Codex, live source fetch, or Telegram.
- `runner/tools/validate_runtime.py --check all` passes.
- `runner/tests` pass.

### Not Implemented

- Full hard rebuild and legacy deletion.
- Production cron cutover.
- Live source/digest validation through the new runner.
- Telegram delivery verification.
- Consumption of new `runtime/prompts/` by live runner execution; live runs still delegate to the legacy wrapper in this minimum.

### Verification

```bash
python3 runner/tools/validate_runtime.py --check all
python3 -m pytest runner/tests -q
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
runner/run.sh --dry-run weekday
runner/run.sh --dry-run weekly
git diff --check
```
```

- [ ] **Step 4: Run final verification**

Run:

```bash
python3 runner/tools/validate_runtime.py --check docs
python3 runner/tools/validate_runtime.py --check all
python3 -m pytest runner/tests -q
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
runner/run.sh --dry-run weekday
runner/run.sh --dry-run weekly
git diff --check
git status --short
```

Expected:

- validation passes;
- docs validation passes;
- runner tests pass;
- weekday and weekly self-tests pass;
- weekday and weekly offline dry-runs pass;
- diff check passes;
- status shows only intended tracked changes plus local dry-run reports if `.state/` reports are untracked.

- [ ] **Step 5: Commit MDR-M3**

Run:

```bash
git add docs/operations.md PLANS.md COMPLETION_AUDIT.md
git commit -m "Document minimum refactor dry-run readiness"
```

## Final Verification

Before calling the minimum complete, run:

```bash
python3 runner/tools/validate_runtime.py --check all
python3 -m pytest runner/tests -q
runner/run.sh --self-test weekday
runner/run.sh --self-test weekly
runner/run.sh --dry-run weekday
runner/run.sh --dry-run weekly
git diff --check
git status --short
```

Minimum completion requires all commands to pass. If any command fails, report the failure as a blocker and do not update `COMPLETION_AUDIT.md` to claim readiness.

## Risks And Follow-Up Work

- This minimum delegates live execution to the old `ops/codex-cli/run_schedule.sh`; it is readiness for the new entrypoint, not proof of a fully rebuilt runtime.
- Source quality, live network behavior, and Telegram delivery remain dependent on the legacy wrapper and environment.
- The full `Weekday Weekly Runtime Rebuild` plan remains open for deleting old paths, replacing prompt internals, and moving tools fully under `runner/`.
- Existing dirty benchmark and digest artifacts should be separated before review so they do not obscure the minimum runtime diff.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-14-minimum-refactor-dry-run-readiness.md`.

Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per milestone, review between MDR-M1, MDR-M2, and MDR-M3.
2. **Inline Execution** - execute tasks in this session with checkpointed review after each milestone.
