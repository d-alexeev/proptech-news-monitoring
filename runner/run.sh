#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s [--self-test|--dry-run] {weekday|weekly}\n' "$0" >&2
  printf 'Supported jobs: weekday, weekly\n' >&2
}

MODE="run"
if [ "${1:-}" = "--self-test" ] || [ "${1:-}" = "--dry-run" ]; then
  MODE="${1#--}"
  shift
fi

if [ "$#" -ne 1 ]; then
  usage
  exit 2
fi

JOB="$1"
case "$JOB" in
  weekday)
    LEGACY_SCHEDULE_ID="weekday_digest"
    ;;
  weekly)
    LEGACY_SCHEDULE_ID="weekly_digest"
    ;;
  *)
    usage
    exit 2
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST="$REPO_ROOT/runtime/manifest.yaml"
VALIDATOR="$REPO_ROOT/runner/tools/validate_runtime.py"
LEGACY_WRAPPER="$REPO_ROOT/ops/codex-cli/run_schedule.sh"
DRY_RUN_DIR="$REPO_ROOT/.state/refactor-dry-runs"

python3 "$VALIDATOR" --check all --repo-root "$REPO_ROOT" >/dev/null

if [ "$MODE" = "self-test" ]; then
  CODEX_RUN_SCHEDULE_SELF_TEST=1 "$LEGACY_WRAPPER" "$LEGACY_SCHEDULE_ID" >/dev/null
  printf 'Refactor runner self-test passed: %s\n' "$JOB"
  printf 'runtime manifest: %s\n' "$MANIFEST"
  printf 'legacy wrapper: %s\n' "$LEGACY_WRAPPER"
  printf 'legacy schedule: %s\n' "$LEGACY_SCHEDULE_ID"
  exit 0
fi

if [ "$MODE" = "dry-run" ]; then
  mkdir -p "$DRY_RUN_DIR"
  RUN_ID="$(date -u '+%Y%m%dT%H%M%SZ')-$JOB-dry-run"
  REPORT="$DRY_RUN_DIR/$RUN_ID.json"
  CODEX_RUN_SCHEDULE_SELF_TEST=1 "$LEGACY_WRAPPER" "$LEGACY_SCHEDULE_ID" >/dev/null
  python3 - "$REPORT" "$RUN_ID" "$JOB" "$LEGACY_SCHEDULE_ID" <<'PY'
import json
import pathlib
import sys
from datetime import datetime, timezone

report, run_id, job, legacy_schedule_id = sys.argv[1:5]
payload = {
    "schema_version": 1,
    "run_id": run_id,
    "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "job": job,
    "status": "offline_wiring_ready",
    "runtime_manifest": "runtime/manifest.yaml",
    "legacy_wrapper": "ops/codex-cli/run_schedule.sh",
    "legacy_schedule_id": legacy_schedule_id,
    "live_codex_invoked": False,
    "live_source_fetch_invoked": False,
    "telegram_invoked": False,
    "runtime_prompts_consumed_by_live_run": False,
}
path = pathlib.Path(report)
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
  printf 'Refactor runner dry-run passed: %s\n' "$JOB"
  printf 'Dry-run report: %s\n' "${REPORT#$REPO_ROOT/}"
  exit 0
fi

exec "$LEGACY_WRAPPER" "$LEGACY_SCHEDULE_ID"
