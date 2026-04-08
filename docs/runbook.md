# Runbook

> Legacy / compatibility reference.
>
> Этот файл сохранён как операторский reference для старого и переходного
> pipeline-path, но не является canonical описанием текущего runtime-дизайна.
>
> Current canonical docs:
>
> - [config/runtime/runtime_manifest.yaml](../config/runtime/runtime_manifest.yaml)
> - [docs/runtime-architecture.md](./runtime-architecture.md)
> - [docs/mode-catalog.md](./mode-catalog.md)
> - [docs/launch-rerun-dry-run.md](./launch-rerun-dry-run.md)
>
> Legacy команды и поля ниже должны читаться только как compatibility reference.

## Что уже готово

- Полный реестр источников: [monitor-list.json](../monitor-list.json)
- Legacy aggregate config: [config/monitoring.yaml](../config/monitoring.yaml)
- Шаблон переменных окружения: [.env.example](../.env.example)

## Как использовать

1. Заполнить переменные из [.env.example](../.env.example):
   - `OPENAI_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `TELEGRAM_MESSAGE_THREAD_ID`, если канал использует тему
2. Для legacy compatibility path использовать [config/monitoring.yaml](../config/monitoring.yaml) только как aggregate reference, а не как current canonical runtime layer.
3. Для ежедневной сводки запускать группу `daily_core`.
4. Для weekly digest запускать `daily_core` и `weekly_context`.
5. Для alert-режима проверять `daily_core` каждый час и отправлять сообщение, если `priority_score >= 85`.

## Ожидаемый pipeline

1. Прочитать `monitor-list.json`.
2. Подтянуть активные source groups из `config/monitoring.yaml`.
3. Скачать candidate items с `landing_urls`:
   - Сохранять `raw_snippet` (первые 600–800 символов оригинального текста) в enriched item.
   - Если `article_storage.enabled = true`: дополнительно скачать **полный текст** статьи и сохранить как markdown-файл (см. раздел «Хранение полных текстов» ниже).
4. Дедупликация — два уровня:
   - URL и title similarity (детерминированно)
   - Семантическая дедупликация через [prompts/semantic_deduplicator.md](../prompts/semantic_deduplicator.md) — определяет, одно ли это событие при разных заголовках и источниках; использует `raw_snippet` для сравнения
5. Классификация, скоринг и суммаризация через [prompts/news_analyst.md](../prompts/news_analyst.md). Выходные поля: `companies`, `regions`, `topic_tags`, `event_type`, `priority_score`, `confidence`, `analyst_summary`, `why_it_matters`, `avito_implication`, `story_id`.
   - Если `pipeline.stakeholder_personalization.enabled = true`: дополнительно вычислить `stakeholder_scores` для каждого профиля из `config/stakeholders.yaml`, применяя его `lens_weights`.
6. Контекстуализация через [prompts/contextualizer.md](../prompts/contextualizer.md) — для каждой отобранной новости проверяет архив (`delivery-log.json` + `digests/`) и при наличии добавляет строку `📎 Контекст:`.
7. Отобрать top items по правилам `selection` и `scoring`.
8. Синтез трендов через [prompts/trend_synthesizer.md](../prompts/trend_synthesizer.md) — **только для weekly digest**; требует истории минимум 2 недель в `digests/`.
9. Если `pipeline.stakeholder_personalization.enabled = true`: запустить персонализацию (см. раздел ниже).
10. Отправить итог через `delivery.telegram_profiles.*`.

## Ручной прогон и Cowork как legacy reference

Если pipeline запускается вручную или через Cowork в legacy/manual режиме, следовать тому же порядку шагов явно. Для current-state launch mappings использовать [docs/launch-rerun-dry-run.md](./launch-rerun-dry-run.md).

**Шаг 4 — семантическая дедупликация.** Для каждого candidate item, прошедшего URL-фильтр, подать в `semantic_deduplicator.md`:
```
candidate: { title, url, published, snippet }
corpus: содержимое .state/dedupe.json → поле "seen"
```
Отбросить items с `is_duplicate: true`. Обновить `dedupe.json` новыми записями.

**Шаг 6 — контекстуализация.** После отбора top items подать каждый в `contextualizer.md`:
```
candidate: { title, url, published, snippet, companies, topic }
archive: последние 30 дней из delivery-log.json + список файлов digests/
```
Если `has_context: true` — добавить `context_summary` в блок новости перед «Почему важно».

**Шаг 8 — синтез трендов (только weekly digest).** Подать в `trend_synthesizer.md`:
```
current_week_articles: все статьи текущего дайджеста
previous_weeks_articles: содержимое digests/ за последние 4 недели
```
Вставить результат отдельной секцией между главными новостями и «Что посмотреть».

> ⚠️ Если архив `digests/` содержит менее 2 недель истории — trend_synthesizer запускать с ожиданием усечённого результата (1 тренд вместо 3). При менее 1 недели — пропустить.

**Шаг 9 — персонализация (если включена).** Для каждого активного профиля из `config/stakeholders.yaml` подать в `prompts/digest_personalizer.md`:
```json
{
  "digest_date": "YYYY-MM-DD",
  "stakeholder_profile": { /* профиль из stakeholders.yaml */ },
  "items": [ /* enriched items с stakeholder_scores */ ]
}
```
Персонализатор применяет фильтрацию по `topic_filter` и `min_priority_score`, переранжирует по `lens_weights` профиля, адаптирует `detail_level` и генерирует кастомные секции. Результат — отдельный дайджест-файл для каждого профиля.

> ⚠️ Персонализация требует заполненных `stakeholder_scores` в enriched items (шаг 5). Без них персонализатор падает на `priority_score` как fallback, что может давать менее точную фильтрацию.

## Telegram

- Бот должен быть администратором канала.
- Для канала обычно используется `chat_id` вида `-100...`.
- Если сводка уходит в topic/thread, передавай `message_thread_id`.
- В конфиге уже включено разбиение длинных digest-сообщений на несколько частей.

## Legacy runner interface reference

В старом wrapper path раннеру было достаточно поддержать три аргумента:

- `--config <legacy aggregate config path>`
- `--schedule weekday_digest | weekly_digest | breaking_alert`
- `--dry-run`

Current-state canonical launch behavior задаётся через [config/runtime/schedule_bindings.yaml](../config/runtime/schedule_bindings.yaml) и [docs/launch-rerun-dry-run.md](./launch-rerun-dry-run.md), а не через этот legacy интерфейс как source-of-truth.

## Хранение полных текстов статей

Если `article_storage.enabled = true` в `monitoring.yaml`, каждая статья сохраняется как отдельный markdown-файл.

### Структура папок

```
.state/
  articles/
    YYYY-MM/                              ← один каталог на месяц
      YYYY-MM-DD_<slug>.md               ← один файл на статью
