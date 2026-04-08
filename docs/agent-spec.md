# Спецификация агента

> Legacy detailed specification.
>
> Этот документ полезен как расширенный business/context reference, но он не
> является canonical entrypoint для текущего runtime-дизайна.
>
> Current canonical docs:
>
> - [config/runtime/runtime_manifest.yaml](../config/runtime/runtime_manifest.yaml)
> - [docs/runtime-architecture.md](./runtime-architecture.md)
> - [docs/mode-catalog.md](./mode-catalog.md)
> - [docs/launch-rerun-dry-run.md](./launch-rerun-dry-run.md)
>
> Ссылки на `monitor-list.json`, `config/monitoring.yaml`, legacy `prompts/` и
> старый pipeline-path ниже должны трактоваться как historical or compatibility
> reference.

## 1. Задача агента

Агент мониторит мировой рынок proptech и выдает краткую, полезную для бизнеса сводку. Приоритет отдается не "интересным" новостям, а тем сигналам, которые могут:

- изменить ожидания пользователей рынка жилья
- повлиять на спрос и предложение объявлений
- изменить продуктовые стандарты marketplace и classified-платформ
- повлиять на лидогенерацию, monetization или conversion
- усилить или ослабить международные proptech-паттерны, которые позже могут прийти в Россию

## 2. Основной выход

Главный артефакт агента: Telegram-сообщение в канал.

Структура сообщения:

1. Заголовок дня
2. 3-7 ключевых новостей
3. Для каждой новости:
   - что произошло
   - почему это важно
   - возможное значение для Авито Недвижимости
   - ссылка на первоисточник
4. Блок "На что посмотреть команде Авито"
5. При необходимости: блок "Слабые сигналы"

## 3. Источники

Источники стоит разбить на 4 корзины.

### A. Отраслевые proptech-источники

- Propmodo
- Inman
- HousingWire
- TechCrunch / Fintech / Marketplace sections
- Crunchbase News
- VentureBeat, если есть релевантные AI/marketplace материалы
- профильные VC-блоги и newsletter по real estate tech

### B. Источники о компаниях и сделках

- пресс-релизы компаний
- блоги Zillow, Redfin, Realtor.com, CoStar, Rightmove, Domain, REA Group, Opendoor, Compass
- базы funding/M&A/launches

### C. Макросигналы

- ипотека и affordability
- аренда и vacancy
- regulation вокруг short-term rental, data sharing, AI, advertising transparency
- изменения consumer behavior в real estate journey

### D. Технологические сигналы

- AI tooling for listing enrichment
- pricing/recommendation engines
- lead qualification
- CRM and broker workflows
- verification, fraud, identity, trust and safety
- automation for landlords, developers and agents

## 4. Что считать важной новостью

Каждой новости присваивается общий приоритет по шкале 0-100.

Рекомендуемая формула:

- 35%: релевантность для модели classified/marketplace в недвижимости
- 25%: масштаб события
- 20%: вероятность переноса паттерна на рынок Авито
- 10%: срочность
- 10%: новизна сигнала

### 4.1. Сигналы высокой важности

- крупные продуктовые запуски у Zillow, Redfin, Rightmove, REA, CoStar и похожих игроков
- M&A, которые меняют распределение данных, трафика, CRM или transaction flow
- новые AI-инструменты, заметно улучшающие search, listing quality, agent productivity, pricing
- регуляторные изменения, которые могут переопределить правила рекламы, данных, identity или disclosure
- признаки смены пользовательского поведения: рост self-serve, рост demand for rentals, shift to affordability tools
- новые модели монетизации: subscriptions, performance fees, promoted listings, bundled services

### 4.2. Сигналы средней важности

- раунды финансирования в нишевых proptech-компаниях
- локальные партнерства
- продуктовые эксперименты без доказанного масштаба
- региональные кейсы, полезные как ранний индикатор

### 4.3. Сигналы низкой важности

- общие PR-объявления без продуктового или рыночного эффекта
- повторяющиеся статьи без новых данных
- локальные новости без применимого паттерна

## 5. Приоритизация под Авито Недвижимость

