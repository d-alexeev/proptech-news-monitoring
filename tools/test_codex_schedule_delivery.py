#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import tempfile

import codex_schedule_delivery


def write_json(path: pathlib.Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_repo(root: pathlib.Path, prior_delivery: dict) -> tuple[pathlib.Path, pathlib.Path]:
    run_id = "20260504T121000Z-weekday_digest"
    markdown_path = root / "digests" / "2026-05-04-daily-digest.md"
    digest_manifest_path = root / ".state" / "runs" / "2026-05-04" / "build_daily_digest__20260504T121000Z__telegram_digest.json"
    finish_summary_path = root / ".state" / "codex-runs" / f"{run_id}-finish-summary.json"
    finish_draft_path = root / ".state" / "codex-runs" / f"{run_id}-finish-draft.json"

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(
        "# PropTech Monitor Daily | 4 мая 2026\n\n"
        "## ТОП СИГНАЛЫ\n\n"
        "### Новость\n"
        "Score: 80 | portals | US | [Источник](https://example.test/story)\n\n"
        "**Что это значит:** Российский текст для проверки доставки.\n\n"
        "**Для Avito:** Нужно проверить повтор доставки.\n\n"
        "Статус запуска: источники 1/1 | статьи 1/1 | качество: validated.\n",
        encoding="utf-8",
    )
    write_json(
        digest_manifest_path,
        {
            "run_id": "build_daily_digest__20260504T121000Z__telegram_digest",
            "operator_report": {"telegram_delivery": prior_delivery},
        },
    )
    write_json(
        finish_summary_path,
        {
            "status": "materialized",
            "run_id": run_id,
            "outputs": {
                "markdown_path": "digests/2026-05-04-daily-digest.md",
                "digest_manifest_path": ".state/runs/2026-05-04/build_daily_digest__20260504T121000Z__telegram_digest.json",
            },
        },
    )
    write_json(finish_draft_path, {"telegram_delivery": prior_delivery})
    return finish_summary_path, finish_draft_path


def args(root: pathlib.Path, finish_summary: pathlib.Path, finish_draft: pathlib.Path, **overrides) -> argparse.Namespace:
    values = {
        "repo_root": str(root),
        "run_id": "20260504T121000Z-weekday_digest",
        "date": "2026-05-04",
        "delivery_profile": "telegram_digest",
        "finish_summary": str(finish_summary),
        "finish_draft": str(finish_draft),
        "telegram_send_path": "tools/telegram_send.py",
        "attempts": 3,
        "delay_seconds": 0,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_already_delivered_is_not_sent_again() -> None:
    prior = {"status": "delivered", "delivered": True, "parts_sent": 1, "message_ids": [123]}
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        finish_summary, finish_draft = make_repo(root, prior)
        report = codex_schedule_delivery.run_delivery(args(root, finish_summary, finish_draft))

        assert report["status"] == "delivered"
        assert report["delivered"] is True
        assert report["attempt_count"] == 0

        report_path = root / ".state" / "codex-runs" / "20260504T121000Z-weekday_digest-telegram-delivery-report.json"
        assert report_path.exists()
        manifest = json.loads(
            (root / ".state" / "runs" / "2026-05-04" / "build_daily_digest__20260504T121000Z__telegram_digest.json").read_text()
        )
        assert manifest["operator_report"]["telegram_delivery"]["message_ids"] == [123]

    print("PASS  test_already_delivered_is_not_sent_again")


def test_retry_dns_failure_then_delivered() -> None:
    prior = {"status": "delivery_failed_dns", "delivered": False, "parts_sent": 0, "message_ids": []}
    original_env = {key: os.environ.get(key) for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "FAKE_COUNT_PATH")}
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        finish_summary, finish_draft = make_repo(root, prior)
        fake_sender = root / "tools" / "fake_telegram_send.py"
        fake_sender.parent.mkdir(parents=True, exist_ok=True)
        fake_sender.write_text(
            "import json, os, pathlib, sys\n"
            "count_path = pathlib.Path(os.environ['FAKE_COUNT_PATH'])\n"
            "count = int(count_path.read_text() or '0') if count_path.exists() else 0\n"
            "count += 1\n"
            "count_path.write_text(str(count))\n"
            "sys.stdin.read()\n"
            "if count == 1:\n"
            "    print(json.dumps({'delivery_status':'delivery_failed_dns','parts_sent':0,'errors':[{'classification':'delivery_failed_dns'}]}))\n"
            "    sys.exit(1)\n"
            "print(json.dumps({'delivery_status':'delivered','parts_sent':1,'message_ids':[456],'errors':[]}))\n",
            encoding="utf-8",
        )

        os.environ["TELEGRAM_BOT_TOKEN"] = "123456:FAKE"
        os.environ["TELEGRAM_CHAT_ID"] = "-100123456"
        os.environ["FAKE_COUNT_PATH"] = str(root / "attempt-count.txt")

        try:
            report = codex_schedule_delivery.run_delivery(
                args(root, finish_summary, finish_draft, telegram_send_path=str(fake_sender))
            )
        finally:
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        assert report["status"] == "delivered"
        assert report["delivered"] is True
        assert report["attempt_count"] == 2
        assert report["attempts"][0]["status"] == "delivery_failed_dns"
        assert report["message_ids"] == [456]

        finish_summary_data = json.loads(finish_summary.read_text())
        assert finish_summary_data["telegram_delivery"]["status"] == "delivered"
        manifest = json.loads(
            (root / ".state" / "runs" / "2026-05-04" / "build_daily_digest__20260504T121000Z__telegram_digest.json").read_text()
        )
        assert manifest["operator_report"]["telegram_delivery"]["attempt_count"] == 2

    print("PASS  test_retry_dns_failure_then_delivered")


if __name__ == "__main__":
    test_already_delivered_is_not_sent_again()
    test_retry_dns_failure_then_delivered()