```

`slug` = первые 60 символов заголовка, строчные, пробелы → дефис, спецсимволы удалены.

Пример: `.state/articles/2026-04/2026-04-01_rightmove-sued-for-15-billion.md`

### Формат файла

```markdown
---
url: https://www.onlinemarketplaces.com/articles/rightmove-sued-for-1-5-billion/
title: "Rightmove Sued for £1.5 Billion"
published: 2026-04-01
source_id: onlinemarketplaces
fetch_strategy_used: html_scrape
fetched_at: 2026-04-07T10:00:00Z
fetch_failed: false
companies: [Rightmove]
topic_tags: [regulation, agent_relations, listing_war]
event_type: legal_filing
priority_score: 75
stakeholder_scores:
  product: 55
  strategy: 77
  commercial: 72
  tech: 59
story_id: story_rightmove_agent_lawsuit_2026
---

# Rightmove Sued for £1.5 Billion

Full article text here...
```

### Правила сохранения

- **`overwrite_existing: true`** — при повторном запуске перезаписывать существующий файл (свежий fetch).
- **`fallback_to_snippet: true`** — если fetch не удался (timeout, redirect loop): сохранить `raw_snippet` как тело файла, выставить `fetch_failed: true` в frontmatter.
- **`skip_if_paywall: true`** — если вернулось < `min_body_words` (150) слов: сохранить только frontmatter + однострочное сообщение `> ⚠️ Paywall or stub — full text not available.`
- **Поле `article_file`** в `dedupe.json` — относительный путь к файлу, добавляется после успешного сохранения.

### Ручной прогон (Cowork, legacy/manual reference)

При ручном запуске через Cowork:

1. Для каждой статьи из отобранных items сформировать путь: `.state/articles/YYYY-MM/YYYY-MM-DD_<slug>.md`
2. Скачать содержимое через WebFetch.
3. Очистить HTML → markdown: убрать nav/footer/ads, сохранить заголовки, параграфы, списки.
4. Сформировать YAML frontmatter из enriched-полей статьи.
5. Записать файл. Обновить поле `article_file` в `dedupe.json`.
6. Если WebFetch вернул ошибку или < 150 слов — применить fallback/paywall-правила выше.

## library.mikedp.com — скрапинг через Supabase API

library.mikedp.com — SPA без `<a>`-ссылок на статьи. Содержимое хранится в Supabase и доступно через публичный API.

### Почему не обычный WebFetch

- Sandbox Python не имеет прямого доступа к внешним URL (proxy 403).
- Страницы рендерятся JS-роутером — URL виден только после клика на карточку.
- Supabase возвращает `full_content` в виде HTML, полностью и без пейвола.

### Технические данные

```
Supabase endpoint : https://palshouozbpmjltbubcv.supabase.co
Таблица           : items
Anon key          : хранится в бандле https://library.mikedp.com/assets/index-DFA7Evy9.js
                    (ищем JWT: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.*.*)
