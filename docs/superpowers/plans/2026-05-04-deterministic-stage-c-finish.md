# Deterministic Stage C Finish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace Stage C freeform artifact writing with a deterministic finish materializer so every successful Victory Digest run emits fresh current-run enrichment, digest, brief, and run manifests.

**Architecture:** Keep Codex as the analyst, but move filesystem artifact creation to a deterministic Python helper. Stage C Codex writes one strict compact draft JSON under `.state/codex-runs/{run_id}-finish-draft.json`; `tools/stage_c_finish.py` validates the draft against the current shortlist and article-prefetch manifests, then materializes all current-run `.state` and digest artifacts with exact names.

**Tech Stack:** Bash wrapper, Python stdlib JSON/pathlib/argparse, existing `.state` schemas, existing Codex CLI staged wrapper, offline Python tests.

---

## Implementation Status

Status: completed on 2026-05-04.

Live rerun `20260504T142209Z-weekday_digest` passed the 95% production-ready
test-run gate: wrapper completion, finish artifact validation, article prefetch
thresholds, QA gate, digest safety scans, and Telegram dry-run all passed.
Residual caveats are source-level discovery failures and absence of live
Telegram credentials in the test environment.

---

## Why This Plan Exists

Live Victory run `20260504T131334Z-weekday_digest` proved Stage A discovery and
Stage B article prefetch, but Stage C did not create current-run artifacts:

- missing `.state/enriched/2026-05-04/scrape_and_enrich__20260504T131334Z__daily_core.json`
- missing `.state/runs/2026-05-04/scrape_and_enrich__20260504T131334Z__daily_core.json`
- missing `.state/runs/2026-05-04/build_daily_digest__20260504T131334Z__telegram_digest.json`
- no finish last-message

The next fix must make this failure impossible to misread as success. A digest
date file alone must never be accepted as proof of a successful staged run.

## File Structure

- Create `tools/stage_c_finish.py`
  - Responsibility: validate Stage C draft JSON and materialize current-run artifacts.
  - Must not read `.state/articles/`.
  - Must not perform network I/O.
  - Must not call Codex or Telegram.
- Create `tools/test_stage_c_finish.py`
  - Responsibility: offline unit tests for draft validation, materialization, and stale/full-text leakage rejection.
- Modify `ops/codex-cli/run_schedule.sh`
  - Add `STAGE_C_FINISH_HELPER` and `FINISH_DRAFT` paths.
  - Include draft path in generated Stage C prompt.
  - After Stage C returns, call the materializer before `validate-finish-artifacts`.
- Modify `ops/codex-cli/prompts/weekday_digest_finish.md`
  - Change Stage C output contract: write only compact draft JSON, not final `.state`/digest artifacts directly.
- Modify `tools/codex_schedule_artifacts.py`
  - Extend `validate_finish_artifacts` to also require finish summary when useful.
  - Keep existing validation compatible with current tests.
- Modify `tools/test_codex_cli_run_schedule.py`
  - Add wrapper tests for Stage C draft path and materializer invocation.
- Modify `tools/README.md`
  - Document `stage_c_finish.py`.
- Modify `ops/codex-cli/README.md`
  - Document Stage C draft/materializer handoff.
- Modify `docs/run-reviews/2026-05-04-victory-digest-completion-audit.md`
  - Add follow-up resolution note after implementation.
- Modify `PLANS.md`
  - Mark this deterministic Stage C finish plan as active during implementation and completed after live validation.

## Draft Contract

Stage C Codex writes exactly this JSON shape:

```json
{
  "schema_version": 1,
  "run_id": "20260504T121000Z-weekday_digest",
  "run_date": "2026-05-04",
  "source_group": "daily_core",
  "delivery_profile": "telegram_digest",
  "enriched_items": [
    {
      "source_id": "example_source",
      "url": "https://example.test/full",
      "canonical_url": "https://example.test/full",
      "title": "Full Article",
      "published": "2026-05-04",
      "companies": ["ExampleCo"],
      "regions": ["US"],
      "topic_tags": ["portal_strategy"],
      "event_type": "product_signal",
      "priority_score": 72,
      "confidence": 0.82,
      "analyst_summary": "ExampleCo expanded a portal feature with direct marketplace implications.",
      "why_it_matters": "The change shows how portals are competing on inventory quality and agent workflow.",
      "avito_implication": "Avito should compare the feature against its professional seller tooling roadmap.",
      "story_id": "story_example_full_20260504",
      "body_status": "full",
      "article_file": ".state/articles/2026-05/2026-05-04_full-article.md",
      "evidence_points": [
        "The article says ExampleCo expanded the portal feature.",
        "The article links the feature to professional seller workflow."
      ],
      "source_quality": "trade_media"
    }
  ],
  "daily_brief": {
    "section_order": ["top_stories", "weak_signals"],
    "top_story_ids": ["story_example_full_20260504"],
    "weak_signal_ids": [],
    "selection_notes": ["Mixed full and fallback evidence; render as production candidate with source caveats."],
    "story_cards": [
      {
        "story_id": "story_example_full_20260504",
        "section": "top_stories",
        "title": "Full Article",
        "url": "https://example.test/full",
        "canonical_url": "https://example.test/full",
        "priority_score": 72,
        "confidence": 0.82,
        "analyst_summary": "ExampleCo expanded a portal feature with direct marketplace implications.",
        "why_it_matters": "The change shows how portals are competing on inventory quality and agent workflow.",
        "avito_implication": "Avito should compare the feature against its professional seller tooling roadmap.",
        "context_refs": [],
        "evidence_notes": [
          "The article says ExampleCo expanded the portal feature."
        ]
      }
    ],
    "render_metadata": {
      "digest_status": "canonical_digest",
      "evidence_completeness": "mixed_or_full_evidence"
    }
  },
  "digest_markdown": "# PropTech Monitor | 04.05.2026\n\n## Главное\n\n1. **[Full Article](https://example.test/full)**\n   - Сигнал: ExampleCo expanded a portal feature with direct marketplace implications.\n   - Почему важно: The change shows how portals are competing on inventory quality and agent workflow.\n   - Для Avito: Avito should compare the feature against its professional seller tooling roadmap.\n   - Доказательство: The article says ExampleCo expanded the portal feature.\n\nmode: build_daily_digest | 04.05.2026\n",
  "qa_review": {
    "status": "warnings",
    "critical_findings_count": 0,
    "warning_findings_count": 1,
    "summary": "QA review found no critical issues and one source-coverage caveat."
  },
  "telegram_delivery": {
    "status": "not_configured",
    "delivered": false,
    "message_parts": 0
  }
}
```

## Acceptance Criteria

- A valid Stage C draft materializes:
  - `.state/enriched/{run_date}/scrape_and_enrich__{timestamp}__daily_core.json`
  - `.state/runs/{run_date}/scrape_and_enrich__{timestamp}__daily_core.json`
  - `.state/briefs/daily/{run_date}__telegram_digest.json`
  - `.state/runs/{run_date}/build_daily_digest__{timestamp}__telegram_digest.json`
  - `digests/{run_date}-daily-digest.md`
  - `.state/codex-runs/{run_id}-finish-summary.json`