Агент должен смотреть на новость через набор конкретных линз.

### Линзы оценки

- Listings supply: может ли событие повлиять на количество и качество объявлений?
- Demand capture: меняет ли это способ, которым пользователи ищут жилье?
- Lead funnel: влияет ли это на конверсию в контакт, чат, звонок, заявку?
- Monetization: появляется ли новый работающий формат платного продвижения или fee model?
- Data moat: усиливает ли это контроль над данными, оценкой цены, CRM или transaction intelligence?
- Trust and safety: меняет ли это верификацию, качество контента, fraud control?
- Agent/developer tools: повышает ли это продуктивность профессиональных продавцов и агентств?
- Strategic adjacency: приближает ли это площадку к ипотеке, сделке, аренде, ремонту или AI-concierge?

### Дополнительный коэффициент

Если новость напрямую затрагивает один из этих вопросов, агент повышает приоритет:

- AI in search / recommendations
- seller and agent productivity
- paid visibility products
- lead routing and qualification
- verified listings
- rental marketplace models
- developer ecosystem and new-build workflows

## 6. Выходной формат Telegram-сводки

Рекомендуемый стиль: коротко, делово, без "воды".

Шаблон:

```text
PropTech Monitor | 24 Mar 2026

1. [Высокий приоритет] Zillow launched ...
Что произошло: ...
Почему важно: ...
Для Авито: ...
Источник: ...

2. [Средний приоритет] ...

Что посмотреть:
- ...
- ...

Слабые сигналы:
- ...
```

## 7. Частота запусков

Базовый режим:

- Ежедневно по будням в 09:00 Europe/Moscow
- Weekly digest по пятницам в 17:00 Europe/Moscow

Дополнительно:

- внеплановый alert, если событие получило приоритет 85+

## 8. Архитектура пайплайна

### Шаг 1. Сбор

На входе:

- RSS
- официальные блоги
- curated search queries
- при наличии доступа: news APIs

На выходе:

- список candidate items со ссылкой, заголовком, временем, источником, фрагментом текста

### Шаг 2. Очистка

- дедупликация по URL и canonical URL
- семантическая дедупликация через LLM (`prompts/semantic_deduplicator.md`) — определяет, описывают ли разные статьи одно и то же событие, даже при разных заголовках и источниках; fallback на title similarity при сбое LLM
- фильтрация старых новостей
- фильтрация слабых перепечаток

### Шаг 3. Первичная классификация

Для каждой новости:

- topic: marketplace / rentals / mortgage / AI / CRM / regulation / M&A / funding / other
- geography
- company entities
- event type

### Шаг 4. Скоринг

LLM или rule-based scorer оценивает:

- business impact
- Avito relevance
- urgency
- novelty
- confidence

### Шаг 4.5. Контекстуализация

После скоринга, до сборки сводки: для каждой новости агент проверяет архив последних 30 дней (`delivery-log.json` + `digests/`) через `prompts/contextualizer.md`. Если событие является продолжением ранее отслеженной истории, в блок новости добавляется строка `📎 Контекст:` с отсылкой к исходному дайджесту.

### Шаг 5. Сборка сводки

Агент выбирает:

- top 3-7 новостей (с контекстными строками там, где они найдены)
- 2-4 слабых сигнала
- 2-3 action points для команды

Для weekly digest: перед финальной сборкой запускается `prompts/trend_synthesizer.md` — синтез 1–3 надстраивающих трендов из материалов текущей и предыдущих 4 недель. Результат вставляется отдельной секцией между главными новостями и «Что посмотреть».

### Шаг 6. Доставка

Отправка в Telegram Bot API:

- `sendMessage` в канал
- поддержка Markdown
- при длинной сводке разделение на 2-3 сообщения

## 9. Схема сущностей данных

Полная схема хранится в `config/monitoring.yaml` (секция `item_schema`). Ниже — краткое справочное описание.

### Raw item (после сбора, до обогащения)

