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
DISCOVERY_PROMPT_FILE="$SCRIPT_DIR/prompts/weekday_digest_discovery.md"
FINISH_PROMPT_FILE="$SCRIPT_DIR/prompts/weekday_digest_finish.md"
RUN_ROOT="$REPO_ROOT/.state/codex-runs"
LOCK_DIR="$RUN_ROOT/$SCHEDULE_ID.lock"
RUN_ID="$(date -u '+%Y%m%dT%H%M%SZ')-$SCHEDULE_ID"
RUN_DATE="$(date -u '+%Y-%m-%d')"
EVENT_LOG="$RUN_ROOT/$RUN_ID-events.jsonl"
LAST_MESSAGE="$RUN_ROOT/$RUN_ID-last-message.txt"
PREFETCH_STDOUT="$RUN_ROOT/$RUN_ID-source-prefetch-stdout.json"
PREFETCH_SUMMARY="$RUN_ROOT/$RUN_ID-source-prefetch-summary.json"
BROWSER_PREFETCH_RESULT="$RUN_ROOT/$RUN_ID-source-prefetch-browser-result.json"
GENERATED_PROMPT="$RUN_ROOT/$RUN_ID-prompt.md"
DISCOVERY_EVENT_LOG="$RUN_ROOT/$RUN_ID-discovery-events.jsonl"
FINISH_EVENT_LOG="$RUN_ROOT/$RUN_ID-finish-events.jsonl"
DISCOVERY_LAST_MESSAGE="$RUN_ROOT/$RUN_ID-discovery-last-message.txt"
FINISH_LAST_MESSAGE="$RUN_ROOT/$RUN_ID-finish-last-message.txt"
DISCOVERY_PROMPT="$RUN_ROOT/$RUN_ID-discovery-prompt.md"
FINISH_PROMPT="$RUN_ROOT/$RUN_ID-finish-prompt.md"
ARTICLE_PREFETCH_STDOUT="$RUN_ROOT/$RUN_ID-article-prefetch-stdout.json"
ARTICLE_PREFETCH_RESULT="$RUN_ROOT/$RUN_ID-article-prefetch-result.json"
ARTICLE_PREFETCH_SUMMARY="$RUN_ROOT/$RUN_ID-article-prefetch-summary.json"
FINISH_DRAFT="$RUN_ROOT/$RUN_ID-finish-draft.json"
FINISH_SUMMARY="$RUN_ROOT/$RUN_ID-finish-summary.json"
CODEX_BIN="${CODEX_BIN:-codex}"
ENV_FILE="${CODEX_ENV_FILE:-$REPO_ROOT/.env}"
PREFETCH_HELPER="$REPO_ROOT/tools/source_discovery_prefetch.py"
ARTIFACT_HELPER="$REPO_ROOT/tools/codex_schedule_artifacts.py"
ARTICLE_PREFETCH_HELPER="$REPO_ROOT/tools/shortlist_article_prefetch.py"
STAGE_C_FINISH_HELPER="$REPO_ROOT/tools/stage_c_finish.py"

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
  printf 'Prefetch helper: %s\n' "$PREFETCH_HELPER"
  printf 'Stage A prompt: %s\n' "$DISCOVERY_PROMPT_FILE"
  printf 'Stage B helper: %s\n' "$ARTICLE_PREFETCH_HELPER"
  printf 'Stage C prompt: %s\n' "$FINISH_PROMPT_FILE"
  printf 'Stage C materializer: %s\n' "$STAGE_C_FINISH_HELPER"
  printf 'Artifact helper: %s\n' "$ARTIFACT_HELPER"
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

if [ ! -f "$PREFETCH_HELPER" ]; then
  printf 'Source discovery prefetch helper not found: %s\n' "$PREFETCH_HELPER" >&2
  exit 2
fi

