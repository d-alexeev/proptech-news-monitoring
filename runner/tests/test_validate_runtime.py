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