- The materializer rejects draft items whose `url` or `canonical_url` are not in the current-run shortlist.
- The materializer rejects `body_status = full` when the article prefetch manifest does not contain a matching `body_status_hint = full` entry.
- The materializer rejects digest markdown containing `.state/`, `.state/articles/`, `article_file`, timestamped run ids, or full article body leakage markers.
- `build_daily_digest` date-level digest output is written only by the deterministic materializer.
- Wrapper calls the materializer before `validate-finish-artifacts`.
- Existing `validate-finish-artifacts` catches missing materialized outputs.
- Offline tests pass without network, Telegram credentials, Playwright, or Codex.
- A live Victory Digest rerun either:
  - succeeds with fresh current-run artifacts, or
  - fails with a clear missing/invalid finish draft or materialization error.

## 95% Production-Ready Test-Run Gate

This plan satisfies the user's "95% production-ready digest" target only when
the final live test run passes all checks below. A clean materialized Stage C run
alone is necessary but not sufficient.

Required pass conditions:

- Wrapper exits successfully and prints `Codex schedule run complete: <run_id>`.
- `validate-finish-artifacts --require-finish-summary` exits `0` for the latest
  run id.
- Stage A has no global environment failure. Source-level failures are allowed
  only if they are classified and recorded in run review or change requests.
- Stage B has `run_failure = null`, `attempted_count = shortlisted_count`, and
  `full_count > 0`.
- Stage C materializer writes current-run enriched shard, scrape manifest, daily
  brief, digest manifest, digest markdown, and finish summary.
- QA is not skipped: `qa_review.status` must be `validated` or `warnings`, and
  `critical_findings_count` must be `0`.
- Digest markdown safety scans return no matches for runtime paths, timestamped
  run ids, operator notes, `article_file`, Telegram bot URLs, or full article
  body leakage markers.
- Telegram delivery does not need a live send for this test-run, but
  `tools/telegram_send.py --dry-run` must succeed against the generated digest
  and report at least one message part.
- The run review explicitly marks the result as `production_candidate_95` only
  if every gate above passes. If any gate fails, record the exact blocker and do
  not call the digest 95% production-ready.

## Task 1: Add Stage C Materializer Tests

**Files:**
- Create: `tools/test_stage_c_finish.py`
- Create later in Task 2: `tools/stage_c_finish.py`

- [x] **Step 1: Write failing tests**

Create `tools/test_stage_c_finish.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import tempfile

import stage_c_finish


def write_json(path: pathlib.Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def shortlist_item(url: str) -> dict:
    return {
        "run_id": "monitor_sources__20260504T120000Z__daily_core",
        "source_id": "example_source",
        "url": url,
        "canonical_url": url.rstrip("/"),
        "title": "Full Article",
        "published": "2026-05-04",
        "shortlisted_at": "2026-05-04T12:00:00Z",
        "triage_decision": "shortlist",
        "shortlist_reason": "Relevant portal strategy signal.",
        "provisional_priority": 70,
        "fetch_strategy": "rss",
        "raw_snippet": "Snippet remains available."
    }


def article_prefetch_doc(url: str) -> dict:
    canonical = url.rstrip("/")
    return {
        "run_id": "20260504T121000Z-weekday_digest",
        "shortlist_path": ".state/shortlists/2026-05-04/monitor_sources__20260504T120000Z__daily_core.json",
        "fetched_at": "2026-05-04T12:10:00Z",
        "batch_status": "partial_success",
        "failure_class": None,
        "run_failure": None,
        "summary": {
            "fetched_at": "2026-05-04T12:10:00Z",
            "shortlisted_count": 1,
            "attempted_count": 1,
            "full_count": 1,
            "snippet_fallback_count": 0,
            "paywall_stub_count": 0,
            "batch_status": "partial_success",
            "failure_class": None,
            "run_failure": None,
            "result_path": ".state/codex-runs/20260504T121000Z-weekday_digest-article-prefetch-result.json",
            "summary_path": ".state/codex-runs/20260504T121000Z-weekday_digest-article-prefetch-summary.json"
        },
        "results": [
            {
                "source_id": "example_source",
                "url": url,
                "canonical_url": canonical,
                "title": "Full Article",
                "published": "2026-05-04",
                "body_status_hint": "full",
                "article_file": ".state/articles/2026-05/2026-05-04_full-article.md",
                "fetch_method": "static_http",
                "text_char_count": 1320,
                "error": None,
                "failure_class": None,
                "soft_fail": None,
                "soft_fail_detail": None,
                "http": {"status": 200}
            }
        ]
    }


def finish_draft(url: str) -> dict:
    canonical = url.rstrip("/")
    return {
        "schema_version": 1,
        "run_id": "20260504T121000Z-weekday_digest",
        "run_date": "2026-05-04",
        "source_group": "daily_core",
        "delivery_profile": "telegram_digest",
        "enriched_items": [
            {
                "source_id": "example_source",
                "url": url,
                "canonical_url": canonical,
                "title": "Full Article",
                "published": "2026-05-04",
                "companies": ["ExampleCo"],
                "regions": ["US"],
                "topic_tags": ["portal_strategy"],
                "event_type": "product_signal",
                "priority_score": 72,
                "confidence": 0.82,
                "analyst_summary": "ExampleCo expanded a portal feature with direct marketplace implications.",
                "why_it_matters": "The change shows how portals are competing on inventory quality and agent workflow.",
                "avito_implication": "Avito should compare the feature against its professional seller tooling roadmap.",
                "story_id": "story_example_full_20260504",
                "body_status": "full",
                "article_file": ".state/articles/2026-05/2026-05-04_full-article.md",
                "evidence_points": [
                    "The article says ExampleCo expanded the portal feature.",
                    "The article links the feature to professional seller workflow."
                ],
                "source_quality": "trade_media"
            }
        ],
        "daily_brief": {
            "section_order": ["top_stories", "weak_signals"],
            "top_story_ids": ["story_example_full_20260504"],
            "weak_signal_ids": [],
            "selection_notes": ["Mixed full and fallback evidence."],
            "story_cards": [
                {
                    "story_id": "story_example_full_20260504",
                    "section": "top_stories",
                    "title": "Full Article",
                    "url": url,
                    "canonical_url": canonical,
                    "priority_score": 72,
                    "confidence": 0.82,
                    "analyst_summary": "ExampleCo expanded a portal feature with direct marketplace implications.",
                    "why_it_matters": "The change shows how portals are competing on inventory quality and agent workflow.",
                    "avito_implication": "Avito should compare the feature against its professional seller tooling roadmap.",
                    "context_refs": [],
                    "evidence_notes": ["The article says ExampleCo expanded the portal feature."]
                }
            ],
            "render_metadata": {
                "digest_status": "canonical_digest",
                "evidence_completeness": "mixed_or_full_evidence"
            }
        },
        "digest_markdown": "# PropTech Monitor | 04.05.2026\n\n## Главное\n\n1. **[Full Article](https://example.test/full)**\n   - Сигнал: ExampleCo expanded a portal feature with direct marketplace implications.\n   - Почему важно: The change shows how portals are competing on inventory quality and agent workflow.\n   - Для Avito: Avito should compare the feature against its professional seller tooling roadmap.\n   - Доказательство: The article says ExampleCo expanded the portal feature.\n\nmode: build_daily_digest | 04.05.2026\n",
        "qa_review": {
            "status": "warnings",
            "critical_findings_count": 0,
            "warning_findings_count": 1,
            "summary": "QA review found no critical issues and one source-coverage caveat."
        },
        "telegram_delivery": {
            "status": "not_configured",
            "delivered": False,
            "message_parts": 0
        }
    }


def test_materialize_finish_draft_writes_current_run_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        url = "https://example.test/full"
        shortlist_path = root / ".state/shortlists/2026-05-04/monitor_sources__20260504T120000Z__daily_core.json"
        article_result_path = root / ".state/codex-runs/20260504T121000Z-weekday_digest-article-prefetch-result.json"
        draft_path = root / ".state/codex-runs/20260504T121000Z-weekday_digest-finish-draft.json"
        write_json(shortlist_path, [shortlist_item(url)])
        write_json(article_result_path, article_prefetch_doc(url))
        write_json(draft_path, finish_draft(url))

        summary = stage_c_finish.materialize_finish(
            repo_root=root,
            run_id="20260504T121000Z-weekday_digest",
            run_date="2026-05-04",
            source_group="daily_core",
            delivery_profile="telegram_digest",
            shortlist_path=shortlist_path,
            article_prefetch_result_path=article_result_path,
            draft_path=draft_path,
        )

        assert summary["status"] == "materialized"
        assert (root / ".state/enriched/2026-05-04/scrape_and_enrich__20260504T121000Z__daily_core.json").exists()
        assert (root / ".state/runs/2026-05-04/scrape_and_enrich__20260504T121000Z__daily_core.json").exists()
        assert (root / ".state/runs/2026-05-04/build_daily_digest__20260504T121000Z__telegram_digest.json").exists()
        assert (root / ".state/briefs/daily/2026-05-04__telegram_digest.json").exists()
        assert (root / "digests/2026-05-04-daily-digest.md").exists()
        assert (root / ".state/codex-runs/20260504T121000Z-weekday_digest-finish-summary.json").exists()


def test_rejects_non_shortlisted_draft_url() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        shortlist_path = root / ".state/shortlists/2026-05-04/monitor_sources__20260504T120000Z__daily_core.json"
        article_result_path = root / ".state/codex-runs/20260504T121000Z-weekday_digest-article-prefetch-result.json"
        draft_path = root / ".state/codex-runs/20260504T121000Z-weekday_digest-finish-draft.json"
        write_json(shortlist_path, [shortlist_item("https://example.test/full")])
        write_json(article_result_path, article_prefetch_doc("https://example.test/full"))
        write_json(draft_path, finish_draft("https://example.test/not-shortlisted"))

        try:
            stage_c_finish.materialize_finish(
                repo_root=root,
                run_id="20260504T121000Z-weekday_digest",
                run_date="2026-05-04",
                source_group="daily_core",
                delivery_profile="telegram_digest",
                shortlist_path=shortlist_path,
                article_prefetch_result_path=article_result_path,
                draft_path=draft_path,
            )
        except ValueError as exc:
            assert "not in current-run shortlist" in str(exc)
        else:
            raise AssertionError("non-shortlisted draft URL should be rejected")


def test_rejects_digest_body_runtime_path_leakage() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        url = "https://example.test/full"
        shortlist_path = root / ".state/shortlists/2026-05-04/monitor_sources__20260504T120000Z__daily_core.json"
        article_result_path = root / ".state/codex-runs/20260504T121000Z-weekday_digest-article-prefetch-result.json"
        draft_path = root / ".state/codex-runs/20260504T121000Z-weekday_digest-finish-draft.json"
        draft = finish_draft(url)
        draft["digest_markdown"] += "\nInternal path: .state/articles/2026-05/2026-05-04_full-article.md\n"
        write_json(shortlist_path, [shortlist_item(url)])
        write_json(article_result_path, article_prefetch_doc(url))
        write_json(draft_path, draft)

        try:
            stage_c_finish.materialize_finish(
                repo_root=root,
                run_id="20260504T121000Z-weekday_digest",
                run_date="2026-05-04",
                source_group="daily_core",
                delivery_profile="telegram_digest",
                shortlist_path=shortlist_path,
                article_prefetch_result_path=article_result_path,
                draft_path=draft_path,
            )
        except ValueError as exc:
            assert "digest markdown contains forbidden runtime marker" in str(exc)
        else:
            raise AssertionError("runtime path leakage should be rejected")


def main() -> None:
    tests = [
        test_materialize_finish_draft_writes_current_run_artifacts,
        test_rejects_non_shortlisted_draft_url,
        test_rejects_digest_body_runtime_path_leakage,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
```

