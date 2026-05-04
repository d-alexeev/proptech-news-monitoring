#!/usr/bin/env python3
"""
Offline tests for ops/codex-cli/run_schedule.sh.

Run with:
  python3 tools/test_codex_cli_run_schedule.py
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WRAPPER = REPO_ROOT / "ops/codex-cli/run_schedule.sh"
ENV_EXAMPLE = REPO_ROOT / ".env.example"


def make_wrapper_fixture(root: pathlib.Path) -> pathlib.Path:
    script_path = root / "ops/codex-cli/run_schedule.sh"
    prompt_path = root / "ops/codex-cli/prompts/weekday_digest.md"
    script_path.parent.mkdir(parents=True)
    prompt_path.parent.mkdir(parents=True)
    shutil.copy2(WRAPPER, script_path)
    prompt_path.write_text("fixture prompt\n", encoding="utf-8")
    return script_path


def run_wrapper(script_path: pathlib.Path, env_file: pathlib.Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "CODEX_BIN": "false",
            "CODEX_ENV_FILE": str(env_file),
            "CODEX_RUN_SCHEDULE_SELF_TEST": "1",
        }
    )
    return subprocess.run(
        ["bash", str(script_path), "weekday_digest"],
        cwd=script_path.parents[2],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_malformed_env_fails_with_operator_error_without_secret_values() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        script_path = make_wrapper_fixture(root)
        env_file = root / ".env.bad"
        secret_value = "token-value-that-must-not-appear"
        env_file.write_text(
            f"TELEGRAM_BOT_TOKEN={secret_value}\n"
            "HTTP_USER_AGENT=PropTechNewsMonitor/1.0 (+team@example.com)\n",
            encoding="utf-8",
        )

        result = run_wrapper(script_path, env_file)

    assert result.returncode != 0
    assert "Invalid environment file" in result.stderr
    assert str(env_file) in result.stderr
    assert secret_value not in result.stderr
    assert "HTTP_USER_AGENT=PropTechNewsMonitor" not in result.stderr


def test_self_test_validates_wrapper_without_running_codex() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        script_path = make_wrapper_fixture(root)
        env_file = root / ".env.good"
        env_file.write_text(
            "HTTP_USER_AGENT='PropTechNewsMonitor/1.0 (+team@example.com)'\n",
            encoding="utf-8",
        )

        result = run_wrapper(script_path, env_file)

    assert result.returncode == 0
    assert "Wrapper self-test passed" in result.stdout


def test_env_loader_rejects_command_substitution_before_self_test() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        script_path = make_wrapper_fixture(root)
        marker = root / "side-effect"
        env_file = root / ".env.unsafe"
        env_file.write_text(
            f"HTTP_USER_AGENT='safe value'\nMALICIOUS=$(touch {marker})\n",
            encoding="utf-8",
        )

        result = run_wrapper(script_path, env_file)

    assert result.returncode != 0
    assert "Command substitution is not allowed" in result.stderr
    assert not marker.exists()


def test_env_loader_rejects_unquoted_special_values() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        script_path = make_wrapper_fixture(root)
        env_file = root / ".env.unquoted"
        env_file.write_text(
            "HTTP_USER_AGENT=PropTechNewsMonitor/1.0 (+team@example.com)\n",
            encoding="utf-8",
        )

        result = run_wrapper(script_path, env_file)

    assert result.returncode != 0
    assert "must be single-quoted" in result.stderr


def test_wrapper_uses_supported_codex_exec_flags_and_quotes_user_agent_template() -> None:
    wrapper_text = WRAPPER.read_text(encoding="utf-8")
    env_text = ENV_EXAMPLE.read_text(encoding="utf-8")

    assert "-a never" not in wrapper_text
    assert "-C \"$REPO_ROOT\"" in wrapper_text
    assert "-s workspace-write" in wrapper_text
    assert "--json" in wrapper_text
    assert "--output-last-message \"$LAST_MESSAGE\"" in wrapper_text
    assert "HTTP_USER_AGENT='PropTechNewsMonitor/1.0 (+team@example.com)'" in env_text


def main() -> None:
    tests = [
        test_malformed_env_fails_with_operator_error_without_secret_values,
        test_self_test_validates_wrapper_without_running_codex,
        test_env_loader_rejects_command_substitution_before_self_test,
        test_env_loader_rejects_unquoted_special_values,
        test_wrapper_uses_supported_codex_exec_flags_and_quotes_user_agent_template,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
