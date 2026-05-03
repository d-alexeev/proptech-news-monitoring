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


def main() -> None:
    tests = [
        test_adapter_validation_requires_configured_sources_to_resolve,
        test_fixture_validation_reports_missing_required_fields,
        test_full_text_boundary_allows_enrichment_but_blocks_monitor_sources,
    ]
    for test in tests:
        test()
        print(f"PASS  {test.__name__}")


if __name__ == "__main__":
    main()
