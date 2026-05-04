# Victory Digest Production Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the scheduled weekday digest path to a production-like "Victory Digest" test run with staged source discovery, shortlist-scoped article prefetch, enrichment, digest generation, review, and sanitized run reporting.

**Architecture:** Keep the public schedule id as `weekday_digest`; "Victory Digest" is the operator label for a production-like test run through `ops/codex-cli/run_schedule.sh weekday_digest`. The wrapper remains the only orchestration entry point, but `weekday_digest` is split into Stage A sandboxed discovery, Stage B deterministic full-text collection for current-run shortlisted URLs, and Stage C sandboxed enrichment/digest/review/delivery. Stage B calls the existing article prefetch helper directly, writes bounded full-text artifacts and compact manifests, and never performs source discovery, ranking, login/CAPTCHA/paywall bypass, proxy rotation, or link-following beyond shortlisted URLs.

**Tech Stack:** Bash wrapper, `codex exec`, Python helper scripts, `requests`, optional existing Playwright browser helper, `.state/` runtime artifacts, existing `Claude Cowork` prompts/contracts, offline Python tests, runtime artifact validator, sanitized run-review markdown.

---

## Definition Of Done

Victory Digest is ready for a production-like test run when all of these are true:

- `ops/codex-cli/run_schedule.sh weekday_digest` executes staged discovery, direct full-text collection, and finish stages through one wrapper invocation.
- Stage A and Stage C run with `-s workspace-write`.
- Stage B runs `tools/shortlist_article_prefetch.py` directly against the current-run shortlist shard.
- Stage B reads only the current-run shortlist shard and helper/runtime files needed for article prefetch.
- Stage B writes only `.state/articles/` and `.state/codex-runs/*article-prefetch*` artifacts.
- If Stage B cannot run, fails globally, or does not write manifests, the wrapper writes a synthetic article prefetch summary/result with every shortlisted item as `snippet_fallback`.
- Stage C receives source prefetch artifacts and article prefetch artifacts in its generated prompt.
- Digest/review stages do not read `.state/articles/` full text directly.
- Offline tests, shell syntax checks, wrapper self-test, and runtime validators pass.
- A live `weekday_digest` test run is executed through the wrapper.
- `docs/run-reviews/2026-05-04-weekday-digest.md` records production-readiness status, source-level blockers, article prefetch counts, digest status, QA status, and Telegram status without secrets or full article bodies.
- A completion audit compares original requirements against implemented behavior and open follow-ups.

## Initial Baseline

Already implemented:

- `tools/article_fetch.py`
- `tools/test_article_fetch.py`
- `tools/shortlist_article_prefetch.py`
- `tools/test_shortlist_article_prefetch.py`
- `scrape_and_enrich` contracts for consuming runner article prefetch manifests
- fixture `config/runtime/mode-fixtures/scrape_and_enrich_runner_article_prefetch.yaml`

Initially not implemented:

- staged `weekday_digest` wrapper execution;
- Stage A/Stage C prompt split;
- wrapper discovery of current-run shortlist path;
- direct Stage B full-text collection helper wiring;
- synthetic article prefetch fallback;
- final live Victory Digest run and completion audit.

## Execution Status

Updated 2026-05-04:

- VD-M1 through VD-M6 are implemented and pass offline validation.
- The weekday wrapper now performs Stage A discovery, direct Stage B article
  prefetch, Stage C finish, and post-Stage-C current-run artifact validation.
- Live run `20260504T131334Z-weekday_digest` reached Stage A and Stage B:
  source discovery produced 59 raw candidates and 14 shortlisted items; article
  prefetch produced 8 `full`, 4 `paywall_stub`, and 2 `snippet_fallback`
  outcomes.
- VD-M7 is not complete as a clean production-like pass. Stage C did not create
  current-run `scrape_and_enrich` or `build_daily_digest` manifests for
  timestamp `20260504T131334Z`, no finish last-message was written, and the
  inner `codex exec` was stopped after repeated loader/plugin warnings. The
  wrapper now has a deterministic guard that would fail this condition instead
  of allowing a false success.
- VD-M8 audit is recorded in
  `docs/run-reviews/2026-05-04-victory-digest-completion-audit.md` with open
  follow-ups.

## Files And Responsibilities

- Modify `tools/test_codex_cli_run_schedule.py`: offline regression tests for staged wrapper wiring, article prefetch fallback, prompt handoff, and direct helper invocation.
- Create `tools/test_codex_schedule_artifacts.py`: offline tests for locating current-run shortlist shards and writing synthetic article prefetch manifests.
- Create `tools/codex_schedule_artifacts.py`: deterministic helper for wrapper artifact lookup and synthetic fallback writing.
- Create `ops/codex-cli/prompts/weekday_digest_discovery.md`: Stage A prompt that runs only `monitor_sources`.
- Create `ops/codex-cli/prompts/weekday_digest_finish.md`: Stage C prompt that runs `scrape_and_enrich`, `build_daily_digest`, optional `review_digest`, and delivery.
- Modify `ops/codex-cli/prompts/weekday_digest.md`: keep as the operator-facing schedule description and point to the staged prompts.
- Modify `ops/codex-cli/run_schedule.sh`: implement staged flow for `weekday_digest`; keep `weekly_digest` and `breaking_alert` on the existing single-stage path unless a later plan changes them.
- Modify `ops/codex-cli/README.md`: document staged execution, Stage B full-text collection, fallback behavior, and Victory Digest test procedure.
- Modify `tools/README.md`: document `codex_schedule_artifacts.py` and article prefetch helper boundaries.
- Modify `docs/run-reviews/2026-05-04-weekday-digest.md`: update after live test.
- Create `docs/run-reviews/2026-05-04-victory-digest-completion-audit.md`: completion audit for this production-readiness pass.
- Modify `PLANS.md`: track this plan as active until the live run and audit complete.
- Modify `docs/plans/shortlist-fulltext-enrichment-runner.md`: update implementation status after staged wrapper and live run milestones complete.

