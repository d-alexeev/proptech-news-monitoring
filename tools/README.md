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
- **No state writes:** скрипты сами не пишут в `./.state/`. Это задача
  вызывающего runtime-слоя, который оформляет результат под контракт
  артефактов из `config/runtime/state_layout.yaml`.

## Состав

| Файл | Назначение |
|---|---|
| `rss_fetch.py` | Единый минимальный fetcher для `fetch_strategy: rss`, `html_scrape` и простых JSON/API источников вроде `itunes_api`. |
| `pdf_extract.py` | Enrichment-only PDF-to-text helper for shortlisted public PDFs such as Rightmove RNS documents. |
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