- [x] **Step 2: Run tests to verify RED**

Run:

```bash
python3 tools/test_stage_c_finish.py
```

Expected:

```text
ModuleNotFoundError: No module named 'stage_c_finish'
```

- [x] **Step 3: Commit RED test**

Run:

```bash
git add tools/test_stage_c_finish.py
git -c user.name=Codex -c user.email=codex@local commit -m "Add Stage C materializer tests"
```

Expected:

```text
[codex-runner-scraping-tooling <sha>] Add Stage C materializer tests
```

## Task 2: Implement Minimal Stage C Materializer

**Files:**
- Create: `tools/stage_c_finish.py`
- Modify: `tools/test_stage_c_finish.py` only if RED test has syntax mistakes

- [x] **Step 1: Create helper with validation and materialization**

Create `tools/stage_c_finish.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any


BODY_STATUS_VALUES = {"full", "snippet_fallback", "paywall_stub"}
SOURCE_QUALITY_VALUES = {
    "primary_source",
    "industry_analysis",
    "expert_analysis",
    "trade_media",
    "behavioral_signal",
    "mobile_store",
    "manual_blocked",
}
FORBIDDEN_DIGEST_MARKERS = [
    ".state/",
    ".state/articles/",
    "article_file",
    "__20",
    "operator notes",
    "run id",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: pathlib.Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: pathlib.Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def rel(path: pathlib.Path, repo_root: pathlib.Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def run_timestamp(run_id: str) -> str:
    return run_id.split("-", 1)[0]


def coerce_items(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "shortlisted_items", "shortlist", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    raise ValueError("expected JSON array or object containing an item list")


def url_keys(item: dict) -> set[str]:
    return {
        str(value).rstrip("/")
        for value in (item.get("url"), item.get("canonical_url"))
        if value
    }


def load_shortlisted_urls(shortlist_path: pathlib.Path) -> set[str]:
    items = [
        item for item in coerce_items(read_json(shortlist_path))
        if item.get("triage_decision") == "shortlist"
    ]
    urls: set[str] = set()
    for item in items:
        urls.update(url_keys(item))
    return urls


def load_prefetch_by_url(article_prefetch_result_path: pathlib.Path) -> dict[str, dict]:
    payload = read_json(article_prefetch_result_path)
    results = coerce_items(payload.get("results", []) if isinstance(payload, dict) else payload)
    by_url: dict[str, dict] = {}
    for item in results:
        for key in url_keys(item):
            by_url[key] = item
    return by_url


def require_keys(name: str, item: dict, keys: list[str]) -> None:
    missing = [key for key in keys if key not in item]
    if missing:
        raise ValueError(f"{name} missing required fields: {', '.join(missing)}")


def validate_digest_markdown(markdown: str) -> None:
    lowered = markdown.lower()
    for marker in FORBIDDEN_DIGEST_MARKERS:
        if marker.lower() in lowered:
            raise ValueError(f"digest markdown contains forbidden runtime marker: {marker}")


def validate_enriched_items(enriched_items: list[dict], shortlisted_urls: set[str], prefetch_by_url: dict[str, dict]) -> None:
    required = [
        "source_id",
        "url",
        "canonical_url",
        "title",
        "published",
        "companies",
        "regions",
        "topic_tags",
        "event_type",
        "priority_score",
        "confidence",
        "analyst_summary",
        "why_it_matters",
        "avito_implication",
        "story_id",
        "body_status",
        "article_file",
        "evidence_points",
        "source_quality",
    ]
    for index, item in enumerate(enriched_items):
        require_keys(f"enriched_items[{index}]", item, required)
        item_urls = url_keys(item)
        if not item_urls.intersection(shortlisted_urls):
            raise ValueError(f"enriched item url not in current-run shortlist: {item.get('url')}")
        if item["body_status"] not in BODY_STATUS_VALUES:
            raise ValueError(f"invalid body_status for {item.get('url')}: {item['body_status']}")
        if item["source_quality"] not in SOURCE_QUALITY_VALUES:
            raise ValueError(f"invalid source_quality for {item.get('url')}: {item['source_quality']}")
        if not isinstance(item["priority_score"], int) or not 0 <= item["priority_score"] <= 100:
            raise ValueError(f"priority_score must be integer 0..100 for {item.get('url')}")
        if not isinstance(item["confidence"], (int, float)) or not 0 <= float(item["confidence"]) <= 1:
            raise ValueError(f"confidence must be numeric 0..1 for {item.get('url')}")
        matched_prefetch = next((prefetch_by_url[key] for key in item_urls if key in prefetch_by_url), None)
        if matched_prefetch is None:
            raise ValueError(f"enriched item missing article prefetch match: {item.get('url')}")
        if item["body_status"] == "full":
            if matched_prefetch.get("body_status_hint") != "full":
                raise ValueError(f"full body_status without matching full prefetch entry: {item.get('url')}")
            if not item.get("article_file"):
                raise ValueError(f"full body_status requires article_file: {item.get('url')}")
        if item["body_status"] == "paywall_stub" and item.get("evidence_points"):
            raise ValueError(f"paywall_stub must not contain evidence_points: {item.get('url')}")


def validate_draft(draft: dict, run_id: str, run_date: str, source_group: str, delivery_profile: str, shortlisted_urls: set[str], prefetch_by_url: dict[str, dict]) -> None:
    require_keys(
        "finish draft",
        draft,
        [
            "schema_version",
            "run_id",
            "run_date",
            "source_group",
            "delivery_profile",
            "enriched_items",
            "daily_brief",
            "digest_markdown",
            "qa_review",
            "telegram_delivery",
        ],
    )
    if draft["schema_version"] != 1:
        raise ValueError("finish draft schema_version must be 1")
    if draft["run_id"] != run_id:
        raise ValueError("finish draft run_id does not match wrapper run_id")
    if draft["run_date"] != run_date:
        raise ValueError("finish draft run_date does not match wrapper run_date")
    if draft["source_group"] != source_group:
        raise ValueError("finish draft source_group does not match wrapper source_group")
    if draft["delivery_profile"] != delivery_profile:
        raise ValueError("finish draft delivery_profile does not match wrapper delivery_profile")
    if not isinstance(draft["enriched_items"], list) or not draft["enriched_items"]:
        raise ValueError("finish draft enriched_items must be a non-empty list")
    validate_enriched_items(draft["enriched_items"], shortlisted_urls, prefetch_by_url)
    if not isinstance(draft["daily_brief"], dict):
        raise ValueError("finish draft daily_brief must be an object")
    validate_digest_markdown(str(draft["digest_markdown"]))
    qa_review = draft["qa_review"]
    if not isinstance(qa_review, dict):
        raise ValueError("finish draft qa_review must be an object")
    if qa_review.get("status") not in {"validated", "warnings"}:
        raise ValueError("qa_review.status must be validated or warnings for production-ready Stage C")
    if int(qa_review.get("critical_findings_count", 1)) != 0:
        raise ValueError("qa_review.critical_findings_count must be 0 for production-ready Stage C")


def build_scrape_manifest(run_id: str, run_date: str, source_group: str, enriched_path: str, article_prefetch_result: str, warnings: list[str]) -> dict:
    timestamp = run_timestamp(run_id)
    full_run_id = f"scrape_and_enrich__{timestamp}__{source_group}"
    return {
        "run_id": full_run_id,
        "mode": "scrape_and_enrich",
        "started_at": now_iso(),
        "finished_at": now_iso(),
        "status": "completed",
        "inputs": [article_prefetch_result],
        "outputs": [enriched_path],
        "source_groups": [source_group],
        "counts": {},
        "warnings": warnings,
        "errors": [],
        "operator_report": {
            "enrichment": {
                "status": "completed",
                "evidence_completeness": "mixed_or_full_evidence"
            }
        },
        "notes": [f"Materialized by stage_c_finish for {run_date}."]
    }


def build_daily_brief(draft: dict, run_id: str, run_date: str, delivery_profile: str, markdown_path: str) -> dict:
    daily = dict(draft["daily_brief"])
    story_ids = [item["story_id"] for item in draft["enriched_items"]]
    daily.update({
        "brief_id": f"{run_date}__{delivery_profile}",
        "run_id": f"build_daily_digest__{run_timestamp(run_id)}__{delivery_profile}",
        "digest_date": run_date,
        "delivery_profile": delivery_profile,
        "generated_at": now_iso(),
        "story_ids": story_ids,
        "context_refs": daily.get("context_refs", []),
        "markdown_path": markdown_path,
    })
    return daily


def build_digest_manifest(run_id: str, run_date: str, delivery_profile: str, brief_path: str, markdown_path: str, draft: dict) -> dict:
    timestamp = run_timestamp(run_id)
    full_run_id = f"build_daily_digest__{timestamp}__{delivery_profile}"
    render_metadata = draft["daily_brief"].get("render_metadata", {})
    digest_status = render_metadata.get("digest_status", "non_canonical_digest")
    return {
        "run_id": full_run_id,
        "mode": "build_daily_digest",
        "started_at": now_iso(),
        "finished_at": now_iso(),
        "status": "completed",
        "inputs": [brief_path],
        "outputs": [markdown_path, brief_path],
        "delivery_profile": delivery_profile,
        "counts": {
            "story_count": len(draft["enriched_items"]),
            "top_story_count": len(draft["daily_brief"].get("top_story_ids", [])),
            "weak_signal_count": len(draft["daily_brief"].get("weak_signal_ids", [])),
        },
        "warnings": [],
        "errors": [],
        "operator_report": {
            "digest_generation": {
                "status": "generated",
                "digest_status": digest_status,
                "canonical": digest_status == "canonical_digest"
            },
            "qa_review": draft.get("qa_review", {"status": "skipped"}),
            "telegram_delivery": draft.get("telegram_delivery", {"status": "skipped", "delivered": False})
        },
        "notes": [f"Materialized by stage_c_finish for {run_date}."]
    }


def materialize_finish(
    *,
    repo_root: pathlib.Path,
    run_id: str,
    run_date: str,
    source_group: str,
    delivery_profile: str,
    shortlist_path: pathlib.Path,
    article_prefetch_result_path: pathlib.Path,
    draft_path: pathlib.Path,
) -> dict:
    repo_root = repo_root.resolve()
    timestamp = run_timestamp(run_id)
    shortlist_path = shortlist_path.resolve()
    article_prefetch_result_path = article_prefetch_result_path.resolve()
    draft_path = draft_path.resolve()
    draft = read_json(draft_path)
    shortlisted_urls = load_shortlisted_urls(shortlist_path)
    prefetch_by_url = load_prefetch_by_url(article_prefetch_result_path)
    validate_draft(draft, run_id, run_date, source_group, delivery_profile, shortlisted_urls, prefetch_by_url)

    enriched_path = repo_root / ".state" / "enriched" / run_date / f"scrape_and_enrich__{timestamp}__{source_group}.json"
    scrape_manifest_path = repo_root / ".state" / "runs" / run_date / f"scrape_and_enrich__{timestamp}__{source_group}.json"
    brief_path = repo_root / ".state" / "briefs" / "daily" / f"{run_date}__{delivery_profile}.json"
    digest_manifest_path = repo_root / ".state" / "runs" / run_date / f"build_daily_digest__{timestamp}__{delivery_profile}.json"
    markdown_path = repo_root / "digests" / f"{run_date}-daily-digest.md"
    summary_path = repo_root / ".state" / "codex-runs" / f"{run_id}-finish-summary.json"

    enriched_items = []
    for item in draft["enriched_items"]:
        enriched = dict(item)
        enriched["run_id"] = f"scrape_and_enrich__{timestamp}__{source_group}"
        enriched["enriched_at"] = now_iso()
        enriched_items.append(enriched)

    write_json(enriched_path, enriched_items)
    write_json(
        scrape_manifest_path,
        build_scrape_manifest(
            run_id,
            run_date,
            source_group,
            rel(enriched_path, repo_root),
            rel(article_prefetch_result_path, repo_root),
            [],
        ),
    )
    write_json(brief_path, build_daily_brief(draft, run_id, run_date, delivery_profile, rel(markdown_path, repo_root)))
    write_text(markdown_path, str(draft["digest_markdown"]))
    write_json(digest_manifest_path, build_digest_manifest(run_id, run_date, delivery_profile, rel(brief_path, repo_root), rel(markdown_path, repo_root), draft))

    summary = {
        "status": "materialized",
        "run_id": run_id,
        "run_timestamp": timestamp,
        "run_date": run_date,
        "source_group": source_group,
        "delivery_profile": delivery_profile,
        "enriched_count": len(enriched_items),
        "outputs": {
            "enriched_path": rel(enriched_path, repo_root),
            "scrape_manifest_path": rel(scrape_manifest_path, repo_root),
            "daily_brief_path": rel(brief_path, repo_root),
            "digest_manifest_path": rel(digest_manifest_path, repo_root),
            "markdown_path": rel(markdown_path, repo_root),
            "summary_path": rel(summary_path, repo_root),
        }
    }
    write_json(summary_path, summary)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize deterministic Stage C finish artifacts")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-date", required=True)
    parser.add_argument("--source-group", required=True)
    parser.add_argument("--delivery-profile", required=True)
    parser.add_argument("--shortlist-path", required=True)
    parser.add_argument("--article-prefetch-result", required=True)
    parser.add_argument("--draft-path", required=True)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        summary = materialize_finish(
            repo_root=pathlib.Path(args.repo_root),
            run_id=args.run_id,
            run_date=args.run_date,
            source_group=args.source_group,
            delivery_profile=args.delivery_profile,
            shortlist_path=pathlib.Path(args.shortlist_path),
            article_prefetch_result_path=pathlib.Path(args.article_prefetch_result),
            draft_path=pathlib.Path(args.draft_path),
        )
        if args.pretty:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(summary, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        print(f"stage c finish failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [x] **Step 2: Run tests to verify GREEN**

Run:

```bash
python3 tools/test_stage_c_finish.py
```

Expected:

```text
3 tests passed
```

- [x] **Step 3: Run compile check**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache-local python3 -m py_compile tools/stage_c_finish.py tools/test_stage_c_finish.py
```

