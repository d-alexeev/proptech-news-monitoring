# PropTech News Monitor — LLM Benchmark Suite

Набор тест-кейсов для оценки качества LLM по ключевым задачам агента:
hard-metric JTBD checks, request-level retrieval, request-level synthesis, and
article-grounded request synthesis.

**Статус:** Draft v1.0 — все датасеты требуют валидации экспертом домена перед production-использованием.

## Структура

```
benchmark/
├── README.md                           ← этот файл
└── datasets/
    ├── jtbd-07-classification/         ← Phase 1 (запускать первым)
    │   ├── inputs.jsonl                  45 случаев
    │   ├── golden.jsonl                  эталонные классификации
    │   └── metadata.json                 метрики, edge cases, пороги
    ├── jtbd-09-breaking-alert/         ← Phase 1
    │   ├── inputs.jsonl                  25 случаев
    │   ├── golden.jsonl                  is_breaking + rationale
    │   └── metadata.json
    ├── request-article-retrieval/      ← Request retrieval, hard recall/precision
    │   ├── inputs.jsonl                  4 Avito Real Estate request cases
    │   ├── golden.jsonl                  relevant article ids + critical misses
    │   ├── metadata.json                 recall/precision, critical miss policy
    │   └── agent_qa_review_notes.json    agent QA; expert_review_pending
    ├── request-synthesis/              ← Request synthesis with LLM-as-Judge
    │   ├── inputs.jsonl                  1 ND synthesis case with full-text inputs
    │   ├── golden.jsonl                  expected theses, risks, Avito implications
    │   ├── output_schema.json            candidate output contract
    │   ├── judge_prompt_spec.json        judge prompt contract
    │   ├── judge_schema.json             judge output schema
    │   ├── judge_calibration.json        calibration examples
    │   └── agent_qa_review_notes.json    agent QA; expert_review_pending
    ├── request-article-synthesis/      ← Article-grounded synthesis with LLM-as-Judge
    │   ├── inputs.jsonl                  1 ND article-level synthesis case
    │   ├── golden.jsonl                  per-article expected review points
    │   ├── output_schema.json            candidate output contract
    │   ├── judge_prompt_spec.json        judge prompt contract
    │   ├── judge_schema.json             judge output schema
    │   ├── judge_calibration.json        calibration examples
    │   └── agent_qa_review_notes.json    QA review notes
    ├── jtbd-08-scoring/                ← Phase 2
    │   ├── inputs.jsonl                  16 случаев
    │   ├── golden.jsonl                  5-мерные оценки + total_score
    │   └── metadata.json
    ├── jtbd-06-deduplication/          ← Phase 2
    │   ├── inputs.jsonl                  15 пар (article_new + corpus)
    │   ├── golden.jsonl                  is_duplicate + duplicate_type
    │   └── metadata.json
    └── jtbd-15-contextualization/      ← Phase 2 starter set
        ├── inputs.jsonl                  3 случая (article_new + corpus)
        ├── golden.jsonl                  ranked context + context roles
        └── metadata.json                 метрики, роли контекста, пороги
```

## Dataset Families

| Family | Dataset folders | Evaluation style | Notes |
| --- | --- | --- | --- |
| Hard-metric JTBD | `jtbd-07-classification`, `jtbd-09-breaking-alert`, `jtbd-08-scoring`, `jtbd-06-deduplication` | Deterministic comparison against `golden.jsonl` and thresholds in `metadata.json` | Use for classification, alerting, scoring, and dedupe regressions. |
| Context JTBD | `jtbd-15-contextualization` | Retrieval metrics plus LLM-as-Judge review | Starter set for contextualization quality. |
| Request Retrieval | `request-article-retrieval` | Hard retrieval metrics | Scores returned `article_id` sets for request-specific recall, precision, and critical misses. |
| Request Synthesis | `request-synthesis` | Candidate schema validation plus LLM-as-Judge | Uses `output_schema.json`, `judge_prompt_spec.json`, `judge_schema.json`, and `judge_calibration.json`. |
| Request Article Synthesis | `request-article-synthesis` | Candidate schema validation plus LLM-as-Judge and QA notes | Uses `output_schema.json`, `judge_prompt_spec.json`, `judge_schema.json`, `judge_calibration.json`, and `agent_qa_review_notes.json`. |

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

### Request-Article Retrieval

Датасет: `benchmark/datasets/request-article-retrieval/`.

Это Phase 1 retrieval-only benchmark: модель получает реалистичный продуктовый
запрос Авито Недвижимости и фиксированный corpus article cards, затем должна
вернуть релевантные `article_id`. Синтез тезисов, digest generation и
production validation не входят в этот benchmark.

Текущий статус golden labels: `agent_qa_reviewed_expert_pending`. Перед
production-использованием нужен review эксперта домена.

### Request Synthesis

Датасет: `benchmark/datasets/request-synthesis/`.

