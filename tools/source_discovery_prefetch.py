#!/usr/bin/env python3
"""
source_discovery_prefetch.py — runner-side static source prefetch.

This helper performs deterministic network I/O before the inner scheduled
Codex agent starts. It writes local evidence artifacts under .state/codex-runs
and does not emit raw/shortlist shards.
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import yaml


FetchRunner = Callable[[list[dict], Path], tuple[int, dict, str]]
DnsChecker = Callable[[list[str]], dict[str, dict]]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data


def _first_url(source: dict, key: str = "landing_urls") -> str | None:
    urls = source.get(key)
    if isinstance(urls, list) and urls:
        return str(urls[0])
    return None


def _source_spec(source: dict, source_group: str) -> dict | None:
    source_id = source.get("id")
    strategy = source.get("fetch_strategy")
    if not source_id or not strategy:
        return None
    if strategy == "rss":
        url = source.get("rss_feed")
        kind = "rss"
    elif strategy in ("html_scrape", "itunes_api"):
        url = source.get("itunes_api_url") or _first_url(source)
        kind = "http"
    else:
        return None
    if not url:
        return None
    return {
        "source_id": source_id,
        "url": str(url),
        "kind": kind,
        "source_group": source_group,
        "fetch_strategy": strategy,
    }


def _skipped_source(source: dict, source_group: str) -> dict | None:
    source_id = source.get("id")
    strategy = source.get("fetch_strategy")
    if not source_id or not strategy:
        return None
    if strategy == "chrome_scrape":
        return {
            "source_id": source_id,
            "source_group": source_group,
            "fetch_strategy": strategy,
            "status": "not_attempted",
            "reason": "no_headless_browser_runner",
            "urls": [str(url) for url in source.get("landing_urls", [])],
        }
    if strategy not in ("rss", "html_scrape", "itunes_api"):
        return {
            "source_id": source_id,
            "source_group": source_group,
            "fetch_strategy": strategy,
            "status": "not_attempted",
            "reason": "unsupported_prefetch_strategy",
            "urls": [str(url) for url in source.get("landing_urls", [])],
        }
    return None


def build_prefetch_plan(repo_root: Path, schedule_id: str) -> dict:
    schedule_path = repo_root / "config/runtime/schedule_bindings.yaml"
    schedule_doc = load_yaml(schedule_path)
    schedule = schedule_doc.get(schedule_id)
    if not isinstance(schedule, dict):
        raise ValueError(f"Unknown schedule id: {schedule_id}")
    source_groups = schedule.get("source_groups")
    if not isinstance(source_groups, list) or not source_groups:
        raise ValueError(f"Schedule has no source_groups: {schedule_id}")

    source_specs: list[dict] = []
    skipped_sources: list[dict] = []
    configured_source_count = 0

    for group_id in source_groups:
        group_path = repo_root / f"config/runtime/source-groups/{group_id}.yaml"
        group_doc = load_yaml(group_path)
        sources = group_doc.get("sources")
        if not isinstance(sources, list):
            raise ValueError(f"Source group has no sources array: {group_path}")
        for source in sources:
            if not isinstance(source, dict):
                continue
            configured_source_count += 1
            spec = _source_spec(source, str(group_id))
            if spec:
                source_specs.append(spec)
                continue
            skipped = _skipped_source(source, str(group_id))
            if skipped:
                skipped_sources.append(skipped)

    browser_source_count = sum(
        1 for source in skipped_sources if source.get("fetch_strategy") == "chrome_scrape"
    )
    return {
        "schedule_id": schedule_id,
        "source_groups": [str(group_id) for group_id in source_groups],
        "delivery_profile": schedule.get("delivery_profile"),
        "configured_source_count": configured_source_count,
        "fetchable_source_count": len(source_specs),
        "browser_source_count": browser_source_count,
        "source_specs": source_specs,
        "skipped_sources": skipped_sources,
    }


def default_fetch_runner(source_specs: list[dict], repo_root: Path) -> tuple[int, dict, str]:
    cmd = [sys.executable, "tools/rss_fetch.py", "--stdin", "--pretty"]
    proc = subprocess.run(
        cmd,
        input=json.dumps({"sources": source_specs}, ensure_ascii=False),
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError:
        doc = {
            "fetched_at": now_iso(),
            "results": [],
            "batch_status": "failed",
            "failure_class": "fetcher_output_parse_error",
            "run_failure": {"message": proc.stdout[:2000]},
        }
    return proc.returncode, doc, proc.stderr[-2000:]


def default_dns_checker(hosts: list[str]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for host in hosts:
        try:
            result[host] = {"ok": True, "addr": socket.gethostbyname(host)}
        except Exception as exc:  # noqa: BLE001 - diagnostic artifact
            result[host] = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}
    return result


def _hosts_for_dns(source_specs: list[dict]) -> list[str]:
    hosts = {"example.com"}
    for spec in source_specs:
        host = urlparse(spec.get("url", "")).netloc
        if host:
            hosts.add(host)
    return sorted(hosts)


def _is_successful_result(result: dict) -> bool:
    return not result.get("error") and not result.get("soft_fail")


def _source_discovery_status(fetch_doc: dict, success_count: int) -> tuple[str, str, bool]:
    if (
        fetch_doc.get("batch_status") == "environment_failure"
        and fetch_doc.get("failure_class") == "global_dns_resolution_failure"
    ):
        return "failed", "blocked_before_digest", False
    if success_count > 0:
        return "partial", "prefetch_available", False
    return "failed", "blocked_before_digest", False


def run_prefetch(
    repo_root: Path,
    schedule_id: str,
    *,
    run_id: str,
    fetch_runner: FetchRunner = default_fetch_runner,
    dns_checker: DnsChecker = default_dns_checker,
) -> dict:
    repo_root = repo_root.resolve()
    run_root = repo_root / ".state/codex-runs"
    run_root.mkdir(parents=True, exist_ok=True)

    plan = build_prefetch_plan(repo_root, schedule_id)
    source_specs = plan["source_specs"]
    fetch_exit_code, fetch_doc, stderr_preview = fetch_runner(source_specs, repo_root)
    dns_doc = dns_checker(_hosts_for_dns(source_specs))

    fetch_path = run_root / f"{run_id}-source-prefetch-fetch-result.json"
    dns_path = run_root / f"{run_id}-source-prefetch-dns-check.json"
    summary_path = run_root / f"{run_id}-source-prefetch-summary.json"

    fetch_doc["runner_invocation"] = {
        "cmd": "python3 tools/rss_fetch.py --stdin --pretty",
        "exit_code": fetch_exit_code,
        "stderr_preview": stderr_preview,
    }

    results = fetch_doc.get("results") or []
    success_count = sum(1 for result in results if _is_successful_result(result))
    status, downstream_gate, canonical_complete = _source_discovery_status(
        fetch_doc,
        success_count,
    )

    summary = {
        "run_id": run_id,
        "schedule_id": schedule_id,
        "source_groups": plan["source_groups"],
        "delivery_profile": plan["delivery_profile"],
        "generated_at": now_iso(),
        "source_discovery_status": status,
        "downstream_gate": downstream_gate,
        "canonical_static_source_complete": canonical_complete,
        "batch_status": fetch_doc.get("batch_status"),
        "failure_class": fetch_doc.get("failure_class"),
        "configured_source_count": plan["configured_source_count"],
        "fetchable_source_count": plan["fetchable_source_count"],
        "fetchable_attempted_count": len(source_specs),
        "fetchable_success_count": success_count,
        "browser_source_count": plan["browser_source_count"],
        "browser_attempted_count": 0,
        "skipped_sources": plan["skipped_sources"],
        "fetch_result_path": str(fetch_path.relative_to(repo_root)),
        "dns_check_path": str(dns_path.relative_to(repo_root)),
        "summary_path": str(summary_path.relative_to(repo_root)),
        "runner_invocation": fetch_doc["runner_invocation"],
    }

    fetch_path.write_text(json.dumps(fetch_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dns_path.write_text(json.dumps(dns_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prefetch configured static sources for a schedule")
    parser.add_argument("--schedule-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_prefetch(
        Path(args.repo_root),
        args.schedule_id,
        run_id=args.run_id,
    )
    indent = 2 if args.pretty else None
    print(json.dumps(summary, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"source_discovery_prefetch_error: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
