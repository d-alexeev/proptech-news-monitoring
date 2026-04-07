# Daily Digest Mechanism Review — Неделя 14, 2026
**Период тестирования:** 30 марта — 5 апреля 2026 (7 дней)
**Метод:** dry run × 7, данные из weekly-коллекции, строгий date cutoff по дням
**Цель:** проверить механизм формирования дайджеста, не инфраструктуру ingestion

---

## Что тестировалось

Серия из 7 ежедневных дайджестов симулировала запуск системы каждое утро в 09:00 с lookback_hours = 36. Для каждого дня использовались только данные с published_date ≤ дата запуска. Дедупликация между днями: item, включённый в digest N, не появляется в digest N+1.

---

## Покрытие по дням

| Дата | День | Новых items | Топ-событие | Источник |
|---|---|---|---|---|
| 30 мар | Вс | 1 | CoStar vs Zillow infringement | OMP |
| 31 мар | Пн | 1 | Apartments.com rent growth | CoStar IR |
| 1 апр | Вт | 1 | Rightmove £1.5B lawsuit | OMP |
| 2 апр | Ср | 5 | Avito Adtech, Zillow AI story, Lifull | AIM + Zillow |
| 3 апр | Чт | 5 | Opendoor/Doma, Realtor.com ChatGPT | AIM + OMP |
| 4 апр | Пт | 0* | — | — |
| 5 апр | Сб | 0 | — | — |

*На 4 апреля есть значимый материал Inman, но он из `weekly_context`, а не `daily_core`.

---

## Ключевые наблюдения

### 1. Паттерн публикационной активности — «горб в середине недели»

AIM Group и OnlineMarketplaces концентрируют материалы во вторник–четверг. Воскресенье и суббота — полностью пустые дни. Понедельник почти пустой. Это ожидаемо для B2B media.

**Вывод:** Расписание weekday_digest (пн–пт, 09:00) избыточно в начале недели. Альтернатива — tri-weekly формат (вт/чт/пт) с уплотнённым окном.

---

### 2. Inman в `weekly_context` создаёт структурный пробел в daily pipeline

4 апреля Inman опубликовал аналитический материал о переходе Realtor.com на AI-first search — один из самых значимых материалов недели. Он **не попал в daily digest**, потому что Inman находится в `weekly_context`.

Это создаёт ситуацию: пятничный daily digest пустой, а пятничный weekly digest (17:00) содержит главную новость. С точки зрения UX — неоптимально.

**Вариант решения A:** Перенести Inman в `daily_core` с более агрессивной фильтрацией по теме (сейчас весь фид, фильтр на этапе анализа).

**Вариант решения B:** Добавить `breaking_alert` логику для weekly_context источников: если item набирает score ≥ 85 из weekly_context — отправлять немедленно как alert, не ждать пятницы.

Вариант B сохраняет разделение источников и не увеличивает ежедневный шум.

---

### 3. Дедупликация работает корректно

Цепочка: CoStar vs Zillow (30 мар) → не повторяется 31 мар; Rightmove lawsuit (1 апр) → не повторяется 3 апр; Avito Adtech (2 апр) → не дублируется 3 апр. Дедуп по URL работает как ожидалось.

**Пограничный кейс:** один и тот же story (напр. Rightmove lawsuit) освещается несколькими источниками в разные дни. При текущей реализации первый источник «закрепляет» URL; второй источник — это другой URL — пройдёт дедуп по URL, но может быть поймам title_similarity_threshold = 0.9.

**Рекомендация:** добавить в dedupe.json поле `story_id` для кластеризации смежных coverage одной темы, чтобы аналитик знал: это не новое событие, а дополнительный угол.

---

### 4. Качество сигнала по дням неравномерно

- **Среда 2 апр и четверг 3 апр** — высокая плотность, 5 items каждый день, несколько HIGH-priority событий.
- **Понедельник–вторник** — 1 item в день, оба среднего приоритета или ниже.
- **Пятница** (без учёта Inman-пробела) — пустая.

Это означает, что еженедельный паттерн для Авито Real Estate аудитории может быть: **вторник — скромный дайджест, среда-четверг — главный сигнал, пятница — weekly с контекстом**. Такой ритм лучше соответствует естественной публикационной активности рынка.

---

### 5. AIM Group — главный источник daily_core сигнала

Из 11 уникальных новостных events за неделю 8 пришли первично через AIM Group RSS. OMP — 3 события (включая два HIGH-priority: Rightmove lawsuit и Realtor.com ChatGPT). CoStar IR — 1 data-release (Apartments.com). Zillow Newsroom — 1.

Redfin, Mike DelPrete, Rightmove PLC — ноль событий за неделю.

| Источник | Events | HIGH-priority |
|---|---|---|
| AIM Group | 8 | 1 (Opendoor/Doma) |
| OnlineMarketplaces | 3 | 2 (Rightmove lawsuit, Realtor.com) |
| CoStar IR | 1 | 0 |
| Zillow Newsroom | 1 | 0 |
| Inman | 1* | 1* (в weekly_context) |
| Redfin / Mike DelPrete / Rightmove PLC | 0 | — |

*не доступно в daily pipeline

---

### 6. Хронически недоступные источники

**REA Group** заблокирован на сетевом уровне в Cowork sandbox — это не CSP-ограничение, а IP/domain denylist. Не чинится без смены среды запуска. Рекомендуется: ручная проверка раз в неделю при выходе квартальных результатов, либо переход на другую среду исполнения.

**Similarweb rankings** требует логин для category pages. Individual site pages (`/website/zillow.com/#overview`) доступны без auth и дают: global rank, category rank, total visits, competitors. Стратегия уже обновлена в monitoring.yaml — нужно верифицировать что Chrome scrape individual pages работает стабильно.

**Rightmove PLC** имеет валидный RSS XML (WordPress 6.9.4), но 0 items: регуляторные новости используют custom post type не в дефолтном feed. Chrome scrape homepage — рабочий fallback. Покрытие Rightmove corporate news достаточно обеспечивается через OMP и AIM Group (оба покрыли £1.5B иск подробнее IR-сайта).

---

## Рекомендации по настройке

| Приоритет | Действие | Файл |
|---|---|---|
| Высокий | Добавить в `breaking_alert`: weekly_context items с score ≥ 85 → немедленный alert | monitoring.yaml |
| Средний | Перевести Inman в `daily_core` ИЛИ сохранить weekly_context + breaking_alert rule | monitoring.yaml |
| Средний | Добавить поле `story_id` в dedupe.json для кластеризации cross-source coverage | dedupe.json schema |
| Низкий | Рассмотреть tri-weekly расписание (вт/чт/пт) вместо пн–пт для daily_core | monitoring.yaml |
| Низкий | REA Group: добавить calendar reminder для ручной проверки при earnings dates | — |

---

## Вывод

Механизм формирования дайджеста работает корректно: дедуплиакция по URL стабильна, date cutoff применяется точно, scoring продуцирует предсказуемые приоритеты. Главный структурный gap — Inman в weekly_context: один из значимых материалов недели (Realtor.com AI-first) не попал в daily pipeline. Это решается через breaking_alert rule, а не через изменение архитектуры источников.

---

*Ревью подготовлено: 6 апреля 2026 | На основе dry run series Mar 30 – Apr 5*