Expected: exit code `0`, no output.

- [x] **Step 4: Commit implementation**

Run:

```bash
git add tools/stage_c_finish.py tools/test_stage_c_finish.py
git -c user.name=Codex -c user.email=codex@local commit -m "Add deterministic Stage C finish materializer"
```

Expected:

```text
[codex-runner-scraping-tooling <sha>] Add deterministic Stage C finish materializer
```

## Task 3: Wire Wrapper Draft and Materializer Handoff

**Files:**
- Modify: `ops/codex-cli/run_schedule.sh`
- Modify: `tools/test_codex_cli_run_schedule.py`

- [x] **Step 1: Add failing wrapper tests**

Modify `tools/test_codex_cli_run_schedule.py` by adding this test after
`test_wrapper_validates_current_run_finish_artifacts`:

```python
def test_wrapper_invokes_stage_c_materializer_after_finish_agent() -> None:
    wrapper_text = WRAPPER.read_text(encoding="utf-8")

    assert "STAGE_C_FINISH_HELPER" in wrapper_text
    assert "tools/stage_c_finish.py" in wrapper_text
    assert "FINISH_DRAFT" in wrapper_text
    assert "finish-draft.json" in wrapper_text
    assert "finish-summary.json" in wrapper_text
    assert "stage_c_finish.py" in wrapper_text
    assert "--draft-path \"$FINISH_DRAFT\"" in wrapper_text
    assert "--article-prefetch-result \"$ARTICLE_PREFETCH_RESULT\"" in wrapper_text
    assert "validate-finish-artifacts" in wrapper_text
```