Полезные поля     : slug, title, published_at, format, full_content (HTML), summary_200
```

Если URL бандла изменился — найти новый через `<script src="...">` на главной странице.

### Шаг 1 — Chrome JS: загрузить и подготовить статьи

Запустить в Chrome (вкладка с library.mikedp.com):

```javascript
fetch('https://library.mikedp.com/assets/index-DFA7Evy9.js')
  .then(r => r.text())
  .then(src => {
    var m = src.match(/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+/);
    window.__anonKey = m[0];
    return fetch(
      'https://palshouozbpmjltbubcv.supabase.co/rest/v1/items' +
      '?select=slug,title,published_at,format,full_content,summary_200' +
      '&order=published_at.desc&published_at=gte.2026-02-01T00:00:00Z&limit=100',
      { headers: { apikey: window.__anonKey, Authorization: 'Bearer ' + window.__anonKey } }
    );
  })
  .then(r => r.json())
  .then(data => {
    function stripHTML(html) {
      if (!html) return '';
      var d = document.createElement('div');
      d.innerHTML = html;
      d.querySelectorAll('script,style,img').forEach(n => n.remove());
      var nodes = d.querySelectorAll('h1,h2,h3,h4,h5,p,li,blockquote');
      var parts = [], seen = new Set();
      nodes.forEach(n => {
        var t = n.textContent.trim();
        if (t.length > 10 && !seen.has(t)) { seen.add(t); parts.push(t); }
      });
      return parts.length > 0 ? parts.join('\n\n') : d.textContent.trim();
    }
    window.__stripped = data.map(i => ({
      slug: i.slug,
      title: i.title,
      published_at: i.published_at,
      format: i.format,
      // подкасты: используем summary_200 (full_content = сырой транскрипт ~100K символов)
      text: (i.format === 'podcast') ? (i.summary_200 || '') : stripHTML(i.full_content),
    }));
    // Проверка: выводит slug|количество_слов для каждой статьи
    return window.__stripped.map(i => i.slug + '|' + i.text.split(/\s+/).length + 'w').join('\n');
  });
```

### Шаг 2 — Chrome JS: читать текст по одной статье

```javascript
// Список: индекс, slug, дата, формат
window.__stripped.map((i,n) => n+'|'+i.slug+'|'+i.published_at.slice(0,10)+'|'+i.format)

// Текст статьи (читать чанками по 2000 символов если > 4000)
window.__stripped[0].text
window.__stripped[0].text.substring(0, 2000)
window.__stripped[0].text.substring(2000, 4000)
```

> ⚠️ MCP блокирует большие JSON, base64 и hex. Передавать только plain text — по одной статье.

### Шаг 3 — Bash + Python: записать .md файл

```bash
# Скопировать текст из шага 2 в файл
cat > /tmp/art_SLUG.txt << 'EOF'
<текст статьи>
EOF

