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


def test_validate_finish_artifacts_requires_current_run_manifests() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        run_id = "20260504T121000Z-weekday_digest"

        try:
            codex_schedule_artifacts.validate_finish_artifacts(
                repo_root=root,
                run_id=run_id,
                run_date="2026-05-04",
                source_group="daily_core",
                delivery_profile="telegram_digest",
            )
        except FileNotFoundError as exc:
            assert "missing current-run finish artifacts" in str(exc)
            assert "scrape_and_enrich__20260504T121000Z__daily_core.json" in str(exc)
        else:
            raise AssertionError("missing current-run artifacts should fail validation")

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

        validation = codex_schedule_artifacts.validate_finish_artifacts(
            repo_root=root,
            run_id=run_id,
            run_date="2026-05-04",
            source_group="daily_core",
            delivery_profile="telegram_digest",
        )

        assert validation["status"] == "ok"
        assert validation["run_timestamp"] == "20260504T121000Z"


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


def main() -> None:
    tests = [
        test_find_latest_shortlist_for_source_group,
        test_find_new_shortlist_rejects_stale_shards,
        test_write_synthetic_article_prefetch_fallback,
        test_validate_finish_artifacts_requires_current_run_manifests,
        test_validate_finish_artifacts_requires_finish_summary_when_requested,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