Add the test to the `tests = [...]` list:

```python
        test_wrapper_validates_current_run_finish_artifacts,
        test_wrapper_invokes_stage_c_materializer_after_finish_agent,
        test_readme_documents_staged_victory_digest_runbook,
```

- [x] **Step 2: Run wrapper tests to verify RED**

Run:

```bash
python3 tools/test_codex_cli_run_schedule.py
```

Expected:

```text
AssertionError
```

from `test_wrapper_invokes_stage_c_materializer_after_finish_agent`.

- [x] **Step 3: Modify wrapper variables**

In `ops/codex-cli/run_schedule.sh`, add these variables near the existing
`ARTICLE_PREFETCH_*` variables:

```bash
FINISH_DRAFT="$RUN_ROOT/$RUN_ID-finish-draft.json"
FINISH_SUMMARY="$RUN_ROOT/$RUN_ID-finish-summary.json"
```

Add this helper variable near `ARTICLE_PREFETCH_HELPER`:

```bash
STAGE_C_FINISH_HELPER="$REPO_ROOT/tools/stage_c_finish.py"
```

Add this self-test line after `Stage C prompt`:

```bash
  printf 'Stage C materializer: %s\n' "$STAGE_C_FINISH_HELPER"
```

- [x] **Step 4: Extend generated finish prompt with draft path**

In `build_finish_prompt()`, after the article prefetch summary line, add:

```bash
    printf '%s\n' "- Finish draft path: \`$FINISH_DRAFT\`"
    printf '%s\n\n' "- Finish summary path: \`$FINISH_SUMMARY\`"
```

- [x] **Step 5: Validate helper exists before Stage C**

In `run_weekday_staged_schedule()`, after the `ARTICLE_PREFETCH_HELPER` existence
check, add:

```bash
  if [ ! -f "$STAGE_C_FINISH_HELPER" ]; then
    printf 'Stage C finish helper not found: %s\n' "$STAGE_C_FINISH_HELPER" >&2
    exit 2
  fi
```

- [x] **Step 6: Call materializer after Codex Stage C**

Immediately after the Stage C `codex exec` command and before
`validate-finish-artifacts`, add:

