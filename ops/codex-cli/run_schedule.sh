#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s {weekday_digest|weekly_digest|breaking_alert}\n' "$0" >&2
}

if [ "$#" -ne 1 ]; then
  usage
  exit 2
fi

SCHEDULE_ID="$1"
case "$SCHEDULE_ID" in
  weekday_digest|weekly_digest|breaking_alert)
    ;;
  *)
    usage
    exit 2
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROMPT_FILE="$SCRIPT_DIR/prompts/$SCHEDULE_ID.md"
RUN_ROOT="$REPO_ROOT/.state/codex-runs"
LOCK_DIR="$RUN_ROOT/$SCHEDULE_ID.lock"
RUN_ID="$(date -u '+%Y%m%dT%H%M%SZ')-$SCHEDULE_ID"
EVENT_LOG="$RUN_ROOT/$RUN_ID-events.jsonl"
LAST_MESSAGE="$RUN_ROOT/$RUN_ID-last-message.txt"
CODEX_BIN="${CODEX_BIN:-codex}"

if [ ! -f "$PROMPT_FILE" ]; then
  printf 'Prompt file not found: %s\n' "$PROMPT_FILE" >&2
  exit 2
fi

mkdir -p "$RUN_ROOT"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  printf 'Another %s run appears to be active: %s\n' "$SCHEDULE_ID" "$LOCK_DIR" >&2
  exit 10
fi

cleanup() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cd "$REPO_ROOT"

if [ -f "$REPO_ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$REPO_ROOT/.env"
  set +a
fi

if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  . "$REPO_ROOT/.venv/bin/activate"
fi

"$CODEX_BIN" exec \
  -C "$REPO_ROOT" \
  -s workspace-write \
  -a never \
  --json \
  --output-last-message "$LAST_MESSAGE" \
  - < "$PROMPT_FILE" > "$EVENT_LOG"

printf 'Codex schedule run complete: %s\n' "$RUN_ID"
printf 'Events: %s\n' "$EVENT_LOG"
printf 'Final message: %s\n' "$LAST_MESSAGE"

