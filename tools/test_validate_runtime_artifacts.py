#!/usr/bin/env python3
"""
Offline contract tests for validate_runtime_artifacts.py.

Run with:
  python3 tools/test_validate_runtime_artifacts.py
"""
from __future__ import annotations

import pathlib
import tempfile

import yaml

import validate_runtime_artifacts as validator


def write_yaml(path: pathlib.Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_adapter_validation_requires_configured_sources_to_resolve() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        write_yaml(
            root / "config/runtime/source-groups/daily_core.yaml",
            {"sources": [{"id": "known_source"}, {"id": "missing_source"}]},
        )
        write_yaml(root / "config/runtime/source-groups/weekly_context.yaml", {"sources": []})
        (root / "cowork/adapters").mkdir(parents=True)
        (root / "cowork/adapters/known.md").write_text("adapter", encoding="utf-8")
        (root / "cowork/adapters/source_map.md").write_text(
            "| source_id | adapter | note |\n"
            "| --- | --- | --- |\n"
            "| `known_source` | `cowork/adapters/known.md` | fixture |\n",
            encoding="utf-8",
        )

        errors = validator.check_adapters(root)

    assert any("missing_source" in error for error in errors)


def test_fixture_validation_reports_missing_required_fields() -> None:
    schema = {
        "artifacts": {
            "raw_candidate": {
                "required_fields": [
                    {"name": "run_id", "type": "string"},
                    {"name": "fetch_strategy", "type": "enum[rss,html_scrape]"},
                ]
            }
        }
    }
    fixture = {"artifacts": {"raw_candidate": {"run_id": "run_1"}}}

    errors = validator.validate_artifact_fixture(
        schema,
        fixture,
        ["raw_candidate"],
        "fixture.yaml",
    )

    assert any("fetch_strategy" in error for error in errors)


def test_full_text_boundary_allows_enrichment_but_blocks_monitor_sources() -> None:
    forbidden_fixture = {
        "fixture_id": "bad_monitor",
        "mode_id": "monitor_sources",
        "inputs": {"candidate": {"source_id": "zillow", "article_file": ".state/articles/a.md"}},
    }
    allowed_fixture = {
        "fixture_id": "good_enrichment",
        "mode_id": "scrape_and_enrich",
        "inputs": {"body_word_count": 640, "article_file": ".state/articles/a.md"},
    }

    bad_errors = validator.find_full_text_violations(
        forbidden_fixture,
        pathlib.Path("monitor_sources_bad.yaml"),
    )
    good_errors = validator.find_full_text_violations(
        allowed_fixture,
        pathlib.Path("scrape_and_enrich_good.yaml"),
    )

    assert any("article_file" in error for error in bad_errors)
    assert good_errors == []


def test_enrichment_boundary_blocks_full_text_on_non_shortlisted_sections() -> None:
    fixture = {
        "fixture_id": "bad_enrichment_guard",
        "mode_id": "scrape_and_enrich",
        "inputs": {
            "raw_candidates_not_shortlisted": [
                {
                    "source_id": "redfin_news",
                    "url": "https://example.test/not-shortlisted",
                    "triage_decision": "drop",
                    "body": "This body must not be available for non-shortlisted input.",
                }
            ]
        },
        "expected": {
            "forbidden_fetch_urls": ["https://example.test/not-shortlisted"],
            "article_file": ".state/articles/non-shortlisted.md",
        },
    }

    errors = validator.find_full_text_violations(
        fixture,
        pathlib.Path("scrape_and_enrich_non_shortlisted_bad.yaml"),
    )

    assert any("non-shortlisted" in error or "forbidden_fetch_urls" in error for error in errors)
    assert any("body" in error or "article_file" in error for error in errors)


def test_mode_fixture_embedded_change_request_requires_schema_fields() -> None:
    schema = {
        "artifacts": {
            "change_request": {
                "required_fields": [
                    {"name": "request_id", "type": "string"},
                    {"name": "failure_type", "type": "enum[adapter_gap,scrape_failure]"},
                    {"name": "source_id", "type": "string_or_null"},
                ]
            }
        }
    }
    fixture = {
        "fixture_id": "bad_change_request_fixture",
        "mode_id": "scrape_and_enrich",
        "expected": {
            "action": "emit_change_request",
            "change_request": {
                "request_id": "change_request__fixture",
                "source_id": "zillow_newsroom",
            },
        },
    }

    errors = validator.validate_mode_fixture_change_requests(
        schema,
        fixture,
        pathlib.Path("scrape_and_enrich_bad_cr.yaml"),
    )

    assert any("failure_type" in error for error in errors)


def test_mode_fixture_metadata_change_request_requires_reviewable_fields() -> None:
    schema = {
        "artifacts": {
            "change_request": {
                "required_fields": [
                    {"name": "request_id", "type": "string"},
                    {"name": "failure_type", "type": "enum[adapter_gap,scrape_failure]"},
                    {"name": "source_id", "type": "string_or_null"},
                ]
            }
        }
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        write_yaml(
            root / "config/runtime/mode-fixtures/scrape_and_enrich_bad_metadata_cr.yaml",
            {
                "fixture_id": "scrape_and_enrich_bad_metadata_change_request",
                "mode_id": "scrape_and_enrich",
                "inputs": {
                    "run_id": "scrape_and_enrich__fixture",
                    "stage": "full_text_fetch",
                },
                "expected": {
                    "action": "emit_change_request",
                    "change_request_output_path": ".state/change-requests/bad.json",
                    "required_fields": ["run_id", "mode", "stage"],
                },
            },
        )

        errors = validator.check_mode_fixture_change_requests(schema, root)

    assert any("failure_type" in error for error in errors)
    assert any("source_id" in error for error in errors)
    assert any("suggested_target_files/tests_to_add" in error for error in errors)


def test_runner_integration_validation_requires_complete_strategy_map() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        write_yaml(
            root / "config/runtime/source-groups/daily_core.yaml",
            {
                "group_id": "daily_core",
                "sources": [
                    {
                        "id": "inman_tech_innovation",
                        "fetch_strategy": "rss",
                        "rss_feed": "https://feeds.feedburner.com/inmannews",
                    },
                    {
                        "id": "blocked_manual_source_example",
                        "fetch_strategy": "blocked",
                        "blocked_mode": "manual_only_permanent",
                        "landing_urls": ["https://example.test/manual-only"],
                    },
                ],
            },
        )
        write_yaml(root / "config/runtime/source-groups/weekly_context.yaml", {"group_id": "weekly_context", "sources": []})
        write_yaml(root / "config/runtime/mode-fixtures/runner_fetcher_contract_inman.yaml", {"fixture_id": "fetcher"})
        write_yaml(root / "config/runtime/mode-fixtures/monitor_sources_blocked_manual_change_request.yaml", {"fixture_id": "blocked"})
        write_yaml(
            root / "config/runtime/mode-fixtures/runner_integration_map.yaml",
            {
                "fixture_id": "runner_integration_map",
                "sources": [
                    {
                        "group_id": "daily_core",
                        "source_id": "inman_tech_innovation",
                        "fetch_strategy": "rss",
                        "primary_tool_path": "Browser fallback",
                        "invocation_kind": "rss",
                        "invocation_url_field": "rss_feed",
                        "adapter": "none",
                        "optional_fallback": None,
                        "manual_policy": None,
                        "fixture_coverage": "config/runtime/mode-fixtures/runner_fetcher_contract_inman.yaml",
                        "live_residual_risk": "Feed could be unavailable during live RT-M7.",
                    },
                    {
                        "group_id": "daily_core",
                        "source_id": "blocked_manual_source_example",
                        "fetch_strategy": "blocked",
                        "primary_tool_path": "No fetch / manual intake policy",
                        "invocation_kind": "browser",
                        "invocation_url_field": "landing_urls",
                        "adapter": "cowork/adapters/blocked_manual_access.md",
                        "optional_fallback": None,
                        "manual_policy": "manual_only_permanent",
                        "fixture_coverage": "config/runtime/mode-fixtures/monitor_sources_blocked_manual_change_request.yaml",
                        "live_residual_risk": "Manual intake remains outside automated runner fetch.",
                    },
                ],
            },
        )

        errors = validator.check_runner_integration(root)

    assert any("inman_tech_innovation" in error and "HTTP/RSS fetcher" in error for error in errors)
    assert any("blocked_manual_source_example" in error and "must not define fetch invocation" in error for error in errors)


def test_runner_integration_validation_rejects_empty_fixture_coverage() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        write_yaml(
            root / "config/runtime/source-groups/daily_core.yaml",
            {
                "group_id": "daily_core",
                "sources": [
                    {
                        "id": "inman_tech_innovation",
                        "fetch_strategy": "rss",
                        "rss_feed": "https://feeds.feedburner.com/inmannews",
                    }
                ],
            },
        )
        write_yaml(
            root / "config/runtime/source-groups/weekly_context.yaml",
            {"group_id": "weekly_context", "sources": []},
        )
        write_yaml(
            root / "config/runtime/mode-fixtures/runner_integration_map.yaml",
            {
                "fixture_id": "runner_integration_map",
                "sources": [
                    {
                        "group_id": "daily_core",
                        "source_id": "inman_tech_innovation",
                        "fetch_strategy": "rss",
                        "primary_tool_path": "HTTP/RSS fetcher",
                        "invocation_kind": "rss",
                        "invocation_url_field": "rss_feed",
                        "adapter": "none",
                        "optional_fallback": None,
                        "manual_policy": None,
                        "fixture_coverage": [],
                        "live_residual_risk": "Feed could be unavailable during live RT-M7.",
                    }
                ],
            },
        )

        errors = validator.check_runner_integration(root)

    assert any("fixture_coverage" in error and "one or more" in error for error in errors)


def test_runner_integration_validation_reports_missing_and_duplicate_sources() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        write_yaml(
            root / "config/runtime/source-groups/daily_core.yaml",
            {
                "group_id": "daily_core",
                "sources": [
                    {
                        "id": "inman_tech_innovation",
                        "fetch_strategy": "rss",
                        "rss_feed": "https://feeds.feedburner.com/inmannews",
                    },
                    {
                        "id": "redfin_news",
                        "fetch_strategy": "rss",
                        "rss_feed": "https://www.redfin.com/news/feed/",
                    },
                ],
            },
        )
        write_yaml(
            root / "config/runtime/source-groups/weekly_context.yaml",
            {"group_id": "weekly_context", "sources": []},
        )
        write_yaml(
            root / "config/runtime/mode-fixtures/runner_fetcher_contract_inman.yaml",
            {"fixture_id": "fetcher"},
        )
        row = {
            "group_id": "daily_core",
            "source_id": "inman_tech_innovation",
            "fetch_strategy": "rss",
            "primary_tool_path": "HTTP/RSS fetcher",
            "invocation_kind": "rss",
            "invocation_url_field": "rss_feed",
            "adapter": "none",
            "optional_fallback": None,
            "manual_policy": None,
            "fixture_coverage": "config/runtime/mode-fixtures/runner_fetcher_contract_inman.yaml",
            "live_residual_risk": "Feed could be unavailable during live RT-M7.",
        }
        write_yaml(
            root / "config/runtime/mode-fixtures/runner_integration_map.yaml",
            {"fixture_id": "runner_integration_map", "sources": [row, row]},
        )

        errors = validator.check_runner_integration(root)

    assert any("duplicate runner integration row" in error for error in errors)
    assert any("missing source daily_core/redfin_news" in error for error in errors)


def test_all_snippet_digest_gate_requires_partial_status_and_evidence_notes() -> None:
    bad_fixture = {
        "fixture_id": "bad_all_snippet",
        "mode_id": "build_daily_digest",
        "inputs": {
            "enriched_items": [
                {
                    "story_id": "story_1",
                    "body_status": "snippet_fallback",
                    "evidence_points": ["Snippet evidence."],
                }
            ]
        },
        "expected": {
            "selection_outputs": {"digest_status": "canonical_digest"},
            "daily_brief": {
                "render_metadata": {"digest_status": "canonical_digest"},
                "story_cards": [
                    {
                        "story_id": "story_1",
                        "url": "https://example.test/story-1",
                        "canonical_url": "https://example.test/story-1",
                    }
                ],
            },
        },
    }
    good_fixture = {
        "fixture_id": "good_all_snippet",
        "mode_id": "build_daily_digest",
        "inputs": {
            "enriched_items": [
                {
                    "story_id": "story_1",
                    "body_status": "snippet_fallback",
                    "evidence_points": ["Snippet evidence."],
                }
            ]
        },
        "expected": {
            "selection_outputs": {"digest_status": "partial_digest"},
            "daily_brief": {
                "render_metadata": {"digest_status": "partial_digest"},
                "story_cards": [
                    {
                        "story_id": "story_1",
                        "url": "https://example.test/story-1",
                        "canonical_url": "https://example.test/story-1",
                        "evidence_notes": ["Snippet evidence."],
                    }
                ],
            },
        },
    }

    bad_errors = validator.validate_all_snippet_digest_fixture(
        bad_fixture,
        pathlib.Path("bad_all_snippet.yaml"),
    )
    good_errors = validator.validate_all_snippet_digest_fixture(
        good_fixture,
        pathlib.Path("good_all_snippet.yaml"),
    )

    assert any("all-snippet" in error and "canonical_digest" in error for error in bad_errors)
    assert any("evidence_notes" in error for error in bad_errors)
    assert good_errors == []


def main() -> None:
    tests = [
        test_adapter_validation_requires_configured_sources_to_resolve,
        test_fixture_validation_reports_missing_required_fields,
        test_full_text_boundary_allows_enrichment_but_blocks_monitor_sources,
        test_enrichment_boundary_blocks_full_text_on_non_shortlisted_sections,
        test_mode_fixture_embedded_change_request_requires_schema_fields,
        test_mode_fixture_metadata_change_request_requires_reviewable_fields,
        test_runner_integration_validation_requires_complete_strategy_map,
        test_runner_integration_validation_rejects_empty_fixture_coverage,
        test_runner_integration_validation_reports_missing_and_duplicate_sources,
        test_all_snippet_digest_gate_requires_partial_status_and_evidence_notes,
    ]
    for test in tests:
        test()
        print(f"PASS  {test.__name__}")


if __name__ == "__main__":
    main()
