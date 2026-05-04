#!/usr/bin/env python3
"""Wrapper-owned delivery retry for Codex schedule runs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RETRYABLE_STATUSES = {"delivery_failed_dns", "delivery_failed_http", "delivery_failed_unknown"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_repo_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def classify_attempt(returncode: int, stdout: str, stderr: str) -> tuple[str, dict[str, Any] | None]:
    try:
        parsed = json.loads(stdout) if stdout.strip() else {}
    except json.JSONDecodeError:
        parsed = {}

    if returncode == 0:
        return "delivered", parsed

    if isinstance(parsed, dict):
        status = parsed.get("delivery_status")
        if isinstance(status, str) and status:
            return status, parsed
        errors = parsed.get("errors")
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            classification = errors[0].get("classification")
            if isinstance(classification, str) and classification:
                return classification, parsed

    combined = f"{stdout}\n{stderr}".lower()
    if "failed to resolve" in combined or "nameresolutionerror" in combined or "dns" in combined:
        return "delivery_failed_dns", parsed if isinstance(parsed, dict) else None
    if "status=" in combined or "http" in combined:
        return "delivery_failed_http", parsed if isinstance(parsed, dict) else None
    return "delivery_failed_unknown", parsed if isinstance(parsed, dict) else None


def update_artifacts(
    *,
    finish_summary_path: Path,
    digest_manifest_path: Path,
    report_path: Path,
    report: dict[str, Any],
    repo_root: Path,
) -> None:
    if finish_summary_path.exists():
        finish_summary = read_json(finish_summary_path)
        outputs = finish_summary.setdefault("outputs", {})
        if isinstance(outputs, dict):
            outputs["telegram_delivery_report_path"] = str(report_path.relative_to(repo_root))
        finish_summary["telegram_delivery"] = {
            "status": report["status"],
            "delivered": report["delivered"],
            "attempt_count": report["attempt_count"],
            "report_path": str(report_path.relative_to(repo_root)),
        }
        write_json(finish_summary_path, finish_summary)

    if digest_manifest_path.exists():
        digest_manifest = read_json(digest_manifest_path)
        operator_report = digest_manifest.setdefault("operator_report", {})
        if isinstance(operator_report, dict):
            operator_report["telegram_delivery"] = report
        write_json(digest_manifest_path, digest_manifest)


def build_report(
    *,
    run_id: str,
    delivery_profile: str,
    status: str,
    delivered: bool,
    attempts: list[dict[str, Any]],
    prior_delivery: dict[str, Any] | None,
    message_ids: list[int] | None = None,
    parts_sent: int = 0,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "delivery_profile": delivery_profile,
        "status": status,
        "delivered": delivered,
        "delivered_at": now_iso() if delivered else None,
        "attempt_count": len(attempts),
        "parts_sent": parts_sent,
        "message_ids": message_ids or [],
        "attempts": attempts,
        "prior_stage_c_delivery": prior_delivery,
        "runner_delivery": True,
    }


def run_delivery(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    finish_summary_path = resolve_repo_path(repo_root, args.finish_summary)
    finish_draft_path = resolve_repo_path(repo_root, args.finish_draft)
    report_path = repo_root / ".state" / "codex-runs" / f"{args.run_id}-telegram-delivery-report.json"

    finish_summary = read_json(finish_summary_path)
    outputs = finish_summary.get("outputs", {})
    if not isinstance(outputs, dict) or not outputs.get("markdown_path") or not outputs.get("digest_manifest_path"):
        raise ValueError("finish summary outputs must include markdown_path and digest_manifest_path")

    markdown_path = resolve_repo_path(repo_root, str(outputs["markdown_path"]))
    digest_manifest_path = resolve_repo_path(repo_root, str(outputs["digest_manifest_path"]))
    finish_draft = read_json(finish_draft_path)
    prior_delivery = finish_draft.get("telegram_delivery")
    if not isinstance(prior_delivery, dict):
        prior_delivery = None

    if prior_delivery and prior_delivery.get("delivered") is True:
        report = build_report(
            run_id=args.run_id,
            delivery_profile=args.delivery_profile,
            status="delivered",
            delivered=True,
            attempts=[],
            prior_delivery=prior_delivery,
            message_ids=[int(x) for x in prior_delivery.get("message_ids", [])],
            parts_sent=int(prior_delivery.get("parts_sent", 0)),
        )
        write_json(report_path, report)
        update_artifacts(
            finish_summary_path=finish_summary_path,
            digest_manifest_path=digest_manifest_path,
            report_path=report_path,
            report=report,
            repo_root=repo_root,
        )
        return report

    if not os.environ.get("TELEGRAM_BOT_TOKEN") or not os.environ.get("TELEGRAM_CHAT_ID"):
        report = build_report(
            run_id=args.run_id,
            delivery_profile=args.delivery_profile,
            status="not_configured",
            delivered=False,
            attempts=[],
            prior_delivery=prior_delivery,
        )
        write_json(report_path, report)
        update_artifacts(
            finish_summary_path=finish_summary_path,
            digest_manifest_path=digest_manifest_path,
            report_path=report_path,
            report=report,
            repo_root=repo_root,
        )
        return report

    markdown = markdown_path.read_text(encoding="utf-8")
    telegram_send_path = resolve_repo_path(repo_root, args.telegram_send_path)
    attempts: list[dict[str, Any]] = []
    final_status = "delivery_failed_unknown"
    final_payload: dict[str, Any] | None = None

    for attempt_no in range(1, args.attempts + 1):
        completed = subprocess.run(
            [
                sys.executable,
                str(telegram_send_path),
                "--profile",
                args.delivery_profile,
                "--date",
                args.date,
            ],
            input=markdown,
            text=True,
            capture_output=True,
            cwd=repo_root,
            check=False,
        )
        status, payload = classify_attempt(completed.returncode, completed.stdout, completed.stderr)
        final_status = status
        final_payload = payload
        attempts.append(
            {
                "attempt": attempt_no,
                "status": status,
                "returncode": completed.returncode,
                "retryable": status in RETRYABLE_STATUSES,
                "stderr": completed.stderr.strip(),
            }
        )

        if status == "delivered":
            report = build_report(
                run_id=args.run_id,
                delivery_profile=args.delivery_profile,
                status="delivered",
                delivered=True,
                attempts=attempts,
                prior_delivery=prior_delivery,
                message_ids=[int(x) for x in (payload or {}).get("message_ids", [])],
                parts_sent=int((payload or {}).get("parts_sent", 0)),
            )
            write_json(report_path, report)
            update_artifacts(
                finish_summary_path=finish_summary_path,
                digest_manifest_path=digest_manifest_path,
                report_path=report_path,
                report=report,
                repo_root=repo_root,
            )
            return report

        if status not in RETRYABLE_STATUSES or attempt_no == args.attempts:
            break
        time.sleep(args.delay_seconds)

    errors = []
    if isinstance(final_payload, dict) and isinstance(final_payload.get("errors"), list):
        errors = final_payload["errors"]
    report = build_report(
        run_id=args.run_id,
        delivery_profile=args.delivery_profile,
        status=final_status,
        delivered=False,
        attempts=attempts,
        prior_delivery=prior_delivery,
        parts_sent=int((final_payload or {}).get("parts_sent", 0)) if isinstance(final_payload, dict) else 0,
    )
    report["errors"] = errors
    write_json(report_path, report)
    update_artifacts(
        finish_summary_path=finish_summary_path,
        digest_manifest_path=digest_manifest_path,
        report_path=report_path,
        report=report,
        repo_root=repo_root,
    )
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retry schedule Telegram delivery from materialized digest")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--delivery-profile", required=True)
    parser.add_argument("--finish-summary", required=True)
    parser.add_argument("--finish-draft", required=True)
    parser.add_argument("--telegram-send-path", default="tools/telegram_send.py")
    parser.add_argument(
        "--attempts",
        type=int,
        default=int(os.environ.get("CODEX_TELEGRAM_DELIVERY_ATTEMPTS", "3")),
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=float(os.environ.get("CODEX_TELEGRAM_DELIVERY_RETRY_DELAY_SECONDS", "20")),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    report = run_delivery(args)
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
