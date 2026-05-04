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
ENV_FILE="${CODEX_ENV_FILE:-$REPO_ROOT/.env}"

if [ ! -f "$PROMPT_FILE" ]; then
  printf 'Prompt file not found: %s\n' "$PROMPT_FILE" >&2
  exit 2
fi

validate_env_file() {
  local env_file="$1"
  local line line_no key value

  line_no=0
  while IFS= read -r line || [ -n "$line" ]; do
    line_no=$((line_no + 1))
    case "$line" in
      ""|\#*) continue ;;
      export\ *) line="${line#export }" ;;
    esac
    if [[ "$line" != *=* ]]; then
      printf 'Invalid environment file: %s line %s\n' "$env_file" "$line_no" >&2
      printf 'Use simple KEY=VALUE lines only; values with spaces, parentheses, #, $, or quotes must be single-quoted.\n' >&2
      exit 2
    fi
    key="${line%%=*}"
    value="${line#*=}"
    if ! [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      printf 'Invalid environment file: %s line %s\n' "$env_file" "$line_no" >&2
      printf 'Environment variable names must match [A-Za-z_][A-Za-z0-9_]*.\n' >&2
      exit 2
    fi
    case "$value" in
      *'$('*|*'`'*)
        printf 'Invalid environment file: %s line %s\n' "$env_file" "$line_no" >&2
        printf 'Command substitution is not allowed in environment files.\n' >&2
        exit 2
        ;;
    esac
    if [[ "$value" =~ [[:space:]\#\$\"\'\(\)] ]]; then
      if [[ ! "$value" =~ ^\'([^\'\\]|\\.)*\'$ ]]; then
        printf 'Invalid environment file: %s line %s\n' "$env_file" "$line_no" >&2
        printf 'Values with spaces, parentheses, #, $, or quotes must be single-quoted.\n' >&2
        exit 2
      fi
    fi
  done < "$env_file"
}

load_env_file() {
  local env_file="$1"
  local line key value

  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ""|\#*) continue ;;
      export\ *) line="${line#export }" ;;
    esac
    key="${line%%=*}"
    value="${line#*=}"
    if [[ "$value" =~ ^\'([^\'\\]|\\.)*\'$ ]]; then
      value="${value:1:${#value}-2}"
    fi
    printf -v "$key" '%s' "$value"
    export "$key"
  done < "$env_file"
}

if [ -n "${CODEX_ENV_FILE:-}" ] && [ ! -f "$ENV_FILE" ]; then
  printf 'Environment file not found: %s\n' "$ENV_FILE" >&2
  exit 2
fi

if [ -f "$ENV_FILE" ]; then
  validate_env_file "$ENV_FILE"
  load_env_file "$ENV_FILE"
fi

if [ "${CODEX_RUN_SCHEDULE_SELF_TEST:-}" = "1" ]; then
  printf 'Wrapper self-test passed: %s\n' "$SCHEDULE_ID"
  printf 'Prompt: %s\n' "$PROMPT_FILE"
  printf 'Environment: %s\n' "$ENV_FILE"
  printf 'Codex exec flags: -C --cd, -s --sandbox, --json, --output-last-message\n'
  exit 0
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

if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  . "$REPO_ROOT/.venv/bin/activate"
fi

"$CODEX_BIN" exec \
  -C "$REPO_ROOT" \
  -s workspace-write \
  --json \
  --output-last-message "$LAST_MESSAGE" \
  - < "$PROMPT_FILE" > "$EVENT_LOG"

printf 'Codex schedule run complete: %s\n' "$RUN_ID"
printf 'Events: %s\n' "$EVENT_LOG"
printf 'Final message: %s\n' "$LAST_MESSAGE"
