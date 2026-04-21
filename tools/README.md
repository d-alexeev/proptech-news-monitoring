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
  `2` — неверные аргументы; `10` — soft-fail, который должен превратиться
  в `change_request` (blocked/anti-bot, paywall, 4xx не-auth). Exit codes
  `3-9` зарезервированы.
- **Env vars:** читаются из process env. Ни один скрипт не пишет секреты в
  stdout и не логирует их в stderr.
- **No state writes:** скрипты сами не пишут в `./.state/`. Это задача
  вызывающего runtime-слоя, который оформляет результат под контракт
  артефактов из `config/runtime/state_layout.yaml`.

## Состав

| Файл | Назначение |
|---|---|
| `rss_fetch.py` | Fetch RSS/Atom или plain HTTP для `fetch_strategy: rss`/`html_scrape` источников. Выход: raw feed + items. |
| `telegram_send.py` | Доставка markdown в Telegram по `delivery_profile` из `schedule_bindings.yaml`. |
| `chrome_notes.md` | Операционка для `fetch_strategy: chrome_scrape` источников через Claude in Chrome. |

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