print_source_prefetch_preamble() {
  printf '# Runner Source Discovery Prefetch\n\n'
  printf 'The schedule wrapper already ran static source discovery prefetch before this inner Codex agent started.\n'
  printf 'Use these local JSON artifacts as canonical static source and browser source evidence for `monitor_sources`.\n'
  printf 'Do not re-run static network fetches for sources already represented in the prefetch artifacts from inside this sandbox.\n'
  printf 'Use browser evidence only when the prefetch summary includes `browser_result_path`; otherwise configured browser sources remain `not_attempted`.\n\n'
  printf '%s\n' "- Prefetch summary: \`$PREFETCH_SUMMARY\`"
  printf '%s\n' "- Browser prefetch result: \`$BROWSER_PREFETCH_RESULT\` (summary field: \`browser_result_path\`)"
  printf '%s\n' "- Prefetch stdout copy: \`$PREFETCH_STDOUT\`"
  printf '%s\n\n' "- Schedule run id: \`$RUN_ID\`"
}

write_source_prefetch_prompt() {
  local generated_prompt="$1"
  local prompt_file="$2"
  {
    print_source_prefetch_preamble
    cat "$prompt_file"
  } > "$generated_prompt"
}

build_finish_prompt() {
  local shortlist_path="$1"
  {
    print_source_prefetch_preamble
    printf '\n# Runner Article Prefetch\n\n'
    printf 'The schedule wrapper already ran Stage B full-text collection for current-run shortlisted URLs.\n'
    printf 'Use these local JSON artifacts as the only article full-text handoff for `scrape_and_enrich`.\n\n'
    printf '%s\n' "- Shortlist shard: \`$shortlist_path\`"
    printf '%s\n' "- Article prefetch result: \`$ARTICLE_PREFETCH_RESULT\`"
    printf '%s\n' "- Article prefetch summary: \`$ARTICLE_PREFETCH_SUMMARY\`"
    printf '%s\n' "- Finish draft path: \`$FINISH_DRAFT\`"
    printf '%s\n\n' "- Finish summary path: \`$FINISH_SUMMARY\`"
    cat "$FINISH_PROMPT_FILE"
  } > "$FINISH_PROMPT"
}

run_source_prefetch() {
  python3 "$PREFETCH_HELPER" \
    --schedule-id "$SCHEDULE_ID" \
    --run-id "$RUN_ID" \
    --repo-root "$REPO_ROOT" \
    --pretty > "$PREFETCH_STDOUT"
}

run_single_stage_schedule() {
  write_source_prefetch_prompt "$GENERATED_PROMPT" "$PROMPT_FILE"
  "$CODEX_BIN" exec \
    -C "$REPO_ROOT" \
    -s workspace-write \
    --json \
    --output-last-message "$LAST_MESSAGE" \
    - < "$GENERATED_PROMPT" > "$EVENT_LOG"
  printf 'Events: %s\n' "$EVENT_LOG"
  printf 'Final message: %s\n' "$LAST_MESSAGE"
}

