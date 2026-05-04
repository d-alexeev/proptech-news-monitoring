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
    assert "danger-full-access" not in wrapper_text
    assert "-C \"$REPO_ROOT\"" in wrapper_text
    assert "-s workspace-write" in wrapper_text
    assert "--json" in wrapper_text
    assert "--output-last-message \"$LAST_MESSAGE\"" in wrapper_text
    assert "source_discovery_prefetch.py" in wrapper_text
    assert "browser_result_path" in wrapper_text
    assert "source-prefetch-browser-result.json" in wrapper_text
    assert "$GENERATED_PROMPT" in wrapper_text
    assert "printf '- Prefetch" not in wrapper_text
    assert "HTTP_USER_AGENT='PropTechNewsMonitor/1.0 (+team@example.com)'" in env_text


def test_self_test_reports_prefetch_wiring_without_live_network() -> None:
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
    assert "Prefetch helper:" in result.stdout
    assert "source_discovery_prefetch.py" in result.stdout


def test_staged_prompt_files_exist_and_have_stage_boundaries() -> None:
    discovery = REPO_ROOT / "ops/codex-cli/prompts/weekday_digest_discovery.md"
    finish = REPO_ROOT / "ops/codex-cli/prompts/weekday_digest_finish.md"

    assert discovery.exists()
    assert finish.exists()

    discovery_text = discovery.read_text(encoding="utf-8")
    finish_text = finish.read_text(encoding="utf-8")

    assert "monitor_sources only" in discovery_text
    assert "Do not run scrape_and_enrich" in discovery_text
    assert "Stage B article prefetch manifest" in finish_text
    assert "Do not read .state/articles/ from digest or review modes" in finish_text
    assert "scrape_and_enrich" in finish_text
    assert "build_daily_digest" in finish_text
    assert "review_digest" in finish_text


def test_weekday_self_test_reports_direct_article_prefetch_wiring() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        script_path = make_wrapper_fixture(root)
        for name in ["weekday_digest_discovery.md", "weekday_digest_finish.md"]:
            (root / "ops/codex-cli/prompts" / name).write_text(f"{name}\n", encoding="utf-8")
        env_file = root / ".env.good"
        env_file.write_text(
            "HTTP_USER_AGENT='PropTechNewsMonitor/1.0 (+team@example.com)'\n",
            encoding="utf-8",
        )

        result = run_wrapper(script_path, env_file)

    assert result.returncode == 0
    assert "Stage A prompt:" in result.stdout
    assert "Stage B helper:" in result.stdout
    assert "Stage C prompt:" in result.stdout


def test_wrapper_invokes_article_prefetch_helper_directly() -> None:
    wrapper_text = WRAPPER.read_text(encoding="utf-8")

    assert "-s workspace-write" in wrapper_text
    assert "tools/shortlist_article_prefetch.py" in wrapper_text
    assert "snapshot-shortlists" in wrapper_text
    assert "find-new-shortlist" in wrapper_text
    assert "synthetic-article-prefetch" in wrapper_text
    assert "danger-full-access" not in wrapper_text


def test_wrapper_validates_article_prefetch_manifest_presence() -> None:
    wrapper_text = WRAPPER.read_text(encoding="utf-8")

    assert "article_prefetch_manifest_missing" in wrapper_text
    assert "[ ! -f \"$ARTICLE_PREFETCH_RESULT\" ]" in wrapper_text
    assert "[ ! -f \"$ARTICLE_PREFETCH_SUMMARY\" ]" in wrapper_text


def test_wrapper_validates_current_run_finish_artifacts() -> None:
    wrapper_text = WRAPPER.read_text(encoding="utf-8")
    finish_prompt = (REPO_ROOT / "ops/codex-cli/prompts/weekday_digest_finish.md").read_text(encoding="utf-8")

    assert "validate-finish-artifacts" in wrapper_text
    assert "--delivery-profile telegram_digest" in wrapper_text
    assert "current-run finish artifacts" in finish_prompt
    assert "scrape_and_enrich__<run timestamp>__daily_core" in finish_prompt


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


def test_readme_documents_staged_victory_digest_runbook() -> None:
    readme = (REPO_ROOT / "ops/codex-cli/README.md").read_text(encoding="utf-8")

    assert "Victory Digest" in readme
    assert "Stage A" in readme
    assert "Stage B" in readme
    assert "Stage C" in readme
    assert "tools/shortlist_article_prefetch.py" in readme
    assert "synthetic article prefetch fallback" in readme


def main() -> None:
    tests = [
        test_malformed_env_fails_with_operator_error_without_secret_values,
        test_self_test_validates_wrapper_without_running_codex,
        test_env_loader_rejects_command_substitution_before_self_test,
        test_env_loader_rejects_unquoted_special_values,
        test_wrapper_uses_supported_codex_exec_flags_and_quotes_user_agent_template,
        test_self_test_reports_prefetch_wiring_without_live_network,
        test_staged_prompt_files_exist_and_have_stage_boundaries,
        test_weekday_self_test_reports_direct_article_prefetch_wiring,
        test_wrapper_invokes_article_prefetch_helper_directly,
        test_wrapper_validates_article_prefetch_manifest_presence,
        test_wrapper_validates_current_run_finish_artifacts,
        test_wrapper_invokes_stage_c_materializer_after_finish_agent,
        test_readme_documents_staged_victory_digest_runbook,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
