# PropTech News Monitor — LLM Benchmark Suite

Набор тест-кейсов для оценки качества LLM по ключевым задачам агента.

**Статус:** Draft v1.0 — все датасеты требуют валидации экспертом домена перед production-использованием.

## Структура

```
benchmark/
├── README.md                           ← этот файл
└── datasets/
    ├── jtbd-07-classification/         ← Phase 1 (запускать первым)
    │   ├── inputs.jsonl                  30 случаев
    │   ├── golden.jsonl                  эталонные классификации
    │   └── metadata.json                 метрики, edge cases, пороги
    ├── jtbd-09-breaking-alert/         ← Phase 1
    │   ├── inputs.jsonl                  25 случаев
    │   ├── golden.jsonl                  is_breaking + rationale
    │   └── metadata.json
    ├── jtbd-08-scoring/                ← Phase 2
    │   ├── inputs.jsonl                  15 случаев (полный текст статей)
    │   ├── golden.jsonl                  5-мерные оценки + total_score
    │   └── metadata.json
    └── jtbd-06-deduplication/          ← Phase 2
        ├── inputs.jsonl                  15 пар (article_new + corpus)
        ├── golden.jsonl                  is_duplicate + duplicate_type
        └── metadata.json
```

## Быстрый старт

### Формат прогона

Для каждого JTBD: подать `inputs.jsonl` на вход модели → сравнить с `golden.jsonl` → посчитать метрики из `metadata.json`.

**Пример запуска JTBD-07:**
```python
for case in inputs:
    llm_output = classify_signal(case['title'], case['lead'])
    compare(llm_output['primary_type'], golden[case['id']]['primary_type'])
```

**Пример запуска JTBD-09:**
```python
for case in inputs:
    llm_output = assess_breaking(case['title'], case['lead'], case['base_score'])
    compare(llm_output['is_breaking'], golden[case['id']]['is_breaking'])
```

## Ключевые метрики по JTBD

| JTBD | Метод оценки | Главная метрика | Порог |
|------|-------------|----------------|-------|
| 07 — Классификация сигнала | Hard metrics | Macro-F1 | ≥ 0.75 |
| 09 — Breaking alert | Hard metrics | Precision | ≥ 0.85 |
| 08 — Скоринг релевантности | Correlation | Spearman ρ | ≥ 0.75 |
| 06 — Дедупликация | Hard metrics | F1 | ≥ 0.80 |

## Важные тест-кейсы (не пропускать при анализе)

- **jtbd07-006, jtbd07-018** — граничные случаи таксономии (иски, без чёткого класса)
- **jtbd09-001** — score ниже порога (82), но IS breaking (LLM должен переопределить score)
- **jtbd09-007** — score выше порога (86), но NOT breaking (ловушка на слепое следование score)
- **jtbd06-006** — семантический дубль с разными заголовками и источниками (must detect)
- **jtbd06-012** — Авито AI search vs international peers (НЕЛЬЗЯ подавлять как дубль)
- **jtbd08-013, jtbd08-015** — portability_to_avito=10, внутренние продукты Авито

## Источники данных

Все тест-кейсы основаны на реальных данных проекта:
- `.state/dedupe.json` — 30+ реальных статей с метаданными
- `digests/2026-W14-weekly-digest.md` — 6 статей с оценками приоритета
- `config/monitoring.yaml` — веса скоринга и критерии отбора

Синтетические кейсы (помечены в `metadata.json`) добавлены для покрытия граничных случаев.

## Следующие шаги

1. Валидация golden set двумя экспертами домена (PM + Strategy Avito)
2. Первый прогон на `claude-sonnet-4-6` как baseline
3. Расширение JTBD-07 до 50+ случаев для статистически значимых per-class метрик
4. Добавление Phase 2 датасетов: JTBD-11 (суммаризация), JTBD-12 (импликации)