| Поле | Тип | Описание |
|---|---|---|
| `url` | string | Канонический URL статьи. Первичный ключ дедупликации. |
| `title` | string | Заголовок как получен из источника. |
| `published` | ISO date | Дата публикации (YYYY-MM-DD). |
| `source_id` | string | ID источника из `monitoring.yaml`. |
| `fetch_strategy_used` | string | `rss` / `html_scrape` / `api` — как была получена статья. |
| `fetched_at` | ISO datetime | Время сбора агентом. |
| `raw_snippet` | string | Первые 600–800 символов оригинального текста (не интерпретация). Используется для семантической дедупликации и контекстуализации. |

### Enriched item (после классификации и скоринга)

Содержит все поля raw-стадии плюс:

| Поле | Тип | Описание |
|---|---|---|
| `companies` | string[] | Упомянутые компании. Используется контекстуализатором и персонализатором. |
| `regions` | string[] | Географические регионы. |
| `topic_tags` | string[] | 1–4 тега из контролируемого словаря `topic_vocabulary` (см. `monitoring.yaml`). |
| `event_type` | string | Тип события: `product_launch`, `m_and_a_announcement`, `earnings_report` и др. (12 типов в `monitoring.yaml`). |
| `priority_score` | int 0–100 | Итоговый балл по `scoring.weights` из `monitoring.yaml`. |
| `confidence` | float 0–1 | Уверенность в классификации и скоринге. |
| `stakeholder_scores` | map | Карта `profile_id → score`, предвычисленная для каждого профиля из `config/stakeholders.yaml`. Включена когда `pipeline.stakeholder_personalization.enabled = true`. |
| `analyst_summary` | string | Краткое описание события (интерпретация аналитика — не цитата источника). |
| `why_it_matters` | string | Почему событие важно для рынка. |
| `avito_implication` | string | Конкретный вывод или гипотеза для Авито Недвижимость. |
| `story_id` | string | Кластеризует статьи, описывающие одно событие из разных источников. Формат: `story_<slug>_<yyyymm>`. |

### Словарь тем (topic_vocabulary)

Полный список в `config/monitoring.yaml`. Группы:

- **product**: `product_launch`, `product_update`, `ai_search`, `recommendations`, `listing_quality`, `pre_market_listings`, `mobile_product`
- **commercial**: `monetization`, `paid_visibility`, `subscriptions`, `agent_relations`, `lead_qualification`, `listing_war`, `transaction_tech`
- **strategic**: `m_and_a`, `competitive_move`, `market_dynamics`, `regulation`, `funding`, `talent_leadership`
- **tech**: `ai_ml`, `data_infra`, `trust_safety`
- **macro**: `consumer_behaviour`, `macro_market`

## 10. Правила качества

- Не включать больше 7 основных новостей за выпуск.
- Не повторять одну и ту же тему несколько дней подряд без нового угла.
- Всегда указывать первоисточник или наиболее близкий к нему материал.
- Если уверенность низкая, помечать это как слабый сигнал.
- Не писать громких выводов без факта или явной аналитической оговорки.

## 11. Telegram delivery

