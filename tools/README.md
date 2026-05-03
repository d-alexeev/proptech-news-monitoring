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
| `telegram_send.py` | Доставка markdown в Telegram по `delivery_profile` из `schedule_bindings.yaml`. |
| `chrome_notes.md` | Операционка для `fetch_strategy: chrome_scrape` источников через Claude in Chrome. |

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
