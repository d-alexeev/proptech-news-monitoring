# PropTech News Monitoring

Агент, который регулярно отслеживает ключевые события мирового proptech-рынка, приоритизирует их по потенциальному влиянию на Авито Недвижимость и отправляет короткие сводки в Telegram-канал.

## Цель

Агент должен не просто собирать новости, а отвечать на вопрос:

> "Что из происходящего на глобальном рынке proptech может повлиять на стратегию, продукт, монетизацию, спрос, supply или конкурентный ландшафт Авито Недвижимости?"

---

## Структура проекта

```
PropTech News Monitoring/
├── .env.example                      ← шаблон переменных окружения
├── monitor-list.json                 ← реестр источников мониторинга
│
├── config/
│   ├── monitoring.yaml               ← боевой runtime-конфиг агента
│   └── monitoring.example.yaml       ← пример конфига с комментариями
│
├── prompts/
│   ├── news_analyst.md               ← системный промпт LLM-аналитика (классификация, скоринг, синтез)
│   ├── semantic_deduplicator.md      ← семантическая дедупликация (JTBD-06)
│   ├── trend_synthesizer.md          ← синтез трендов из нескольких новостей (JTBD-13)
│   └── contextualizer.md             ← исторический контекст из архива дайджестов (JTBD-15)
│
├── digests/                          ← сгенерированные выпуски
│   ├── YYYY-MM-DD-daily.md           ← ежедневные сводки
│   └── YYYY-WNN-weekly-digest.md     ← еженедельные обзоры
│
├── docs/
│   ├── agent-spec.md                 ← полная спецификация агента
│   ├── runbook.md                    ← инструкция по запуску
│   ├── llm-jtbd-analysis-v2.md       ← приоритизация LLM-задач (актуальная)
│   ├── benchmark-design.md           ← дизайн benchmark-сьюта
│   ├── daily-digest-mechanism-review.md ← разбор механики daily digest
│   └── rss-api-audit.md              ← аудит RSS и API источников
│
├── benchmark/                        ← LLM benchmark suite
│   ├── README.md                     ← описание и метрики
│   └── datasets/
│       ├── jtbd-06-deduplication/    ← F1 ≥ 0.80
│       ├── jtbd-07-classification/   ← Macro-F1 ≥ 0.75 (запускать первым)
│       ├── jtbd-08-scoring/          ← Spearman ρ ≥ 0.75
│       └── jtbd-09-breaking-alert/   ← Precision ≥ 0.85
│
└── .state/                           ← runtime-состояние агента (gitignore)
    ├── dedupe.json                   ← индекс дедупликации
    ├── delivery-log.json             ← лог отправленных сводок
    ├── batch-progress.json           ← прогресс текущего прогона
    └── raw/                          ← собранные сырые данные
```

---

## Быстрый старт

### 1. Переменные окружения

Скопировать `.env.example` в `.env` и заполнить:

```bash
cp .env.example .env
```

| Переменная | Назначение |
|---|---|
| `OPENAI_API_KEY` | Ключ LLM-провайдера |
| `TELEGRAM_BOT_TOKEN` | Токен бота |
| `TELEGRAM_CHAT_ID` | ID канала (вида `-100...`) |
| `TELEGRAM_MESSAGE_THREAD_ID` | ID топика, если канал с темами |

### 2. Конфиг

Основной конфиг — `config/monitoring.yaml`. Включает:

- расписание запусков
- список source groups из `monitor-list.json`
- веса скоринга
- пороги отбора и delivery-профили

### 3. Запуск

Раннер поддерживает три режима:

```bash
runner --config config/monitoring.yaml --schedule weekday_digest
runner --config config/monitoring.yaml --schedule weekly_digest
runner --config config/monitoring.yaml --schedule breaking_alert
runner --config config/monitoring.yaml --schedule weekday_digest --dry-run
```

Подробная инструкция — в [docs/runbook.md](docs/runbook.md).

---

## Логика пайплайна

1. **Сбор** — читает активные источники из `monitor-list.json` по конфигу.
2. **Дедупликация** — по URL, canonical URL и семантическому сходству заголовков.
3. **Классификация** — topic, geography, company entities, event type.
4. **Скоринг** — LLM оценивает по 5 измерениям: marketplace relevance, event scale, portability to Avito, urgency, novelty.
5. **Сборка сводки** — top 3–7 новостей + слабые сигналы + action points.
6. **Доставка** — Telegram Bot API, с разбиением длинных сообщений на части.

Детальная архитектура — в [docs/agent-spec.md](docs/agent-spec.md).

---

## Расписание

| Режим | Когда | Порог |
|---|---|---|
| Ежедневная сводка | Будни, 09:00 MSK | priority ≥ 55 |
| Weekly digest | Пятница, 17:00 MSK | — |
| Breaking alert | Непрерывно | priority ≥ 85 |

---

## Скоринг новостей

Каждой новости присваивается приоритет 0–100 по формуле:

| Измерение | Вес |
|---|---|
| Релевантность для classified/marketplace | 35% |
| Масштаб события | 25% |
| Вероятность переноса паттерна на Авито | 20% |
| Срочность | 10% |
| Новизна сигнала | 10% |

Подробнее о критериях — в [docs/agent-spec.md](docs/agent-spec.md).

---

## LLM Benchmark

В папке `benchmark/` — тест-сьют для оценки качества LLM по ключевым задачам агента. Четыре датасета, основанных на реальных данных проекта:

- **JTBD-07** — классификация сигнала (30 кейсов)
- **JTBD-09** — breaking alert detection (25 кейсов)
- **JTBD-08** — скоринг релевантности (15 кейсов с полными текстами)
- **JTBD-06** — дедупликация (15 пар статей)

Инструкция по прогону и важные edge-кейсы — в [benchmark/README.md](benchmark/README.md).

---

## Ключевые документы

| Документ | Назначение |
|---|---|
| [docs/agent-spec.md](docs/agent-spec.md) | Полная спецификация: источники, скоринг, форматы, MVP-план |
| [docs/runbook.md](docs/runbook.md) | Пошаговая инструкция запуска |
| [docs/llm-jtbd-analysis.md](docs/llm-jtbd-analysis.md) | Каталог LLM-задач (JTBD) по стадиям пайплайна |
| [docs/rss-api-audit.md](docs/rss-api-audit.md) | Аудит доступности источников |
| [benchmark/README.md](benchmark/README.md) | LLM benchmark: метрики и инструкция |
| [prompts/news_analyst.md](prompts/news_analyst.md) | Системный промпт: классификация, скоринг, синтез, action items |
| [prompts/semantic_deduplicator.md](prompts/semantic_deduplicator.md) | Семантическая дедупликация — определяет, одно ли это событие |
| [prompts/trend_synthesizer.md](prompts/trend_synthesizer.md) | Синтез трендов из нескольких новостей за неделю/месяц |
| [prompts/contextualizer.md](prompts/contextualizer.md) | Исторический контекст — связывает новое событие с архивом дайджестов |
