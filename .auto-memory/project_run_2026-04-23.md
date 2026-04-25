---
name: Ежедневный прогон 2026-04-23 (36h scheduled)
description: Результаты scheduled прогона 23 апреля 2026 — 3 top + 1 weak, Telegram доставлен (IDs 38-39), blockers CoStar timeout x5, OLM chrome unavail
type: project
---

Стандартный scheduled прогон 36h lookback (с 2026-04-21T16:05Z по 2026-04-23T04:05Z).

**Top-истории:**
1. Avito IPO: Иван Таврин объявил готовность к IPO на форуме МосБиржи — score 88.25 (breaking alert candidate, >85 threshold)
2. Redfin: 53K contract fallthroughs в марте США (13.4%) — score 57.0
3. Beike/Beijing Lianjia: пилот «искренних продаж» — score 55.25

**Слабые сигналы:** Украина — Рада отклонила налог на маркетплейсы (score 44.5)

**Telegram:** доставлен, 2 части, message IDs 38-39

**Blockers:**
- CoStar RSS timeout — 5-й подряд, CR `cr__20260423T041000Z__costar_timeout` создан
- OnlineMarketplaces: chrome_scrape недоступен, CR `cr__20260423T041001Z__onlinemarketplaces_chrome` создан
- REA Group: blocked/manual (не изменилось)
- Mike DelPrete: stale (91д без публикаций, норм по адаптеру)

**Why:** Тонкий прогон по новостям — большинство источников в норме, но CoStar и OLM остаются проблемными. Avito IPO — самая важная история за последние прогоны.

**How to apply:** На следующем прогоне проверить, появились ли новости CoStar Q1 2026 earnings (28 апр), и убедиться что Avito IPO не попадёт под anti-repeat если за ночь выйдут дополнительные подробности.