# Записать .md и обновить dedupe.json
python3 save_article.py <slug> <YYYY-MM-DD> <format>
# Пример:
python3 save_article.py "hemnet-trouble-in-arpa-paradise" "2026-02-16" "article"
```

Скрипт `save_article.py` (в корне проекта):
- читает `/tmp/art_<slug>.txt`
- записывает `.state/articles/YYYY-MM/YYYY-MM-DD_<slug>.md` с YAML frontmatter
- обновляет поле `article_file` в `dedupe.json`
- выводит `OK | NNNw | путь` или `FALLBACK` если < 100 слов

### Формат frontmatter для mikedp-статей

```yaml
---
url: https://library.mikedp.com/content/<slug>
source: library.mikedp.com
published: YYYY-MM-DD
format: article          # или podcast
content_source: supabase_full_content
---
```

---

## Схема .state-файлов

### `.state/dedupe.json`

Объект с двумя ключами:

- `_schema_notes` — документация всех полей (обновляется при изменении схемы).
- `seen` — карта `url → enriched item`. Текущая схема enriched item:

```json
{
  "title": "...",
  "title_hash": "6-char hash",
  "story_id": "story_<slug>_<yyyymm>",
  "first_seen": "ISO datetime",
  "published": "ISO date",
  "sent": true,
  "digest_date": "ISO date",
  "companies": ["Zillow"],
  "topic_tags": ["product_launch", "ai_search"],
  "raw_snippet": "первые 600-800 символов оригинала",
  "priority_score": 78,
  "stakeholder_scores": { "product": 85, "strategy": 60, "commercial": 40, "tech": 78 }
}
```

Поля `companies`, `topic_tags`, `raw_snippet`, `priority_score`, `stakeholder_scores` добавляются при активном LLM-слое. Существующие записи без этих полей — записи из dry-run периода.

### `.state/delivery-log.json`

Объект с двумя ключами:

- `_schema_notes` — документация всех полей.
- `runs` — массив run-записей. Текущая схема run:

```json
{
  "run_id": "ISO datetime",
  "schedule": "weekday_digest | weekly_digest | manual",
  "mode": "dry-run | live",
  "sources_used": ["source_id", ...],
  "items_found": 12,
  "items_in_digest": 5,
  "items_sent": 0,
  "telegram_message_id": null,
  "digest_file": "digests/YYYY-MM-DD-daily.md",
  "stakeholder_profile": "default",
  "articles": [
    {
      "title": "...",
      "url": "...",
      "published": "ISO date",
      "companies": ["..."],
      "topic_tags": ["..."],
      "priority_score": 72
    }
  ]
}
```

Поля `stakeholder_profile`, `companies`, `topic_tags`, `priority_score` в articles — добавляются при активном LLM-слое. Записи из dry-run периода содержат только `title`, `url`, `published`.

### Миграция существующих .state записей

При активации LLM-слоя существующие записи в `dedupe.json` можно обогатить ретроспективно, запустив enrichment-промпт на `raw_snippet` (если поле заполнено) или на `title`. Это необязательно — пайплайн продолжит работу без ретроспективного обогащения, но contextualizer и персонализатор будут работать с неполными данными для старых записей.

## Активация стейкхолдерских профилей

1. В `config/monitoring.yaml` выставить `pipeline.stakeholder_personalization.enabled: true`.
2. Убедиться, что шаг 5 пайплайна (скоринг) вычисляет `stakeholder_scores` для каждого профиля.
3. Опционально: для каждого профиля раскомментировать `delivery.thread_id_env` в `config/stakeholders.yaml` и прописать соответствующие переменные окружения (например, `TELEGRAM_THREAD_PRODUCT`).
4. Запустить dry-run — убедиться, что для каждого профиля генерируется отдельный дайджест-файл.
5. Переключить в live-режим.

## Практичный порядок внедрения

1. Сделать dry-run ingestion без Telegram.
2. Прогнать LLM benchmark для проверки качества классификации, скоринга и дедупликации — инструкция в [benchmark/README.md](../benchmark/README.md).
3. Проверить quality отбора на 3-5 последних выпусках из `digests/`.
4. Подключить Telegram delivery.
5. Повесить расписание или автоматизацию.
6. Активировать стейкхолдерские профили (см. выше) — после стабилизации базового пайплайна.
