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
