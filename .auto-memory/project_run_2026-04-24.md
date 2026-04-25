---
name: Ежедневный прогон 2026-04-24 (36h scheduled)
description: Результаты scheduled прогона 24 апреля 2026 — 4 top + 2 weak; Telegram доставлен (IDs 41-42); blockers CoStar timeout x6, OLM JS-парсинг
type: project
---

Стандартный scheduled прогон 36h lookback (с 2026-04-22T16:05Z по 2026-04-24T04:05Z).

**Top-истории:**
1. Moat point: Will data really save portals from AI disruption? — score 76.0 (AIM Group, global, paywall snippet)
2. Lifull Home's: 5-кратный рост автодетектирования bait-and-switch — score 68.75 (AIM Group, JP, paywall snippet)
3. Zillow: 18.5% домов в США pending за 7 дней; рынок на двух скоростях — score 62.0 (Zillow Newsroom, US, full)
4. «Этажи» (РФ): выручка +53% до 1.6 млрд руб., прибыль +50% — score 61.0 (AIM Group, RU, paywall snippet)

**Слабые сигналы:** Redfin новые листинги весна (54.25), PropAI Dubai восстановление (52.0)

**Anti-repeat исключены:** story_avito_ipo_2026, story_us_contract_fallthroughs_2026, story_beike_sincere_sale_2026, story_ukraine_marketplace_tax_2026

**Telegram:** доставлен, 2 части, message IDs 41-42

**QA verdict:** pass_with_notes — 3/4 top items snippet_fallback; нет фактических ошибок.

**Blockers:**
- CoStar RSS timeout — 6-й подряд, активный CR `cr__20260423T041000Z__costar_timeout`
- OnlineMarketplaces: JS-листинг не парсится без Chrome MCP, активный CR `cr__20260423T041001Z__onlinemarketplaces_chrome`
- REA Group: blocked/manual (постоянно)
- Mike DelPrete: stale 92 дня (норм по адаптеру)

**Watchlist следующего прогона:**
- CoStar Q1 2026 earnings ожидаются ~28 апреля 2026 — высокий приоритет
- Если Avito IPO выйдут новые подробности — не будет под anti-repeat (story_avito_ipo_2026 уже прошёл 23 апреля, следующий прогон может включить развитие истории с новым score)

**Why:** Хороший прогон по качеству историй (портальная стратегия, antifrod, US market data, РФ конкурент). 3 из 4 AIM-историй заперты за пейволлом — стандартная ситуация, snippet_fallback работает корректно.

**How to apply:** На следующем прогоне 25 апреля приоритизировать поиск CoStar альтернатив и проверить, появились ли новые данные по Avito IPO.