## Milestones

### VD-M1. Wrapper Artifact Helper

**Goal:** Add deterministic, testable artifact lookup and synthetic article prefetch fallback logic before changing the wrapper.

**Files:**
- Create: `tools/codex_schedule_artifacts.py`
- Create: `tools/test_codex_schedule_artifacts.py`

**Acceptance Criteria:**
- Helper finds the newest current-date shortlist shard for a source group and schedule run.
- Helper can snapshot shortlist shards before Stage A and resolve only a newly created shortlist after Stage A.
- Helper refuses to hand Stage B a stale shortlist when Stage A did not create a new current-run shortlist.
- Helper can also accept an explicit shortlist path from `--shortlist-path`.
- Helper writes synthetic article prefetch result and summary JSON files when article prefetch is unavailable.
- Synthetic fallback includes every shortlisted URL with `body_status_hint=snippet_fallback`, `article_file=null`, `fetch_method=synthetic_fallback`, and `failure_class=article_prefetch_unavailable`.
- Helper does not read `.state/raw/`, digests, Telegram reports, or prior article bodies.

**Steps:**

- [ ] **Step 1: Write failing tests for shortlist lookup and synthetic fallback**

Create `tools/test_codex_schedule_artifacts.py` with:

```python
#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import tempfile

import codex_schedule_artifacts


def write_json(path: pathlib.Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def item(url: str, decision: str = "shortlist") -> dict:
    return {
        "run_id": "monitor_sources__20260504T120000Z__daily_core",
        "source_id": "example_source",
        "url": url,
        "canonical_url": url,
        "title": "Example story",
        "published": "2026-05-04",
        "triage_decision": decision,
    }


def test_find_latest_shortlist_for_source_group() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        older = root / ".state/shortlists/2026-05-04/monitor_sources__20260504T110000Z__daily_core.json"
        newer = root / ".state/shortlists/2026-05-04/monitor_sources__20260504T120000Z__daily_core.json"
        other_group = root / ".state/shortlists/2026-05-04/monitor_sources__20260504T130000Z__weekly_context.json"
        write_json(older, [item("https://example.test/older")])
        write_json(newer, [item("https://example.test/newer")])
        write_json(other_group, [item("https://example.test/weekly")])

        found = codex_schedule_artifacts.find_latest_shortlist(
            repo_root=root,
            run_date="2026-05-04",
            source_group="daily_core",
        )

        assert found == newer


def test_find_new_shortlist_rejects_stale_shards() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        stale = root / ".state/shortlists/2026-05-04/monitor_sources__20260504T110000Z__daily_core.json"
        write_json(stale, [item("https://example.test/stale")])
        before = codex_schedule_artifacts.snapshot_shortlists(
            repo_root=root,
            run_date="2026-05-04",
            source_group="daily_core",
        )

        try:
            codex_schedule_artifacts.find_new_shortlist(
                repo_root=root,
                run_date="2026-05-04",
                source_group="daily_core",
                before_paths=before,
            )
        except FileNotFoundError as exc:
            assert "no new shortlist shard" in str(exc)
        else:
            raise AssertionError("stale shortlist should not be accepted")

        fresh = root / ".state/shortlists/2026-05-04/monitor_sources__20260504T120000Z__daily_core.json"
        write_json(fresh, [item("https://example.test/fresh")])

        found = codex_schedule_artifacts.find_new_shortlist(
            repo_root=root,
            run_date="2026-05-04",
            source_group="daily_core",
            before_paths=before,
        )

        assert found == fresh


def test_write_synthetic_article_prefetch_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        shortlist = root / ".state/shortlists/2026-05-04/monitor_sources__20260504T120000Z__daily_core.json"
        write_json(shortlist, [item("https://example.test/one"), item("https://example.test/drop", "drop")])

        doc = codex_schedule_artifacts.write_synthetic_article_prefetch(
            repo_root=root,
            run_id="20260504T121000Z-weekday_digest",
            shortlist_path=shortlist,
            reason="article_prefetch_stage_failed",
            fetched_at="2026-05-04T12:10:00Z",
        )

        assert doc["summary"]["shortlisted_count"] == 1
        assert doc["summary"]["attempted_count"] == 0
        assert doc["summary"]["snippet_fallback_count"] == 1
        assert doc["results"][0]["url"] == "https://example.test/one"
        assert doc["results"][0]["body_status_hint"] == "snippet_fallback"
        assert doc["results"][0]["article_file"] is None
        assert doc["results"][0]["fetch_method"] == "synthetic_fallback"
        assert doc["results"][0]["failure_class"] == "article_prefetch_unavailable"
        assert (root / doc["summary"]["result_path"]).exists()
        assert (root / doc["summary"]["summary_path"]).exists()


def main() -> None:
    tests = [
        test_find_latest_shortlist_for_source_group,
        test_find_new_shortlist_rejects_stale_shards,
        test_write_synthetic_article_prefetch_fallback,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 tools/test_codex_schedule_artifacts.py
```

Expected: `ModuleNotFoundError: No module named 'codex_schedule_artifacts'`.

- [ ] **Step 3: Implement minimal helper**

