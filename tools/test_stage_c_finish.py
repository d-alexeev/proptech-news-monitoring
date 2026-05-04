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
        "raw_snippet": "Snippet remains available.",
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
            "summary_path": ".state/codex-runs/20260504T121000Z-weekday_digest-article-prefetch-summary.json",
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
                "http": {"status": 200},
            }
        ],
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
                    "The article links the feature to professional seller workflow.",
                ],
                "source_quality": "trade_media",
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
                    "evidence_notes": ["The article says ExampleCo expanded the portal feature."],
                }
            ],
            "render_metadata": {
                "digest_status": "canonical_digest",
                "evidence_completeness": "mixed_or_full_evidence",
            },
        },
        "digest_markdown": "# PropTech Monitor | 04.05.2026\n\n## Главное\n\n1. **[Full Article](https://example.test/full)**\n   - Сигнал: ExampleCo expanded a portal feature with direct marketplace implications.\n   - Почему важно: The change shows how portals are competing on inventory quality and agent workflow.\n   - Для Avito: Avito should compare the feature against its professional seller tooling roadmap.\n   - Доказательство: The article says ExampleCo expanded the portal feature.\n\nmode: build_daily_digest | 04.05.2026\n",
        "qa_review": {
            "status": "warnings",
            "critical_findings_count": 0,
            "warning_findings_count": 1,
            "summary": "QA review found no critical issues and one source-coverage caveat.",
        },
        "telegram_delivery": {
            "status": "not_configured",
            "delivered": False,
            "message_parts": 0,
        },
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