```bash
  python3 "$STAGE_C_FINISH_HELPER" \
    --repo-root "$REPO_ROOT" \
    --run-id "$RUN_ID" \
    --run-date "$RUN_DATE" \
    --source-group daily_core \
    --delivery-profile telegram_digest \
    --shortlist-path "$SHORTLIST_PATH" \
    --article-prefetch-result "$ARTICLE_PREFETCH_RESULT" \
    --draft-path "$FINISH_DRAFT" \
    --pretty > "$FINISH_SUMMARY"
```

- [x] **Step 7: Print finish summary path**

After the existing `printf 'Article prefetch summary...'` line, add:

```bash
  printf 'Finish materializer summary: %s\n' "$FINISH_SUMMARY"
```

- [x] **Step 8: Run wrapper tests to verify GREEN**

Run:

```bash
python3 tools/test_codex_cli_run_schedule.py
```

Expected:

```text
13 tests passed
```

- [x] **Step 9: Run shell syntax check**

Run:

```bash
bash -n ops/codex-cli/run_schedule.sh
```

Expected: exit code `0`, no output.

- [x] **Step 10: Commit wrapper wiring**

Run:

```bash
git add ops/codex-cli/run_schedule.sh tools/test_codex_cli_run_schedule.py
git -c user.name=Codex -c user.email=codex@local commit -m "Wire Stage C finish materializer"
```

Expected:

```text
[codex-runner-scraping-tooling <sha>] Wire Stage C finish materializer
```

## Task 4: Update Stage C Prompt Contract

**Files:**
- Modify: `ops/codex-cli/prompts/weekday_digest_finish.md`
- Modify: `tools/test_codex_cli_run_schedule.py`

- [x] **Step 1: Add failing prompt assertions**

Extend `test_staged_prompt_files_exist_and_have_stage_boundaries()` in
`tools/test_codex_cli_run_schedule.py` with:

```python
    assert "Finish draft path" in finish_text
    assert "schema_version" in finish_text
    assert "digest_markdown" in finish_text
    assert "Do not write final .state/enriched" in finish_text
```

- [x] **Step 2: Run tests to verify RED**

Run:

```bash
python3 tools/test_codex_cli_run_schedule.py
```

Expected: `AssertionError` from the new prompt assertions.

- [x] **Step 3: Replace Stage C output instructions**

Modify `ops/codex-cli/prompts/weekday_digest_finish.md` so the output section
contains this exact contract:

