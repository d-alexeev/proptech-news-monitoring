# Chrome operational notes

Chrome используется для источников с `fetch_strategy: chrome_scrape` и как
fallback для `fetch_strategy: blocked`, если политика в
`cowork/adapters/blocked_manual_access.md` этого не запрещает.

## Включение Claude in Chrome

В cowork-сессии Chrome доступен как MCP-коннектор `Claude in Chrome`.

1. Открыть `Settings → Desktop app → Computer use` и включить
   доступ для Cowork.
2. Установить расширение Claude in Chrome и авторизовать его в своём
   браузере (один раз).
3. Запустить обычный Chrome на той же машине, где идёт cowork-сессия, и
   оставить его открытым во время прогона.

После этого становятся доступны MCP-тулы `mcp__Claude_in_Chrome__*`
(`navigate`, `read_page`, `get_page_text`, `javascript_tool`, `find`,
`form_input`, `read_network_requests`, `read_console_messages`,
`tabs_create_mcp`, `tabs_close_mcp` и т.п.). Раннер вызывает их вместо
`requests.get()` для соответствующих `source_id`.

## Ограничения

- Claude in Chrome требует активного Chrome и активной cowork-сессии.
  Для cron/CI-запуска этот путь **не подходит** — там нужен headless
  раннер (Playwright/Puppeteer), но это за пределами текущей настройки.
- Любой шаг логина/капчи эскалируется через `change_request`, а не
  автоматизируется через `form_input`. Это требование
  `cowork/adapters/blocked_manual_access.md`.
- Full-text правило остаётся в силе: body через Chrome доступен
  **только** в `scrape_and_enrich`. В `monitor_sources` Chrome
  используется максимум для заголовков/сниппетов листинговых страниц.

## Карта источников → стратегия fetch

По `config/runtime/source-groups/`:

| source_id | group | fetch_strategy | Инструмент | Adapter |
|---|---|---|---|---|
| `aim_group_real_estate_intelligence` | daily_core | `rss` | `tools/rss_fetch.py` | — |
| `onlinemarketplaces` | daily_core | `chrome_scrape` | Claude in Chrome | `cowork/adapters/onlinemarketplaces_family.md` |
| `mike_delprete` | daily_core | `chrome_scrape` | Claude in Chrome | `cowork/adapters/mike_delprete_library.md` |
| `zillow_newsroom` | daily_core | `html_scrape` | Claude in Chrome или `rss_fetch.py --kind http` | `cowork/adapters/zillow_newsroom_html.md` |
| `costar_homes` | daily_core | `rss` | `tools/rss_fetch.py` | — |
| `redfin_news` | daily_core | `rss` | `tools/rss_fetch.py` | — |
| `rea_group_investor_centre` | daily_core | `blocked` | **не ходить**, `change_request` | `cowork/adapters/blocked_manual_access.md` |
| `rightmove_plc` | daily_core | `chrome_scrape` | Claude in Chrome | `cowork/adapters/rightmove_plc.md` |
| `similarweb_global_real_estate` | daily_core | `chrome_scrape` | Claude in Chrome | `cowork/adapters/similarweb_site_overview.md` |
| `property_portal_watch` | weekly_context | `chrome_scrape` | Claude in Chrome | — |
| `inman_tech_innovation` | weekly_context | `rss` | `tools/rss_fetch.py` | — |
| `similarweb_country_real_estate` | weekly_context | `chrome_scrape` | Claude in Chrome | `cowork/adapters/similarweb_site_overview.md` |
| `zillow_ios` | weekly_context | `itunes_api` | `rss_fetch.py --kind http` (iTunes lookup) | `cowork/adapters/itunes_lookup_api.md` |
| `zillow_android` | weekly_context | `chrome_scrape` | Claude in Chrome | `cowork/adapters/google_play_app_page.md` |
| `rightmove_ios` | weekly_context | `itunes_api` | `rss_fetch.py --kind http` | `cowork/adapters/itunes_lookup_api.md` |
| `rightmove_android` | weekly_context | `chrome_scrape` | Claude in Chrome | `cowork/adapters/google_play_app_page.md` |

## Протокол для раннера

На `monitor_sources`:

1. Резолвить `source_id -> fetch_strategy` из source-group config.
2. `rss` / `html_scrape` без JS — звать `tools/rss_fetch.py`.
3. `chrome_scrape` — загрузить соответствующий adapter из
   `cowork/adapters/` и работать через `mcp__Claude_in_Chrome__*`.
4. `blocked` — немедленно эмитить `change_request`, не пытаться обойти.
5. На всё, что вернуло `soft_fail` (HTTP 403/451/429, capttcha body,
   Cloudflare 5xx), также эмитить `change_request` через
   `cowork/shared/change_request_policy.md`.