run_weekday_staged_schedule() {
  if [ ! -f "$DISCOVERY_PROMPT_FILE" ]; then
    printf 'Discovery prompt file not found: %s\n' "$DISCOVERY_PROMPT_FILE" >&2
    exit 2
  fi
  if [ ! -f "$FINISH_PROMPT_FILE" ]; then
    printf 'Finish prompt file not found: %s\n' "$FINISH_PROMPT_FILE" >&2
    exit 2
  fi
  if [ ! -f "$ARTIFACT_HELPER" ]; then
    printf 'Artifact helper not found: %s\n' "$ARTIFACT_HELPER" >&2
    exit 2
  fi
  if [ ! -f "$ARTICLE_PREFETCH_HELPER" ]; then
    printf 'Article prefetch helper not found: %s\n' "$ARTICLE_PREFETCH_HELPER" >&2
    exit 2
  fi
  if [ ! -f "$STAGE_C_FINISH_HELPER" ]; then
    printf 'Stage C finish helper not found: %s\n' "$STAGE_C_FINISH_HELPER" >&2
    exit 2
  fi

  SHORTLIST_BEFORE_JSON="$(python3 "$ARTIFACT_HELPER" snapshot-shortlists \
    --repo-root "$REPO_ROOT" \
    --run-date "$RUN_DATE" \
    --source-group daily_core)"

  write_source_prefetch_prompt "$DISCOVERY_PROMPT" "$DISCOVERY_PROMPT_FILE"
  "$CODEX_BIN" exec \
    -C "$REPO_ROOT" \
    -s workspace-write \
    --json \
    --output-last-message "$DISCOVERY_LAST_MESSAGE" \
    - < "$DISCOVERY_PROMPT" > "$DISCOVERY_EVENT_LOG"

  SHORTLIST_PATH="$(python3 "$ARTIFACT_HELPER" find-new-shortlist \
    --repo-root "$REPO_ROOT" \
    --run-date "$RUN_DATE" \
    --source-group daily_core \
    --before-json "$SHORTLIST_BEFORE_JSON")"

  if ! python3 "$ARTICLE_PREFETCH_HELPER" \
    --repo-root "$REPO_ROOT" \
    --shortlist-path "$SHORTLIST_PATH" \
    --run-id "$RUN_ID" \
    --pretty > "$ARTICLE_PREFETCH_STDOUT"; then
    python3 "$ARTIFACT_HELPER" synthetic-article-prefetch \
      --repo-root "$REPO_ROOT" \
      --run-id "$RUN_ID" \
      --shortlist-path "$SHORTLIST_PATH" \
      --reason article_prefetch_stage_failed > "$ARTICLE_PREFETCH_STDOUT"
  fi

  if [ ! -f "$ARTICLE_PREFETCH_RESULT" ] || [ ! -f "$ARTICLE_PREFETCH_SUMMARY" ]; then
    python3 "$ARTIFACT_HELPER" synthetic-article-prefetch \
      --repo-root "$REPO_ROOT" \
      --run-id "$RUN_ID" \
      --shortlist-path "$SHORTLIST_PATH" \
      --reason article_prefetch_manifest_missing > "$ARTICLE_PREFETCH_STDOUT"
  fi

  build_finish_prompt "$SHORTLIST_PATH"
  "$CODEX_BIN" exec \
    -C "$REPO_ROOT" \
    -s workspace-write \
    --json \
    --output-last-message "$FINISH_LAST_MESSAGE" \
    - < "$FINISH_PROMPT" > "$FINISH_EVENT_LOG"

  python3 "$STAGE_C_FINISH_HELPER" \
    --repo-root "$REPO_ROOT" \
    --run-id "$RUN_ID" \
    --run-date "$RUN_DATE" \
    --source-group daily_core \
    --delivery-profile telegram_digest \
    --shortlist-path "$SHORTLIST_PATH" \
    --article-prefetch-result "$ARTICLE_PREFETCH_RESULT" \
    --draft-path "$FINISH_DRAFT" \
    --pretty > "$FINISH_SUMMARY"

  python3 "$ARTIFACT_HELPER" validate-finish-artifacts \
    --repo-root "$REPO_ROOT" \
    --run-id "$RUN_ID" \
    --run-date "$RUN_DATE" \
    --source-group daily_core \
    --delivery-profile telegram_digest \
    --require-finish-summary

  printf 'Discovery events: %s\n' "$DISCOVERY_EVENT_LOG"
  printf 'Discovery final message: %s\n' "$DISCOVERY_LAST_MESSAGE"
  printf 'Article prefetch summary: %s\n' "$ARTICLE_PREFETCH_SUMMARY"
  printf 'Finish materializer summary: %s\n' "$FINISH_SUMMARY"
  printf 'Finish events: %s\n' "$FINISH_EVENT_LOG"
  printf 'Finish final message: %s\n' "$FINISH_LAST_MESSAGE"
}

run_source_prefetch

if [ "$SCHEDULE_ID" = "weekday_digest" ]; then
  run_weekday_staged_schedule
else
  run_single_stage_schedule
fi

printf 'Codex schedule run complete: %s\n' "$RUN_ID"