```markdown
## Required Finish Draft

Write exactly one compact JSON draft to the generated prompt's `Finish draft path`.
Do not write final `.state/enriched`, `.state/runs`, `.state/briefs`, or
`digests/*.md` artifacts directly. The wrapper will validate and materialize
those files through `tools/stage_c_finish.py`.

The draft JSON must contain:

- `schema_version: 1`
- `run_id`
- `run_date`
- `source_group`
- `delivery_profile`
- `enriched_items`
- `daily_brief`
- `digest_markdown`
- `qa_review`
- `telegram_delivery`

Each `enriched_items[]` entry must match a current-run shortlisted URL and a
current-run article prefetch result entry by `url` or `canonical_url`.

For `body_status = full`, include the matched `article_file` path from the
article prefetch result. For `snippet_fallback` or `paywall_stub`, keep
`article_file` null unless the prefetch result explicitly provides a safe file.

`digest_markdown` must be final human-readable digest markdown. It must not
contain `.state/`, `.state/articles/`, `article_file`, timestamped run ids,
operator notes, or full article bodies.

`qa_review.status` must be `validated` or `warnings`; `skipped` is not
acceptable for a 95% production-ready test-run. `critical_findings_count` must
be `0`.
```

- [x] **Step 4: Run tests to verify GREEN**

Run:

```bash
python3 tools/test_codex_cli_run_schedule.py
```

Expected:

```text
13 tests passed
```

- [x] **Step 5: Commit prompt contract**

Run:

```bash
git add ops/codex-cli/prompts/weekday_digest_finish.md tools/test_codex_cli_run_schedule.py
git -c user.name=Codex -c user.email=codex@local commit -m "Require Stage C finish draft contract"
```

Expected:

```text
[codex-runner-scraping-tooling <sha>] Require Stage C finish draft contract
```

## Task 5: Tighten Finish Artifact Validation

**Files:**
- Modify: `tools/codex_schedule_artifacts.py`
- Modify: `tools/test_codex_schedule_artifacts.py`

- [x] **Step 1: Add failing validation test**

Add this test to `tools/test_codex_schedule_artifacts.py` after
`test_validate_finish_artifacts_requires_current_run_manifests()`:

```python
def test_validate_finish_artifacts_requires_finish_summary_when_requested() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        run_id = "20260504T121000Z-weekday_digest"
        write_json(
            root / ".state/enriched/2026-05-04/scrape_and_enrich__20260504T121000Z__daily_core.json",
            [],
        )
        write_json(
            root / ".state/runs/2026-05-04/scrape_and_enrich__20260504T121000Z__daily_core.json",
            {"run_id": "scrape_and_enrich__20260504T121000Z__daily_core"},
        )
        write_json(
            root / ".state/runs/2026-05-04/build_daily_digest__20260504T121000Z__telegram_digest.json",
            {"run_id": "build_daily_digest__20260504T121000Z__telegram_digest"},
        )
        write_json(
            root / ".state/briefs/daily/2026-05-04__telegram_digest.json",
            {"brief_id": "2026-05-04__telegram_digest"},
        )

        try:
            codex_schedule_artifacts.validate_finish_artifacts(
                repo_root=root,
                run_id=run_id,
                run_date="2026-05-04",
                source_group="daily_core",
                delivery_profile="telegram_digest",
                require_finish_summary=True,
            )
        except FileNotFoundError as exc:
            assert "finish-summary.json" in str(exc)
        else:
            raise AssertionError("missing finish summary should fail when required")
```

Add the test to the list:

```python
        test_validate_finish_artifacts_requires_current_run_manifests,
        test_validate_finish_artifacts_requires_finish_summary_when_requested,
```

- [x] **Step 2: Run tests to verify RED**

Run:

```bash
python3 tools/test_codex_schedule_artifacts.py
```

Expected:

```text
TypeError: validate_finish_artifacts() got an unexpected keyword argument 'require_finish_summary'
```

- [x] **Step 3: Extend validation helper**

Change the `validate_finish_artifacts` signature in
`tools/codex_schedule_artifacts.py` to:

```python
def validate_finish_artifacts(
    *,
    repo_root: pathlib.Path,
    run_id: str,
    run_date: str,
    source_group: str,
    delivery_profile: str,
    require_finish_summary: bool = False,
) -> dict:
```

Before computing `missing`, append this path when requested:

```python
    if require_finish_summary:
        required_paths.append(repo_root / ".state" / "codex-runs" / f"{run_id}-finish-summary.json")
```

Add CLI flag:

```python
    validate_finish.add_argument("--require-finish-summary", action="store_true")
```

Pass it in `main()`:

```python
                require_finish_summary=args.require_finish_summary,
```

- [x] **Step 4: Update wrapper validation call**

In `ops/codex-cli/run_schedule.sh`, add this flag to the existing
`validate-finish-artifacts` command:

```bash
    --require-finish-summary
```

- [x] **Step 5: Run tests to verify GREEN**

Run:

```bash
python3 tools/test_codex_schedule_artifacts.py
python3 tools/test_codex_cli_run_schedule.py
```

Expected:

```text
5 tests passed
13 tests passed
```

- [x] **Step 6: Commit validation tightening**

Run:

```bash
git add tools/codex_schedule_artifacts.py tools/test_codex_schedule_artifacts.py ops/codex-cli/run_schedule.sh
git -c user.name=Codex -c user.email=codex@local commit -m "Require Stage C finish summary validation"
```

Expected:

```text
[codex-runner-scraping-tooling <sha>] Require Stage C finish summary validation
```

## Task 6: Document Operator Runbook and Tool Surface

**Files:**
- Modify: `ops/codex-cli/README.md`
- Modify: `tools/README.md`
- Modify: `docs/run-reviews/2026-05-04-victory-digest-completion-audit.md`
- Modify: `PLANS.md`

- [x] **Step 1: Update operator README**

In `ops/codex-cli/README.md`, add this paragraph after the Stage C validation
paragraph:

```markdown
Stage C has a strict IO boundary. The inner Codex agent writes one compact
finish draft under `.state/codex-runs/*-finish-draft.json`; the wrapper then
runs `tools/stage_c_finish.py` to materialize `.state/enriched`,
`.state/runs`, `.state/briefs`, and `digests/{date}-daily-digest.md`.
If the draft is missing, stale, invalid, or leaks runtime paths into the digest
body, the wrapper fails before delivery.
```

- [x] **Step 2: Update tools README**

In `tools/README.md`, add this table row after `codex_schedule_artifacts.py`:

```markdown
| `stage_c_finish.py` | Deterministic Stage C materializer that validates compact finish drafts and writes current-run enrichment, daily brief, digest markdown, and run manifests. |
```

- [x] **Step 3: Update completion audit follow-up status**

In `docs/run-reviews/2026-05-04-victory-digest-completion-audit.md`, add this
section before `## Follow-Ups`:

```markdown
## Deterministic Stage C Plan

Follow-up work is tracked in
`docs/superpowers/plans/2026-05-04-deterministic-stage-c-finish.md`.
The intended fix is to keep Codex responsible for compact analysis, but move
artifact writes to `tools/stage_c_finish.py`.
```

- [x] **Step 4: Update active plan index**

In `PLANS.md`, add a row to the active plan table:

```markdown
| Deterministic Stage C Finish | active; planned | `docs/superpowers/plans/2026-05-04-deterministic-stage-c-finish.md` | Make Stage C emit a strict compact draft and materialize current-run enrichment/digest artifacts through a deterministic helper. |
```

- [x] **Step 5: Run documentation checks**

Run:

```bash
rg -n "stage_c_finish.py|finish-draft|Deterministic Stage C Finish" ops/codex-cli/README.md tools/README.md docs/run-reviews/2026-05-04-victory-digest-completion-audit.md PLANS.md
```

Expected output includes all four files.

- [x] **Step 6: Commit docs**

Run:

```bash
git add ops/codex-cli/README.md tools/README.md docs/run-reviews/2026-05-04-victory-digest-completion-audit.md PLANS.md
git -c user.name=Codex -c user.email=codex@local commit -m "Document deterministic Stage C finish path"
```

Expected:

```text
[codex-runner-scraping-tooling <sha>] Document deterministic Stage C finish path
```

## Task 7: Offline Gate and Wrapper Self-Test

**Files:**
- No code changes unless a verification failure identifies a concrete bug.

- [x] **Step 1: Run Stage C helper tests**

Run:

```bash
python3 tools/test_stage_c_finish.py
```

Expected:

```text
3 tests passed
```

- [x] **Step 2: Run schedule artifact tests**

Run:

```bash
python3 tools/test_codex_schedule_artifacts.py
```

Expected:

```text
5 tests passed
```

- [x] **Step 3: Run wrapper tests**

Run:

```bash
python3 tools/test_codex_cli_run_schedule.py
```

Expected:

```text
13 tests passed
```

- [x] **Step 4: Run runtime validators**

Run:

```bash
python3 tools/test_validate_runtime_artifacts.py
python3 tools/validate_runtime_artifacts.py --check all
```

Expected output includes:

```text
PASS  all
```

- [x] **Step 5: Run compile and shell checks**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache-local python3 -m py_compile tools/stage_c_finish.py tools/test_stage_c_finish.py tools/codex_schedule_artifacts.py tools/test_codex_schedule_artifacts.py tools/test_codex_cli_run_schedule.py
bash -n ops/codex-cli/run_schedule.sh
git diff --check
```

Expected: all commands exit `0`.

- [x] **Step 6: Run wrapper self-test**

Run:

```bash
CODEX_ENV_FILE=/private/tmp/codex-empty-env CODEX_RUN_SCHEDULE_SELF_TEST=1 ops/codex-cli/run_schedule.sh weekday_digest
```

Expected output includes:

```text
Wrapper self-test passed: weekday_digest
Stage C materializer:
Codex exec flags: -C --cd, -s --sandbox, --json, --output-last-message
```

- [x] **Step 7: Commit verification note if docs changed**

If a verification note is added to a docs file, commit it:

```bash
git add docs/run-reviews/2026-05-04-victory-digest-completion-audit.md
git -c user.name=Codex -c user.email=codex@local commit -m "Record deterministic Stage C offline gate"
```

If no docs changed, do not create an empty commit.

## Task 8: Production-Like Victory Rerun

**Files:**
- Modify after run: `docs/run-reviews/2026-05-04-weekday-digest.md`
- Modify after run: `docs/run-reviews/2026-05-04-victory-digest-completion-audit.md`
- Modify after run: `PLANS.md`

- [x] **Step 1: Run production-like wrapper with empty env**

Run:

```bash
CODEX_ENV_FILE=/private/tmp/codex-empty-env ops/codex-cli/run_schedule.sh weekday_digest
```

Expected:

- The wrapper may require elevated execution because inner `codex exec` needs access to `~/.codex`.
- If sandbox denial occurs, rerun with an approved escalation through the Codex tool policy.
- The run either reaches `Codex schedule run complete: <run_id>` or fails with a clear `stage c finish failed:` message.

- [x] **Step 2: Inspect latest run artifacts**

Run:

```bash
find .state/codex-runs -maxdepth 1 -type f | sort | tail -n 40
find .state/enriched/2026-05-04 -maxdepth 1 -type f | sort | tail -n 10
find .state/runs/2026-05-04 -maxdepth 1 -type f | sort | tail -n 20
```

Expected successful run includes files matching:

```text
.state/codex-runs/<run_id>-finish-draft.json
.state/codex-runs/<run_id>-finish-summary.json
.state/enriched/2026-05-04/scrape_and_enrich__<timestamp>__daily_core.json
.state/runs/2026-05-04/scrape_and_enrich__<timestamp>__daily_core.json
.state/runs/2026-05-04/build_daily_digest__<timestamp>__telegram_digest.json
```

- [x] **Step 3: Validate current-run finish artifacts**

Replace `<run_id>` with the latest wrapper run id:

```bash
python3 tools/codex_schedule_artifacts.py validate-finish-artifacts \
  --repo-root . \
  --run-id <run_id> \
  --run-date 2026-05-04 \
  --source-group daily_core \
  --delivery-profile telegram_digest \
  --require-finish-summary
```

Expected successful output:

```json
{"status": "ok", "run_id": "<run_id>", "run_timestamp": "<timestamp>", "required_paths": [...]}
```

- [x] **Step 4: Run digest safety scans**

Run:

```bash
rg -n -- '\.state/|__[0-9]{8}T[0-9]{6}Z__|operator notes|run id|article_file' digests/2026-05-04-daily-digest.md
rg -n -P 'https://api\.telegram\.org/bot[0-9]+:[A-Za-z0-9_-]+|/bot[0-9]+:[A-Za-z0-9_-]+' docs/run-reviews ops/codex-cli/README.md
```

Expected: no matches.

- [x] **Step 5: Update run review**

In `docs/run-reviews/2026-05-04-weekday-digest.md`, update `Victory Run` with:

```markdown
| Stage C finish | `materialized` | deterministic materializer wrote current-run enriched shard, scrape manifest, daily brief, digest manifest, digest markdown, and finish summary. |
```

If the run failed, record the exact failure class instead:

```markdown
| Stage C finish | `failed` | materializer failed with `<sanitized error class>` before writing current-run digest artifacts. |
```

- [x] **Step 6: Update completion audit**

In `docs/run-reviews/2026-05-04-victory-digest-completion-audit.md`, update
the verdict:

```markdown
Status: deterministic Stage C implemented; live rerun status: `<success_or_failure>`.
```

Use `success` only if `validate-finish-artifacts --require-finish-summary`
passed and digest safety scans returned no matches.

- [x] **Step 7: Update plan index**

In `PLANS.md`, change the deterministic Stage C row status to one of:

```markdown
completed through offline gate; live rerun pending
```

or:

```markdown
completed; live rerun passed
```

or:

```markdown
implemented; live rerun blocked by <sanitized blocker>
```

- [x] **Step 8: Commit live run review**

Run:

```bash
git add docs/run-reviews/2026-05-04-weekday-digest.md docs/run-reviews/2026-05-04-victory-digest-completion-audit.md PLANS.md
git -c user.name=Codex -c user.email=codex@local commit -m "Record deterministic Stage C Victory rerun"
```

Expected:

```text
[codex-runner-scraping-tooling <sha>] Record deterministic Stage C Victory rerun
```

## Task 9: 95% Production-Ready Acceptance Gate

**Files:**
- Modify after gate: `docs/run-reviews/2026-05-04-weekday-digest.md`
- Modify after gate: `docs/run-reviews/2026-05-04-victory-digest-completion-audit.md`
- Modify after gate: `PLANS.md`

- [x] **Step 1: Identify the latest successful wrapper run id**

Run:

```bash
find .state/codex-runs -maxdepth 1 -type f -name '*-finish-summary.json' | sort | tail -n 1
```

Expected output shape:

```text
.state/codex-runs/<run_id>-finish-summary.json
```

Set `<run_id>` from the filename before `-finish-summary.json`.

- [x] **Step 2: Validate finish artifacts with summary required**

Run:

```bash
python3 tools/codex_schedule_artifacts.py validate-finish-artifacts \
  --repo-root . \
  --run-id <run_id> \
  --run-date 2026-05-04 \
  --source-group daily_core \
  --delivery-profile telegram_digest \
  --require-finish-summary
```

Expected: exit code `0` and JSON with `"status": "ok"`.

- [x] **Step 3: Validate article prefetch readiness**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path

run_id = "<run_id>"
summary = json.loads(Path(f".state/codex-runs/{run_id}-article-prefetch-summary.json").read_text())
assert summary["run_failure"] is None, summary
assert summary["attempted_count"] == summary["shortlisted_count"], summary
assert summary["full_count"] > 0, summary
assert summary["snippet_fallback_count"] < summary["shortlisted_count"], summary
print("article_prefetch_gate=pass")
PY
```

Expected:

```text
article_prefetch_gate=pass
```

- [x] **Step 4: Validate QA readiness**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path

run_id = "<run_id>"
draft = json.loads(Path(f".state/codex-runs/{run_id}-finish-draft.json").read_text())
qa = draft["qa_review"]
assert qa["status"] in {"validated", "warnings"}, qa
assert qa["critical_findings_count"] == 0, qa
print("qa_gate=pass")
PY
```

Expected:

```text
qa_gate=pass
```

- [x] **Step 5: Run digest safety scans**

Run:

```bash
rg -n -- '\.state/|__[0-9]{8}T[0-9]{6}Z__|operator notes|run id|article_file' digests/2026-05-04-daily-digest.md
rg -n -P 'https://api\.telegram\.org/bot[0-9]+:[A-Za-z0-9_-]+|/bot[0-9]+:[A-Za-z0-9_-]+' digests/2026-05-04-daily-digest.md docs/run-reviews ops/codex-cli/README.md
```

Expected: both commands return no matches.

- [x] **Step 6: Run Telegram dry-run delivery check**

Run:

```bash
python3 tools/telegram_send.py \
  --profile telegram_digest \
  --date 2026-05-04 \
  --dry-run < digests/2026-05-04-daily-digest.md
```

Expected JSON includes:

```json
{
  "dry_run": true,
  "parts_sent": 1,
  "errors": []
}
```

`parts_sent` may be greater than `1` for a long digest, but it must be at least
`1`, and `errors` must be an empty list.

- [x] **Step 7: Record 95% verdict**

If Steps 2-6 all pass, update
`docs/run-reviews/2026-05-04-weekday-digest.md` with:

```markdown
| 95% production-ready gate | `production_candidate_95` | current-run artifacts validated, article prefetch gate passed, QA had zero critical findings, digest safety scans passed, and Telegram dry-run rendered successfully. |
```

If any step fails, update the same table with:

```markdown
| 95% production-ready gate | `failed` | blocker: `<sanitized blocker>` |
```

- [x] **Step 8: Update audit and plan index**

If the gate passed, update
`docs/run-reviews/2026-05-04-victory-digest-completion-audit.md` with:

```markdown
Status: deterministic Stage C implemented; live rerun passed the 95% production-ready gate.
```

Update `PLANS.md`:

```markdown
| Deterministic Stage C Finish | completed; live rerun passed 95% production-ready gate | `docs/superpowers/plans/2026-05-04-deterministic-stage-c-finish.md` | Stage C emits a strict compact draft and deterministic materializer writes current-run enrichment/digest artifacts. |
```

- [x] **Step 9: Commit 95% gate result**

Run:

```bash
git add docs/run-reviews/2026-05-04-weekday-digest.md docs/run-reviews/2026-05-04-victory-digest-completion-audit.md PLANS.md
git -c user.name=Codex -c user.email=codex@local commit -m "Record Victory Digest 95 percent readiness gate"
```

Expected:

```text
[codex-runner-scraping-tooling <sha>] Record Victory Digest 95 percent readiness gate
```

## Self-Review

Spec coverage:

- Current-run artifact gap is covered by Tasks 1, 2, 3, and 5.
- Stage C over-agentic filesystem writes are covered by Tasks 3 and 4.
- Digest body leakage risk is covered by Tasks 1, 2, and 8.
- Offline verification is covered by Task 7.
- Live production-like rerun is covered by Task 8.
- The 95% production-ready test-run verdict is covered by Task 9.
- Run review and completion audit are covered by Tasks 6 and 8.

Placeholder scan:

- No deferred-work markers or unspecified test instructions are used.
- Code snippets include concrete function names, paths, and expected outputs.

Type consistency:

- `run_id`, `run_date`, `source_group`, `delivery_profile`, `enriched_items`,
  `daily_brief`, `digest_markdown`, `qa_review`, and `telegram_delivery` are
  used consistently in tests, helper code, wrapper handoff, and prompt contract.