Create `tools/codex_schedule_artifacts.py` with functions:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(path: pathlib.Path, repo_root: pathlib.Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def read_json(path: pathlib.Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def coerce_items(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("shortlisted_items", "items", "shortlist", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    raise ValueError("shortlist shard must be a JSON array or an object containing a shortlist array")


def shortlisted_items(shortlist_path: pathlib.Path) -> list[dict]:
    return [
        item for item in coerce_items(read_json(shortlist_path))
        if item.get("triage_decision") == "shortlist"
    ]


def find_latest_shortlist(*, repo_root: pathlib.Path, run_date: str, source_group: str) -> pathlib.Path:
    base = repo_root / ".state" / "shortlists" / run_date
    matches = sorted(base.glob(f"monitor_sources__*__{source_group}.json"))
    if not matches:
        raise FileNotFoundError(f"no shortlist shard found for {run_date} source group {source_group}")
    return matches[-1]


def snapshot_shortlists(*, repo_root: pathlib.Path, run_date: str, source_group: str) -> set[str]:
    base = repo_root / ".state" / "shortlists" / run_date
    return {
        path.resolve().as_posix()
        for path in base.glob(f"monitor_sources__*__{source_group}.json")
    }


def find_new_shortlist(
    *,
    repo_root: pathlib.Path,
    run_date: str,
    source_group: str,
    before_paths: set[str],
) -> pathlib.Path:
    base = repo_root / ".state" / "shortlists" / run_date
    matches = sorted(
        path for path in base.glob(f"monitor_sources__*__{source_group}.json")
        if path.resolve().as_posix() not in before_paths
    )
    if not matches:
        raise FileNotFoundError(f"no new shortlist shard found for {run_date} source group {source_group}")
    return matches[-1]


def synthetic_entry(item: dict, reason: str) -> dict:
    return {
        "source_id": item.get("source_id") or "",
        "url": item.get("url") or "",
        "canonical_url": item.get("canonical_url") or item.get("url") or "",
        "title": item.get("title") or "",
        "published": item.get("published"),
        "body_status_hint": "snippet_fallback",
        "article_file": None,
        "fetch_method": "synthetic_fallback",
        "text_char_count": 0,
        "error": None,
        "failure_class": "article_prefetch_unavailable",
        "soft_fail": reason,
        "soft_fail_detail": reason,
        "http": None,
    }


def write_synthetic_article_prefetch(
    *,
    repo_root: pathlib.Path,
    run_id: str,
    shortlist_path: pathlib.Path,
    reason: str,
    fetched_at: str | None = None,
) -> dict:
    repo_root = repo_root.resolve()
    shortlist_path = shortlist_path.resolve()
    fetched_at_value = fetched_at or now_iso()
    entries = [synthetic_entry(item, reason) for item in shortlisted_items(shortlist_path)]
    result_path = repo_root / ".state" / "codex-runs" / f"{run_id}-article-prefetch-result.json"
    summary_path = repo_root / ".state" / "codex-runs" / f"{run_id}-article-prefetch-summary.json"
    summary = {
        "fetched_at": fetched_at_value,
        "shortlisted_count": len(entries),
        "attempted_count": 0,
        "full_count": 0,
        "snippet_fallback_count": len(entries),
        "paywall_stub_count": 0,
        "batch_status": "synthetic_fallback",
        "failure_class": "article_prefetch_unavailable",
        "run_failure": reason,
        "result_path": rel(result_path, repo_root),
        "summary_path": rel(summary_path, repo_root),
    }
    doc = {
        "run_id": run_id,
        "shortlist_path": rel(shortlist_path, repo_root),
        "fetched_at": fetched_at_value,
        "batch_status": "synthetic_fallback",
        "failure_class": "article_prefetch_unavailable",
        "run_failure": reason,
        "summary": summary,
        "results": entries,
    }
    write_json(result_path, doc)
    write_json(summary_path, summary)
    return doc
```

Add a CLI with subcommands `snapshot-shortlists`, `find-new-shortlist`, `find-shortlist`, and `synthetic-article-prefetch` so the bash wrapper can call the helper without parsing Python internals. `snapshot-shortlists` should print one JSON array of absolute path strings; `find-new-shortlist` should accept `--before-json` with that array and print exactly one absolute shortlist path.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
python3 tools/test_codex_schedule_artifacts.py
PYTHONPYCACHEPREFIX=.pycache-local python3 -m py_compile tools/codex_schedule_artifacts.py
```

Expected: tests pass and compile exits `0`.

- [ ] **Step 5: Commit**

Run:

```bash
git add tools/codex_schedule_artifacts.py tools/test_codex_schedule_artifacts.py
git -c user.name=Codex -c user.email=codex@local commit -m "Add schedule artifact helper"
```

### VD-M2. Two Prompt Contracts

**Goal:** Add explicit prompts for the two Codex reasoning stages: discovery and finish.

**Files:**
- Create: `ops/codex-cli/prompts/weekday_digest_discovery.md`
- Create: `ops/codex-cli/prompts/weekday_digest_finish.md`
- Modify: `ops/codex-cli/prompts/weekday_digest.md`

**Acceptance Criteria:**
- Discovery prompt runs `monitor_sources` only.
- Finish prompt runs `scrape_and_enrich`, `build_daily_digest`, optional `review_digest`, and Telegram delivery.
- Finish prompt states that article full-text artifacts come only from the Stage B helper manifest.
- Finish prompt forbids digest/review modes from reading `.state/articles/` directly.

**Steps:**

- [ ] **Step 1: Write wrapper prompt tests first**

Extend `tools/test_codex_cli_run_schedule.py` with:

```python
def test_staged_prompt_files_exist_and_have_stage_boundaries() -> None:
    discovery = REPO_ROOT / "ops/codex-cli/prompts/weekday_digest_discovery.md"
    finish = REPO_ROOT / "ops/codex-cli/prompts/weekday_digest_finish.md"

    assert discovery.exists()
    assert finish.exists()

    discovery_text = discovery.read_text(encoding="utf-8")
    finish_text = finish.read_text(encoding="utf-8")

    assert "monitor_sources only" in discovery_text
    assert "Do not run scrape_and_enrich" in discovery_text
    assert "Stage B article prefetch manifest" in finish_text
    assert "Do not read .state/articles/ from digest or review modes" in finish_text
    assert "scrape_and_enrich" in finish_text
    assert "build_daily_digest" in finish_text
    assert "review_digest" in finish_text
```

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 tools/test_codex_cli_run_schedule.py
```

Expected: failure because staged prompt files do not exist.

- [ ] **Step 3: Create discovery prompt**

Create `ops/codex-cli/prompts/weekday_digest_discovery.md`:

```markdown
# Codex CLI Stage A: weekday_digest discovery

Run `monitor_sources only` for the `weekday_digest` schedule binding.

Use the Runner Source Discovery Prefetch preamble in the generated prompt as
canonical local source evidence. Do not repeat static RSS/HTTP fetches already
represented in the prefetch artifacts.

Allowed writes:

- `./.state/raw/{run_date}/`
- `./.state/shortlists/{run_date}/`
- `./.state/runs/{run_date}/`
- optional `./.state/change-requests/{request_date}/`

Do not run scrape_and_enrich, build_daily_digest, review_digest, Telegram
delivery, or article full-text fetching in this stage.

Final response must include:

- monitor_sources run id
- shortlist shard path
- raw shard path
- run manifest path
- source discovery status and source-level blockers
```

- [ ] **Step 4: Create finish prompt**

Create `ops/codex-cli/prompts/weekday_digest_finish.md`:

```markdown
# Codex CLI Stage C: weekday_digest finish

Run the remaining `weekday_digest` modes after discovery and article prefetch:

1. `scrape_and_enrich`
2. `build_daily_digest`
3. optional `review_digest`
4. Telegram delivery when configured

Use the generated prompt's source prefetch artifacts and Stage B article
prefetch manifest as local evidence. `scrape_and_enrich` may read article files
only when the article prefetch manifest entry matches a current-run shortlisted
URL.

Do not read .state/articles/ from digest or review modes. Do not pass article
body text into digest markdown, review markdown, final response, or run-review
docs.

Final response must report source discovery, article prefetch, enrichment,
digest generation, QA/review, Telegram delivery, incomplete items, and change
requests as separate stage statuses.
```

- [ ] **Step 5: Update existing weekday prompt**

Modify `ops/codex-cli/prompts/weekday_digest.md` so it states that direct
production runs use the discovery/finish prompts through `run_schedule.sh`, while
the file remains the operator-facing schedule summary.

- [ ] **Step 6: Verify GREEN**

Run:

```bash
python3 tools/test_codex_cli_run_schedule.py
bash -n ops/codex-cli/run_schedule.sh
```

Expected: tests pass and shell syntax exits `0`.

- [ ] **Step 7: Commit**

Run:

```bash
git add ops/codex-cli/prompts/weekday_digest_discovery.md ops/codex-cli/prompts/weekday_digest_finish.md ops/codex-cli/prompts/weekday_digest.md tools/test_codex_cli_run_schedule.py
git -c user.name=Codex -c user.email=codex@local commit -m "Add staged weekday digest prompts"
```

### VD-M3. Staged Wrapper Execution

**Goal:** Wire `weekday_digest` through source prefetch, Stage A discovery, direct Stage B full-text collection, and Stage C finish.

**Files:**
- Modify: `ops/codex-cli/run_schedule.sh`
- Modify: `tools/test_codex_cli_run_schedule.py`

**Acceptance Criteria:**
- `weekly_digest` and `breaking_alert` keep the existing single-stage flow.
- `weekday_digest` self-test reports Stage A prompt, Stage B helper, and Stage C prompt paths.
- Stage A and Stage C use `-s workspace-write`.
- Stage B calls `tools/shortlist_article_prefetch.py` directly after Stage A writes a new current-run shortlist shard.
- Generated Stage C prompt includes article prefetch result and summary paths.
- Wrapper writes synthetic article prefetch fallback if the direct helper exits non-zero.

**Steps:**

- [ ] **Step 1: Write failing tests for staged wrapper output and direct helper invocation**

Extend `tools/test_codex_cli_run_schedule.py` with:

```python
def test_weekday_self_test_reports_direct_article_prefetch_wiring() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        script_path = make_wrapper_fixture(root)
        for name in ["weekday_digest_discovery.md", "weekday_digest_finish.md"]:
            (root / "ops/codex-cli/prompts" / name).write_text(f"{name}\n", encoding="utf-8")
        env_file = root / ".env.good"
        env_file.write_text("HTTP_USER_AGENT='PropTechNewsMonitor/1.0 (+team@example.com)'\n", encoding="utf-8")

        result = run_wrapper(script_path, env_file)

    assert result.returncode == 0
    assert "Stage A prompt:" in result.stdout
    assert "Stage B helper:" in result.stdout
    assert "Stage C prompt:" in result.stdout


def test_wrapper_invokes_article_prefetch_helper_directly() -> None:
    wrapper_text = WRAPPER.read_text(encoding="utf-8")

    assert "-s workspace-write" in wrapper_text
    assert "tools/shortlist_article_prefetch.py" in wrapper_text
    assert "snapshot-shortlists" in wrapper_text
    assert "find-new-shortlist" in wrapper_text
    assert "synthetic-article-prefetch" in wrapper_text
    assert "danger-full-access" not in wrapper_text
```

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 tools/test_codex_cli_run_schedule.py
```

Expected: failure because staged wrapper strings are missing.

- [ ] **Step 3: Refactor wrapper variables**

In `ops/codex-cli/run_schedule.sh`, add variables:

```bash
DISCOVERY_PROMPT_FILE="$SCRIPT_DIR/prompts/weekday_digest_discovery.md"
FINISH_PROMPT_FILE="$SCRIPT_DIR/prompts/weekday_digest_finish.md"
DISCOVERY_EVENT_LOG="$RUN_ROOT/$RUN_ID-discovery-events.jsonl"
FINISH_EVENT_LOG="$RUN_ROOT/$RUN_ID-finish-events.jsonl"
DISCOVERY_LAST_MESSAGE="$RUN_ROOT/$RUN_ID-discovery-last-message.txt"
FINISH_LAST_MESSAGE="$RUN_ROOT/$RUN_ID-finish-last-message.txt"
DISCOVERY_PROMPT="$RUN_ROOT/$RUN_ID-discovery-prompt.md"
FINISH_PROMPT="$RUN_ROOT/$RUN_ID-finish-prompt.md"
ARTICLE_PREFETCH_RESULT="$RUN_ROOT/$RUN_ID-article-prefetch-result.json"
ARTICLE_PREFETCH_SUMMARY="$RUN_ROOT/$RUN_ID-article-prefetch-summary.json"
ARTIFACT_HELPER="$REPO_ROOT/tools/codex_schedule_artifacts.py"
ARTICLE_PREFETCH_HELPER="$REPO_ROOT/tools/shortlist_article_prefetch.py"
```

- [ ] **Step 4: Expand self-test**

For `CODEX_RUN_SCHEDULE_SELF_TEST=1`, print:

```bash
printf 'Stage A prompt: %s\n' "$DISCOVERY_PROMPT_FILE"
printf 'Stage B helper: %s\n' "$ARTICLE_PREFETCH_HELPER"
printf 'Stage C prompt: %s\n' "$FINISH_PROMPT_FILE"
printf 'Artifact helper: %s\n' "$ARTIFACT_HELPER"
```

- [ ] **Step 5: Add single-stage function**

Move the existing single `codex exec` invocation into:

```bash
run_single_stage_schedule() {
  build_source_prefetch_prompt "$GENERATED_PROMPT" "$PROMPT_FILE"
  "$CODEX_BIN" exec \
    -C "$REPO_ROOT" \
    -s workspace-write \
    --json \
    --output-last-message "$LAST_MESSAGE" \
    - < "$GENERATED_PROMPT" > "$EVENT_LOG"
}
```

Keep this path for `weekly_digest` and `breaking_alert`.

- [ ] **Step 6: Add weekday staged flow**

Implement:

```bash
run_weekday_staged_schedule() {
  SHORTLIST_BEFORE_JSON="$(python3 "$ARTIFACT_HELPER" snapshot-shortlists \
    --repo-root "$REPO_ROOT" \
    --run-date "$(date -u '+%Y-%m-%d')" \
    --source-group daily_core)"

  build_discovery_prompt
  "$CODEX_BIN" exec -C "$REPO_ROOT" -s workspace-write --json \
    --output-last-message "$DISCOVERY_LAST_MESSAGE" \
    - < "$DISCOVERY_PROMPT" > "$DISCOVERY_EVENT_LOG"

  SHORTLIST_PATH="$(python3 "$ARTIFACT_HELPER" find-new-shortlist \
    --repo-root "$REPO_ROOT" \
    --run-date "$(date -u '+%Y-%m-%d')" \
    --source-group daily_core \
    --before-json "$SHORTLIST_BEFORE_JSON")"

  if ! python3 "$ARTICLE_PREFETCH_HELPER" \
    --repo-root "$REPO_ROOT" \
    --shortlist-path "$SHORTLIST_PATH" \
    --run-id "$RUN_ID" \
    --pretty > "$RUN_ROOT/$RUN_ID-article-prefetch-stdout.json"; then
    python3 "$ARTIFACT_HELPER" synthetic-article-prefetch \
      --repo-root "$REPO_ROOT" \
      --run-id "$RUN_ID" \
      --shortlist-path "$SHORTLIST_PATH" \
      --reason article_prefetch_stage_failed
  fi

  build_finish_prompt "$SHORTLIST_PATH"
  "$CODEX_BIN" exec -C "$REPO_ROOT" -s workspace-write --json \
    --output-last-message "$FINISH_LAST_MESSAGE" \
    - < "$FINISH_PROMPT" > "$FINISH_EVENT_LOG"
}
```

Use helper functions to generate prompts. The generated finish prompt must include:

```markdown
- Shortlist shard: `$SHORTLIST_PATH`
- Article prefetch result: `$ARTICLE_PREFETCH_RESULT`
- Article prefetch summary: `$ARTICLE_PREFETCH_SUMMARY`
```

- [ ] **Step 7: Verify GREEN**

Run:

```bash
python3 tools/test_codex_cli_run_schedule.py
bash -n ops/codex-cli/run_schedule.sh
CODEX_RUN_SCHEDULE_SELF_TEST=1 ops/codex-cli/run_schedule.sh weekday_digest
```

Expected: tests pass; self-test prints staged prompt paths and the Stage B helper path.

- [ ] **Step 8: Commit**

Run:

```bash
git add ops/codex-cli/run_schedule.sh tools/test_codex_cli_run_schedule.py
git -c user.name=Codex -c user.email=codex@local commit -m "Wire staged weekday digest wrapper"
```

### VD-M4. Stage B Manifest Guard

**Goal:** Ensure the direct full-text collection stage reliably produces manifests before Stage C starts.

**Files:**
- Modify: `ops/codex-cli/run_schedule.sh`
- Modify: `tools/test_codex_cli_run_schedule.py`

**Acceptance Criteria:**
- Wrapper validates that `$ARTICLE_PREFETCH_RESULT` and `$ARTICLE_PREFETCH_SUMMARY` exist after the direct Stage B helper call.
- If either file is missing, wrapper writes synthetic fallback.
- Missing-manifest fallback is visible in Stage C prompt.

**Steps:**

- [ ] **Step 1: Write failing test for manifest validation**

Add to `tools/test_codex_cli_run_schedule.py`:

```python
def test_wrapper_validates_article_prefetch_manifest_presence() -> None:
    wrapper_text = WRAPPER.read_text(encoding="utf-8")

    assert "article_prefetch_manifest_missing" in wrapper_text
    assert "[ ! -f \"$ARTICLE_PREFETCH_RESULT\" ]" in wrapper_text
    assert "[ ! -f \"$ARTICLE_PREFETCH_SUMMARY\" ]" in wrapper_text
```

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 tools/test_codex_cli_run_schedule.py
```

Expected: failure because manifest presence checks do not exist.

- [ ] **Step 3: Add manifest presence fallback**

After the direct Stage B helper call, add:

```bash
if [ ! -f "$ARTICLE_PREFETCH_RESULT" ] || [ ! -f "$ARTICLE_PREFETCH_SUMMARY" ]; then
  python3 "$ARTIFACT_HELPER" synthetic-article-prefetch \
    --repo-root "$REPO_ROOT" \
    --run-id "$RUN_ID" \
    --shortlist-path "$SHORTLIST_PATH" \
    --reason article_prefetch_manifest_missing
fi
```

- [ ] **Step 4: Verify GREEN**

Run:

```bash
python3 tools/test_codex_cli_run_schedule.py
bash -n ops/codex-cli/run_schedule.sh
CODEX_RUN_SCHEDULE_SELF_TEST=1 ops/codex-cli/run_schedule.sh weekday_digest
```

- [ ] **Step 5: Commit**

Run:

```bash
git add ops/codex-cli/run_schedule.sh tools/test_codex_cli_run_schedule.py
git -c user.name=Codex -c user.email=codex@local commit -m "Harden article prefetch stage fallback"
```

### VD-M5. Documentation And Operator Runbook

**Goal:** Document how to run Victory Digest and what production-like status means.

**Files:**
- Modify: `ops/codex-cli/README.md`
- Modify: `tools/README.md`
- Modify: `docs/plans/shortlist-fulltext-enrichment-runner.md`

**Acceptance Criteria:**
- README explains three-stage weekday flow.
- README explains that Stage B is a direct full-text helper call.
- README explains synthetic fallback semantics.
- Tools README lists `codex_schedule_artifacts.py`.
- SFE plan status marks SFE-M4/SFE-M5 complete after implementation.

**Steps:**

- [ ] **Step 1: Add docs test expectations**

Add to `tools/test_codex_cli_run_schedule.py`:

```python
def test_readme_documents_staged_victory_digest_runbook() -> None:
    readme = (REPO_ROOT / "ops/codex-cli/README.md").read_text(encoding="utf-8")

    assert "Victory Digest" in readme
    assert "Stage A" in readme
    assert "Stage B" in readme
    assert "Stage C" in readme
    assert "tools/shortlist_article_prefetch.py" in readme
    assert "synthetic article prefetch fallback" in readme
```

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 tools/test_codex_cli_run_schedule.py
```

- [ ] **Step 3: Update operator README**

Add a section to `ops/codex-cli/README.md`:

```markdown
## Victory Digest Production-Like Run

Victory Digest is the operator label for a production-like `weekday_digest`
test run through the canonical wrapper:

```bash
ops/codex-cli/run_schedule.sh weekday_digest
```

For `weekday_digest`, the wrapper runs:

- Stage A: sandboxed source discovery and shortlist emission.
- Stage B: direct full-text collection for the current shortlist through
  `tools/shortlist_article_prefetch.py`.
- Stage C: sandboxed enrichment, digest generation, review, and delivery.

Stage A and Stage C run through `codex exec` with `workspace-write`. Stage B is
not a separate Codex agent; it is a deterministic helper call from the wrapper.
It may fetch full text only for URLs present in the current-run shortlist shard.

If Stage B fails or does not write article prefetch manifests, the wrapper writes
a synthetic article prefetch fallback so Stage C can continue with
`snippet_fallback` evidence rather than failing the whole digest.
```

- [ ] **Step 4: Update tools README**

Add `codex_schedule_artifacts.py` to the tools table with:

```markdown
| `codex_schedule_artifacts.py` | Wrapper helper for locating current-run shortlist shards and writing synthetic article prefetch fallback manifests. |
```

- [ ] **Step 5: Update SFE plan status**

In `docs/plans/shortlist-fulltext-enrichment-runner.md`, mark staged wrapper/full-text handoff complete after direct Stage B wrapper implementation. Keep SFE-M6 as optional browser article fallback unless implemented in this pass.

- [ ] **Step 6: Verify GREEN**

Run:

```bash
python3 tools/test_codex_cli_run_schedule.py
python3 tools/test_article_fetch.py
python3 tools/test_shortlist_article_prefetch.py
python3 tools/test_codex_schedule_artifacts.py
python3 tools/validate_runtime_artifacts.py --check all
```

- [ ] **Step 7: Commit**

Run:

```bash
git add ops/codex-cli/README.md tools/README.md docs/plans/shortlist-fulltext-enrichment-runner.md tools/test_codex_cli_run_schedule.py
git -c user.name=Codex -c user.email=codex@local commit -m "Document Victory Digest staged runbook"
```

### VD-M6. Full Offline Verification Gate

**Goal:** Establish the final offline gate before live Victory Digest execution.

**Files:**
- Modify only if tests reveal a contract mismatch:
  - `ops/codex-cli/run_schedule.sh`
  - `tools/codex_schedule_artifacts.py`
  - `tools/test_codex_cli_run_schedule.py`
  - `tools/test_codex_schedule_artifacts.py`

**Acceptance Criteria:**
- All helper tests pass.
- Shell syntax passes.
- Wrapper self-test passes.
- Runtime artifact validation passes.
- No tracked `.state/` files are staged.

**Steps:**

- [ ] **Step 1: Run full offline gate**

Run:

```bash
python3 tools/test_article_fetch.py
python3 tools/test_shortlist_article_prefetch.py
python3 tools/test_codex_schedule_artifacts.py
python3 tools/test_codex_cli_run_schedule.py
python3 tools/test_validate_runtime_artifacts.py
python3 tools/validate_runtime_artifacts.py --check all
PYTHONPYCACHEPREFIX=.pycache-local python3 -m py_compile tools/article_fetch.py tools/shortlist_article_prefetch.py tools/codex_schedule_artifacts.py
bash -n ops/codex-cli/run_schedule.sh
CODEX_RUN_SCHEDULE_SELF_TEST=1 ops/codex-cli/run_schedule.sh weekday_digest
git diff --check
git status --short
```

Expected: every command exits `0`; `git status --short` shows only intended tracked source/docs changes or is clean after commits.

- [ ] **Step 2: Fix only failing touched-area issues**

If a command fails, change only files listed in this plan. Re-run the failed command and then the full offline gate.

- [ ] **Step 3: Commit any verification fixes**

Run only when Step 2 changed files:

```bash
git add ops/codex-cli/run_schedule.sh ops/codex-cli/README.md tools/README.md tools/codex_schedule_artifacts.py tools/test_codex_schedule_artifacts.py tools/test_codex_cli_run_schedule.py docs/plans/shortlist-fulltext-enrichment-runner.md
git -c user.name=Codex -c user.email=codex@local commit -m "Pass Victory Digest offline gate"
```

### VD-M7. Live Victory Digest Test Run

**Goal:** Run the production-like weekday digest path and record actual source/enrichment/delivery outcomes.

**Files:**
- Modify: `docs/run-reviews/2026-05-04-weekday-digest.md`
- Create: `.state/` artifacts locally only; do not commit `.state/`

**Acceptance Criteria:**
- Run command is `ops/codex-cli/run_schedule.sh weekday_digest`.
- Run reaches Stage A, Stage B or synthetic fallback, and Stage C.
- Run review records article prefetch `full_count`, `snippet_fallback_count`, `paywall_stub_count`.
- Run review records whether the digest is `canonical_digest`, `partial_digest`, or `non_canonical_digest`.
- Run review records Telegram status as `delivered`, `dry_run`, `not_configured`, or classified failure.
- Run review contains no secrets, full Bot API URLs, cookies, proxy credentials, full article bodies, or raw `.state` event log excerpts.

**Steps:**

- [ ] **Step 1: Run Victory Digest**

Run:

```bash
ops/codex-cli/run_schedule.sh weekday_digest
```

Expected: wrapper exits `0` for a generated digest or exits with a classified non-zero failure that has local `.state/codex-runs/` evidence. In local sandboxed development, if the direct Stage B helper needs network access, request escalation for the wrapper/helper command through the normal approval path.

- [ ] **Step 2: Inspect local run artifacts**

Run:

```bash
ls -1 .state/codex-runs | tail -n 30
find .state -path '*article-prefetch*' -type f | tail -n 20
find .state/shortlists -type f | tail -n 5
find .state/enriched -type f | tail -n 5
find digests -type f | tail -n 5
```

Expected: source prefetch, article prefetch result/summary, Stage A/C event logs, shortlist, enrichment, run manifests, and digest artifacts are present when their stages ran.

- [ ] **Step 3: Update run review**

Update `docs/run-reviews/2026-05-04-weekday-digest.md` with a compact stage
table. Use the exact local artifact paths produced by Step 2, but include only
sanitized paths and count/status fields. Required rows:

- Source prefetch: status from the source prefetch summary, artifact path to the source prefetch summary, source-level blockers.
- Stage A discovery: status from the `monitor_sources` run manifest, artifact path to the current shortlist shard, shortlist count.
- Stage B article prefetch: status from the article prefetch summary, artifact path to the article prefetch summary, `full_count`, `snippet_fallback_count`, and `paywall_stub_count`.
- Stage C enrichment: status from the `scrape_and_enrich` run manifest, artifact path to the enrichment shard, `evidence_completeness`.
- Digest generation: status from the digest run manifest, digest markdown path, `canonical_digest` / `partial_digest` / `non_canonical_digest`.
- QA review: status from the review report, warning count, critical count.
- Telegram delivery: status from the Telegram send report or wrapper final message, one of `delivered`, `dry_run`, `not_configured`, or classified failure.

Do not paste article text or JSONL event excerpts.

- [ ] **Step 4: Scan review and digest for leaks**

Run:

```bash
rg --count-matches 'api\.telegram\.org/bot|/bot[0-9]+:[A-Za-z0-9_-]+' docs/run-reviews/2026-05-04-weekday-digest.md digests
rg -n -- '\.state/|__[0-9]{8}T[0-9]{6}Z__|operator notes|run id' digests
```

Expected: no Telegram token or Bot API URL matches. Digest markdown must not expose internal run ids or operator-only `.state` paths; run-review docs may reference sanitized local artifact paths.

- [ ] **Step 5: Commit run review**

Run:

```bash
git add docs/run-reviews/2026-05-04-weekday-digest.md
git -c user.name=Codex -c user.email=codex@local commit -m "Record Victory Digest run review"
```

### VD-M8. Completion Audit

**Goal:** Produce a concise audit comparing requirements, implementation, live run outcome, and remaining production risks.

**Files:**
- Create: `docs/run-reviews/2026-05-04-victory-digest-completion-audit.md`
- Modify: `PLANS.md`
- Modify: `docs/plans/victory-digest-production-readiness.md`
- Modify: `docs/plans/shortlist-fulltext-enrichment-runner.md`

**Acceptance Criteria:**
- Audit lists implemented requirements.
- Audit lists partially implemented requirements and blockers.
- Audit lists missing requirements, if any.
- Audit lists source-level blockers requiring change requests.
- Audit states whether Victory Digest is production-like, partial production-like, or blocked.
- Active plan index status is updated.

**Steps:**

- [ ] **Step 1: Create completion audit**

Create `docs/run-reviews/2026-05-04-victory-digest-completion-audit.md`:

```markdown
# Victory Digest Completion Audit

Date: 2026-05-04
Schedule: `weekday_digest`

## Requirement Status

Use one row per requirement. The status value must be exactly one of
`implemented`, `partial`, or `missing`. The evidence cell must cite a commit,
test command, run artifact, or run-review section.

Required rows:

- Staged wrapper execution
- Stage A and C sandboxed
- Stage B restricted article prefetch
- Synthetic fallback
- Article manifests consumed by scrape_and_enrich
- Digest/review full-text boundary
- Live run completed through wrapper
- Sanitized run review

## Live Run Outcome

Record the concrete live values for:

- Source discovery
- Article prefetch
- Enrichment
- Digest
- QA
- Telegram

## Remaining Blockers

Use one row per blocker. Each row must name the source or stage, the observed
blocker, and the required follow-up. If there are no blockers, write a single
sentence: `No remaining blockers were observed in the Victory Digest run.`

## Production Readiness Decision

Decision: `production_like` / `partial_production_like` / `blocked`

Rationale: cite the live run review and the blocker table.
```

- [ ] **Step 2: Update plan statuses**

Update:

- `PLANS.md`: mark Victory Digest Production Readiness with completed status or partial/blocker status.
- `docs/plans/victory-digest-production-readiness.md`: add implementation status with completed milestones.
- `docs/plans/shortlist-fulltext-enrichment-runner.md`: mark SFE-M7 complete only if the live run and audit meet its acceptance criteria.

- [ ] **Step 3: Final verification**

Run:

```bash
python3 tools/test_article_fetch.py
python3 tools/test_shortlist_article_prefetch.py
python3 tools/test_codex_schedule_artifacts.py
python3 tools/test_codex_cli_run_schedule.py
python3 tools/test_validate_runtime_artifacts.py
python3 tools/validate_runtime_artifacts.py --check all
bash -n ops/codex-cli/run_schedule.sh
git diff --check
git status --short
```

- [ ] **Step 4: Commit audit**

Run:

```bash
git add docs/run-reviews/2026-05-04-victory-digest-completion-audit.md PLANS.md docs/plans/victory-digest-production-readiness.md docs/plans/shortlist-fulltext-enrichment-runner.md
git -c user.name=Codex -c user.email=codex@local commit -m "Audit Victory Digest production readiness"
```

## Coverage Matrix

| Requirement | Milestone |
| --- | --- |
| Wrapper reaches production-like daily flow | VD-M3, VD-M6, VD-M7 |
| Stage A/C stay sandboxed | VD-M3 |
| Stage B article prefetch is isolated | VD-M1, VD-M3, VD-M4 |
| Current-run shortlist only | VD-M1, VD-M2, VD-M3 |
| Synthetic fallback when prefetch unavailable | VD-M1, VD-M3, VD-M4 |
| Article manifests passed to enrichment | VD-M3, VD-M4 |
| Digest/review no full-body leakage | VD-M2, VD-M7, VD-M8 |
| Offline tests before live run | VD-M1 through VD-M6 |
| Operator runbook | VD-M5 |
| Live Victory Digest run | VD-M7 |
| Completion audit | VD-M8 |

## Non-Goals

- Do not create a new schedule id named `victory_digest`.
- Do not broaden `weekly_digest` or `breaking_alert` in this pass.
- Do not use Stage B to discover sources or rank stories.
- Do not automate login, CAPTCHA, paywall bypass, proxy rotation, cookies, or sessions.
- Do not commit `.state/`, Codex JSONL events, full article bodies, Telegram tokens, or raw Bot API URLs.
- Do not change digest editorial selection rules except to pass through evidence status and production-readiness classification.

## Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| Stage B network access denied | Synthetic article prefetch fallback keeps Stage C running with `snippet_fallback`. |
| Stage B consumes hostile web content | The direct helper treats fetched text as data, emits bounded artifacts, and cannot alter Codex prompts or repository instructions. |
| Stage B writes tracked files | Wrapper calls only `tools/shortlist_article_prefetch.py`; expected writes are `.state/articles/` and article-prefetch manifests. |
| Source-level paywalls keep many items as fallback | Run review records `paywall_stub`/`snippet_fallback` and emits change requests where persistent adapter changes are needed. |
| Digest looks complete despite partial evidence | Stage report and run review must preserve `partial_digest` or non-canonical status. |
| Secrets appear in tracked docs | Run review uses sanitized summaries and leak scans before commit. |