Для отправки в канал нужен:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` канала
- бот, добавленный администратором канала

Опционально:

- thread/topic id для отправки в конкретную тему
- подпись или брендирование сводки

## 12. MVP-план реализации

### Текущий статус (апрель 2026)

Пайплайн запущен и работает в production-режиме:

- 19 источников сконфигурированы в `monitor-list.json` + `monitoring.yaml`
- ежедневные сводки и weekly digest генерируются и сохраняются в `digests/`
- дедупликация (URL + title similarity), классификация и скоринг реализованы
- Telegram delivery сконфигурирован
- LLM-слой пока работает как эвристическая заглушка — переход на реальную модель является ближайшим приоритетом
- три новых LLM-промпта написаны и подключены в конфиг, ожидают активации реального LLM-слоя: `semantic_deduplicator.md`, `contextualizer.md`, `trend_synthesizer.md`

### MVP v1 ✓

- ✓ 19 источников (daily_core + weekly_context)
- ✓ ежедневный запуск по будням в 09:00 MSK
- ✓ топ-5 новостей + до 4 слабых сигналов
- ✓ Telegram delivery (digest, weekly, alert profiles)
- ⚠️ LLM summarization — реализовано как заглушка; промпты готовы, generation на реальной модели — следующий шаг

### MVP v2

- ✓ weekly digest (каждую пятницу в 17:00 MSK)
- ✓ alert mode — сконфигурирован (`breaking_alert`, порог score ≥ 85), не тестировался в боевом режиме
- ✓ tracking компаний-конкурентов (`selection.tracked_companies`: Zillow, Rightmove, CoStar, REA Group и др.)
- ✓ memory of previous sends — `dedupe.json` ведёт историю виденных статей и `story_id`
- ⚠️ семантическая дедупликация — промпт готов (`semantic_deduplicator.md`), требует активного LLM
- ⚠️ контекстуализация (исторический контекст из архива) — промпт готов (`contextualizer.md`), требует активного LLM

### MVP v3

- ❌ синтез трендов — промпт готов (`trend_synthesizer.md`), требует активного LLM и накопленного архива дайджестов
- ❌ feedback loop от команды (реакции / thumbs up/down в Telegram)
- ⚠️ персонализация под аудитории — конфиг и промпт готовы, пайплайн не активирован:
  - `config/stakeholders.yaml` — 5 профилей: `default`, `product`, `strategy`, `commercial`, `tech`
  - `prompts/digest_personalizer.md` — промпт персонализации
  - `pipeline.stakeholder_personalization.enabled = false` в `monitoring.yaml` — включить для активации

---

## 13. Стейкхолдерские профили

Персонализация дайджестов под разные аудитории реализована через систему профилей. Активируется через `pipeline.stakeholder_personalization.enabled = true` в `monitoring.yaml`.

### Архитектура

Шаг 4 пайплайна (скоринг) расширяется: для каждой статьи вычисляются `stakeholder_scores` — карта `profile_id → score`, используя `lens_weights` каждого профиля. Это позволяет выполнять маршрутизацию и фильтрацию в O(1) без повторного скоринга.

Шаг 5 (сборка сводки) при включённой персонализации запускает `prompts/digest_personalizer.md` для каждого активного профиля, передавая отфильтрованные и переранжированные items + параметры профиля.

### Конфиг профилей (`config/stakeholders.yaml`)

Каждый профиль задаёт:

| Параметр | Описание |
|---|---|
| `min_priority_score` | Минимальный балл для попадания в дайджест этого профиля. |
| `max_top_items` / `max_weak_signals` | Лимиты секций. |
| `topic_filter.include` / `exclude` | Фильтр по тегам `topic_vocabulary`. |
| `lens_weights` | Переопределяют глобальные `scoring.weights` для расчёта `stakeholder_scores`. |
| `format.detail_level` | `brief` / `standard` / `detailed` — влияет на длину блоков. |
| `format.include_sections` | Список секций дайджеста. Кастомные: `try_now`, `strategic_implications`, `monetization_signals`, `tech_patterns`. |
| `format.extra_instructions` | Дополнительные инструкции для персонализатора. |
| `delivery.telegram_profile` | Профиль доставки из `monitoring.yaml`. |
| `delivery.thread_id_env` | Переменная окружения с ID треда в Telegram (для раздельных топиков). |

### Текущие профили

| Profile ID | Аудитория | min_score | detail_level | Кастомная секция |
|---|---|---|---|---|
| `default` | Все подписчики | 55 | standard | — |
| `product` | Product, Design, UX | 50 | detailed | `try_now` |
| `strategy` | Strategy, BD, Leadership | 65 | brief | `strategic_implications` |
| `commercial` | Monetization, Sales, Agent Relations | 55 | standard | `monetization_signals` |
| `tech` | Engineering, ML, Data Science | 45 | detailed | `tech_patterns` |

### Добавление нового профиля

1. Добавить запись в `config/stakeholders.yaml` по аналогии с существующими.
2. Если нужна новая кастомная секция — добавить её обработку в `prompts/digest_personalizer.md`.
3. При необходимости отдельного Telegram-треда — прописать `thread_id_env` в профиле и добавить переменную окружения.
