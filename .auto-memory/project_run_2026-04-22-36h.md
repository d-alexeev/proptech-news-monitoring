---
name: Ежедневный прогон 36h — 22 апреля 2026
description: Стандартный 36h scheduled run после первого расширенного прогона (2-week lookback) на той же дате
type: project
---

Прогон выполнен 2026-04-21T23:15Z UTC (= 2026-04-22T02:15 Moscow). Lookback: 36 часов (с 2026-04-20T11:15Z).

**Why:** Это первый стандартный scheduled daily run (09:00 MSK) в рамках регулярного расписания. Предыдущий прогон на ту же дату был catch-up с 2-week lookback.

**How to apply:** С 2026-04-22 `.state/` содержит два набора артефактов на одну дату — первый (ID с 225014Z суффиксом) это 2-week, второй (с 231529Z суффиксом) это стандартный 36h. При следующих прогонах anti-repeat должен читать `2026-04-22__telegram_digest_36h.json` как самый свежий daily_brief.

**Топ истории 36h прогона:**
1. Portal pre-market listing war: все US-порталы приняли coming-soon (score 68.0)
2. Housfy M&A: выручка ×2 до €45M, EBITDA ×8.75 за счёт 12 поглощённых агентств (score 63.25)
3. Zillow rental surplus: +1.8% г/г (минимум с 2020), 40% концессий, dual shoppers (score 61.5)

**Слабые сигналы:**
- CoStar Q1 отчёт 28 апреля (score 52) — watch item
- Redfin: US home prices +0.1% YTD, Техас под давлением (score 44.25)

**Доставка:** Telegram — 5 частей, message IDs 18–22, 0 ошибок.

**Harvest тонкий:** 3 top + 2 weak — нормально для 36h окна после 2-week прогона.

**Blockers на следующий прогон:**
- CoStar RSS timeout 3й раз подряд — рассмотреть escalation change_request
- REA Group manual intake всё ещё не выполнен (first intake overdue)
- Inman paywall: ключевой источник по listing war — рассмотреть подписку или альтернативный парсинг
- Следить: CoStar Q1 earnings April 28 (breaking alert candidate если Homes.com показывает ускорение)
