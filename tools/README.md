# tools/

Исполняемые утилиты раннера PropTech News Monitoring.

Этот каталог — **не runtime source-of-truth**. Canonical runtime layer остаётся
в `cowork/`, `config/runtime/` и `docs/`. Скрипты здесь нужны, чтобы внешний
раннер (или я, в режиме Claude Cowork) мог выполнять I/O-шаги, которые
описаны в mode prompts: fetch источников, доставку в Telegram и вспомогательные
операции.

## Контракт

Все скрипты следуют одному соглашению.

- **Stdin/stdout:** где возможно, вход — JSON в stdin, выход — одна JSON-строка
  в stdout. Логи и диагностика — только в stderr.
- **Exit codes:** `0` — успех; `1` — ошибка исполнения (network/parse/auth);
  `2` — неверные аргументы; `10` — все результаты завершились soft-fail,
  а вызывающий runtime решает по adapter policy, нужен ли `change_request`,
  manual reminder, retry или snippet fallback. Exit codes
  `3-9` зарезервированы.
- **Env vars:** читаются из process env. Ни один скрипт не пишет секреты в
  stdout и не логирует их в stderr.
- **State writes:** low-level data helpers such as `rss_fetch.py` and
  `pdf_extract.py` do not write `./.state/`. Runner orchestration helpers may
  write narrowly documented evidence artifacts when they own that runtime step;
  today this exception is `source_discovery_prefetch.py`, which writes only
  `.state/codex-runs/` prefetch evidence for the scheduled agent to consume.

## Состав

| Файл | Назначение |
|---|---|
| `rss_fetch.py` | Единый минимальный fetcher для `fetch_strategy: rss`, `html_scrape` и простых JSON/API источников вроде `itunes_api`. |
| `source_discovery_prefetch.py` | Runner-side static source prefetch for scheduled runs before the inner Codex agent starts. |
| `pdf_extract.py` | Enrichment-only PDF-to-text helper for shortlisted public PDFs such as Rightmove RNS documents. |
| `validate_runtime_artifacts.py` | Offline validator for source adapter resolution, compact state fixtures, change-request fixtures, full-text boundaries, and runner integration dry-run maps. |
| `telegram_send.py` | Доставка markdown в Telegram по `delivery_profile` из `schedule_bindings.yaml`. |
| `chrome_notes.md` | Bounded browser fallback contract for `fetch_strategy: chrome_scrape` and explicit adapter fallback cases. |

## `rss_fetch.py`

`rss_fetch.py` — один JSON-in/JSON-out интерфейс для статического получения
данных. Он не знает source-specific селекторы и не нормализует конкретные
сайты; runner/Codex применяет adapter-aware правила после получения результата.

Invocation mapping:

| Source config | Fetcher invocation | Output contract |
|---|---|---|
| `fetch_strategy: rss` + `rss_feed` | `kind=rss`, `url=<rss_feed>` | `items[]` parsed from RSS/Atom; `body: null`; HTTP metadata included. |
| `fetch_strategy: html_scrape` + URL | `kind=http`, `url=<page URL>` | Raw `body` with HTML/text; `items: []`; HTTP metadata included. |
| `fetch_strategy: itunes_api` + `itunes_api_url` | `kind=http`, `url=<itunes_api_url>` | Raw JSON `body`; `items: []`; `content_type` identifies JSON when origin sends it. |

Single-source examples:

```bash
python3 tools/rss_fetch.py \
  --source-id inman_tech_innovation \
  --url https://feeds.feedburner.com/inmannews \
  --kind rss

python3 tools/rss_fetch.py \
  --source-id zillow_ios \
  --url 'https://itunes.apple.com/lookup?id=310738695&country=us' \
  --kind http
```

Batch example:

```bash
printf '%s\n' '{"sources":[{"source_id":"inman_tech_innovation","url":"https://feeds.feedburner.com/inmannews","kind":"rss"},{"source_id":"zillow_ios","url":"https://itunes.apple.com/lookup?id=310738695&country=us","kind":"http"}]}' \
  | python3 tools/rss_fetch.py --stdin
```

The fetcher emits exactly one JSON document to stdout. It does not write
`.state/`, does not create runtime artifacts, and does not decide whether a
result becomes a shortlist item, digest item, full-text enrichment, or
`change_request`.

Exit codes follow the emitted batch status: `success` and `partial_success`
exit `0`; `failed` and `environment_failure` exit `1`; invalid invocation exits
`2`; `soft_failed` exits `10`. A mixed batch with one hard source error and one
successful source is therefore `batch_status="failed"` and exits `1`. Source-level
soft fails remain nonfatal unless every source soft-failed.

Soft-fail labels are explicit and stable for runner handling:

| Label | Typical trigger | Boundary |
|---|---|---|
| `blocked_or_paywall` | HTTP 401/402/403/451 | Caller decides whether this is a change request, manual reminder, or snippet fallback per adapter policy. |
| `rate_limited` | HTTP 429 | Caller retries on a later run or records source health; fetcher does not rotate proxies. |
| `origin_blocked` | Cloudflare-origin 520-524 family | Caller treats as source/tool access issue. |
| `anti_bot` | CAPTCHA, access-denied, or human-check body text | No CAPTCHA bypass or login automation. |
| `timeout` | connect/read timeout after configured retries | Transient soft failure; no state write. |

Offline contract coverage lives in `tools/test_rss_fetch.py`, including the
regular `inman_tech_innovation` RSS path and iTunes API via `kind=http`.