Это request-level synthesis benchmark: модель получает запрос, отобранные статьи
и full-text evidence, затем возвращает структурированный JSON по
`output_schema.json`. Семантическая оценка выполняется через LLM-as-Judge:
`judge_prompt_spec.json` описывает контракт промпта, `judge_schema.json`
фиксирует формат judge output, а `judge_calibration.json` содержит калибровочные
примеры. Статус: `expert_review_pending`.

### Request Article Synthesis

Датасет: `benchmark/datasets/request-article-synthesis/`.

Это article-grounded synthesis benchmark: модель должна вернуть отдельную
request-specific оценку по каждой входной статье. Candidate output проверяется
по `output_schema.json`, затем оценивается LLM-as-Judge по
`judge_prompt_spec.json`, `judge_schema.json` и `judge_calibration.json`.
`agent_qa_review_notes.json` хранит компактные QA notes для traceability.
Статус: `agent_qa_reviewed_expert_pending`.

## Runner

```bash
python3 benchmark/scripts/run_request_benchmarks.py --help
```

Use this runner for request-level benchmark flows:
`request-article-retrieval`, `request-synthesis`, and
`request-article-synthesis`. It writes summary reports to `benchmark/results/`
and raw model responses to `benchmark/results/raw/`; both paths are ignored
runtime evidence, not committed benchmark data.

Common usage:

```bash
python3 benchmark/scripts/run_request_benchmarks.py --benchmark request-article-retrieval --model <model> --dry-run
python3 benchmark/scripts/run_request_benchmarks.py --benchmark request-synthesis --model <model>
python3 benchmark/scripts/run_request_benchmarks.py --benchmark request-article-synthesis --model <model>
```

LLM-as-Judge support applies to `request-synthesis` and
`request-article-synthesis`. First produce a candidate report, then pass it back
with `--judge-source-report`; `--judge-context-mode` supports `full_golden`,
`hybrid`, and `reduced_rubric`. Calibration can be exercised without a live
judge call:

```bash
python3 benchmark/scripts/run_request_benchmarks.py --benchmark request-synthesis --judge-calibration-dry-run
```

LLM judge datasets remain expert-review pending unless their dataset metadata
explicitly says otherwise.

## Ключевые метрики по JTBD

| Dataset | Метод оценки | Главная метрика | Порог / статус |
|------|-------------|----------------|-------|
| 07 — Классификация сигнала | Hard metrics | Macro-F1 | ≥ 0.75 |
| 09 — Breaking alert | Hard metrics | Precision | ≥ 0.85 |
| Request Article Retrieval | Hard retrieval metrics | Recall / Precision | ≥ 0.85 / ≥ 0.85 |
| Request Synthesis | LLM-as-Judge + schema validation | Judge score / critical issue count | expert calibrated; expert_review_pending |
| Request Article Synthesis | LLM-as-Judge + QA notes | Judge score / grounding failures | agent QA reviewed; expert_review_pending |
| 08 — Скоринг релевантности | Correlation | Spearman ρ | ≥ 0.75 |
| 06 — Дедупликация | Hard metrics | F1 | ≥ 0.80 |
| 15 — Контекстуализация | Retrieval + LLM-as-Judge | Precision@3 | ≥ 0.85 |

## Важные тест-кейсы (не пропускать при анализе)

- **jtbd07-006, jtbd07-018** — граничные случаи таксономии (иски, без чёткого класса)
- **jtbd09-001** — score ниже порога (82), но IS breaking (LLM должен переопределить score)
- **jtbd09-007** — score выше порога (86), но NOT breaking (ловушка на слепое следование score)
- **jtbd06-006** — семантический дубль с разными заголовками и источниками (must detect)
- **jtbd06-012** — Авито AI search vs international peers (НЕЛЬЗЯ подавлять как дубль)
- **jtbd08-013, jtbd08-015** — portability_to_avito=10, внутренние продукты Авито
- **jtbd15-002** — CoStar/Domain consolidation: важно восстановить цепочку и shareholder pressure context

## Источники данных

Все тест-кейсы основаны на реальных данных проекта:
- `.state/dedupe.json` и sharded state exports — реальные статьи с метаданными
- `digests/2026-W14-weekly-digest.md` — 6 статей с оценками приоритета
- `config/runtime/runtime_thresholds.yaml` — веса скоринга и критерии отбора

Синтетические кейсы (помечены в `metadata.json`) добавлены для покрытия граничных случаев.

## Следующие шаги

1. Валидация golden set двумя экспертами домена (PM + Strategy Avito)
2. Первый прогон на `claude-sonnet-4-6` как baseline
3. Расширение JTBD-07 до 50+ случаев для статистически значимых per-class метрик
4. Расширение JTBD-15 до 15–20 случаев
5. Добавление Phase 2 датасетов: JTBD-11 (суммаризация), JTBD-12 (импликации)
