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