## `source_discovery_prefetch.py`

`source_discovery_prefetch.py` runs before scheduled `codex exec` jobs. It reads
`schedule_bindings.yaml`, resolves configured source groups, fetches only static
sources through `rss_fetch.py`, and writes local evidence artifacts under
`.state/codex-runs/`.

It intentionally does not create `.state/raw/` or `.state/shortlists/` shards.
The scheduled agent remains responsible for interpreting the evidence under
`monitor_sources` contracts. Configured `chrome_scrape` sources are reported as
`not_attempted` until a non-interactive browser runner exists.

Example:

```bash
python3 tools/source_discovery_prefetch.py \
  --schedule-id weekday_digest \
  --run-id 20260504T100000Z-weekday_digest \
  --repo-root . \
  --pretty
```

Output is a compact JSON summary with artifact paths:

- `*-source-prefetch-fetch-result.json`
- `*-source-prefetch-dns-check.json`
- `*-source-prefetch-summary.json`

Offline contract coverage lives in `tools/test_source_discovery_prefetch.py`.

## `pdf_extract.py`

`pdf_extract.py` extracts compact text and metadata from public PDFs only after
an item has been shortlisted for `scrape_and_enrich`. It is not a discovery
tool, and `monitor_sources` must not call it or consume its extracted body text.
Typical use is Rightmove PLC RNS enrichment after static discovery has found a
public PDF link.

The helper accepts a local runner-provided PDF path or downloads a public PDF
URL, emits exactly one JSON document to stdout, and writes no `.state/` files.
Diagnostics go to stderr. It does not perform OCR, table reconstruction, bulk
archive download, login, CAPTCHA handling, paywall bypass, or live scraping.

Single-source examples:

```bash
python3 tools/pdf_extract.py \
  --source-id rightmove_plc_rns \
  --path ./rightmove-rns.pdf

python3 tools/pdf_extract.py \
  --source-id rightmove_plc_rns \
  --url https://example.test/rightmove-rns.pdf
```

Batch example:

```bash
printf '%s\n' '{"sources":[{"source_id":"rightmove_plc_rns","url":"https://example.test/rightmove-rns.pdf","kind":"pdf"}]}' \
  | python3 tools/pdf_extract.py --stdin
```

Each result includes `source_id`, `url` or `path`, `kind: pdf`, `metadata`
(`page_count`, PDF title/author when available, and download metadata for URL
inputs), compact `text`, `text_char_count`, `error`, `soft_fail`, and
`body_status_hint`. `scrape_and_enrich` may normalize `body_status_hint` into
the existing `body_status` policy: `full` for useful text, `snippet_fallback`
for too little extractable text, or `paywall_stub` for blocked/download
failures.

Resource limits are intentionally modest for enrichment use. URL downloads use
`max_bytes` / `--max-bytes` with a default 5 MB budget, precheck
`Content-Length`, and stop chunked reads before parsing if the budget is
exceeded. Text extraction uses `max_pages` / `--max-pages` with a default
8-page parser window and stops after enough compact text is collected for
`max_chars`.

Offline contract coverage lives in `tools/test_pdf_extract.py`; the Rightmove
enrichment-only boundary is represented in
`config/runtime/mode-fixtures/runner_pdf_extract_rightmove.yaml`.

## Browser fallback

Browser fallback is documented in `tools/chrome_notes.md`. It is separate from
`rss_fetch.py` and is allowed only for configured `chrome_scrape` sources or
explicit adapter fallback cases after static fetch is insufficient. It must not
be used for `manual_only_permanent` sources, login, CAPTCHA, paywall bypass, or
proxy workarounds.

Local interactive Codex/browser use is an operator interface. Cron/server runs
need a future headless implementation that emits the same `kind: browser`
JSON-shaped result; RT-M3 defines that output contract but does not add a live
browser automation script.

## `validate_runtime_artifacts.py`

`validate_runtime_artifacts.py` is an offline review gate for runner artifacts.
It checks that configured source IDs resolve through `cowork/adapters/source_map.md`
or `none`, validates required fields and lightweight types for the sample
`raw_candidate`, `shortlisted_item`, `enriched_item`, `run_manifest`, and
`change_request` artifacts, validates mode fixtures that expect
`change_request` output, and scans non-enrichment mode fixtures plus unsafe
`scrape_and_enrich` sections for forbidden full-text fields such as
`article_file`, `full_text`, `body_text`, and non-null `body`. It also validates
the RT-M6 runner integration dry-run map so every configured `daily_core` and
`weekly_context` source has exactly one primary minimal tool path, explicit
blocked/manual handling, fixture coverage, and residual live-fetch risk notes.

Commands:

```bash
python3 tools/validate_runtime_artifacts.py --check adapters
python3 tools/validate_runtime_artifacts.py --check fixtures
python3 tools/validate_runtime_artifacts.py --check full-text-boundary
python3 tools/validate_runtime_artifacts.py --check runner-integration
python3 tools/validate_runtime_artifacts.py --check all
```

The validator performs no live source fetch, digest editorial scoring check, or
Telegram send validation.

## Зависимости

Смотри `tools/requirements.txt`. Раннер должен использовать изолированное
окружение (virtualenv или container). Установка:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/requirements.txt
```

## Env

Скрипты ожидают переменные из `.env.example` в корне репо. В cowork-сессии
Claude может читать их через process env; при локальном запуске удобнее
`direnv` или `dotenv`:

```bash
set -a; source .env; set +a
```

`.env` не коммитится (см. `.gitignore`).
