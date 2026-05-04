# Telegram Digest Template and Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make weekday `telegram_digest` output stable, concise, Russian-only, visually richer, and one-message by default by using a fixed digest template plus a large Telegram link preview from the first top story.

**Architecture:** Stage B extracts compact `lead_image` metadata from shortlisted article pages. Stage C renders a fixed markdown template, orders top signals so the first rendered source has usable preview media when possible, and materializes only drafts that satisfy Russian, length, template, and preview contracts. Telegram delivery stays on `sendMessage`, not `sendPhoto`: the long digest remains a text message under the 4096-character Bot API text limit, while `link_preview_options` asks Telegram to show the first story preview image above the text.

**Tech Stack:** Python stdlib HTML parsing, `requests`, markdown mode prompts, YAML runtime contracts, `tools/stage_c_finish.py`, `tools/telegram_send.py`, plain Python tests, Telegram Bot API `sendMessage` with `link_preview_options`.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `tools/article_fetch.py` | Extract article text and `lead_image` metadata from shortlisted article pages. |
| `tools/test_article_fetch.py` | Offline tests for `og:image`, `twitter:image`, relative image URL resolution, and unavailable-image fallback. |
| `tools/shortlist_article_prefetch.py` | Persist `lead_image` into Stage B article prefetch result manifests and summary counts. |
| `tools/test_shortlist_article_prefetch.py` | Tests that prefetch manifests preserve image metadata without writing image binaries. |
| `tools/stage_c_finish.py` | Validate Russian prose, length budget, fixed digest template, selected preview URL, and materialize current-run artifacts. |
| `tools/test_stage_c_finish.py` | Tests for compact template acceptance, over-budget rejection, off-template rejection, and preview metadata validation. |
| `tools/telegram_send.py` | Send digest as text with optional large link preview; dry-run reports preview payload. |
| `tools/test_telegram_send.py` | Tests for link-preview payload, one-message dry-run, no duplicate title, and fallback when preview is absent. |
| `cowork/modes/build_daily_digest.md` | Runtime prompt contract for the fixed Russian daily Telegram template. |
| `ops/codex-cli/prompts/weekday_digest_finish.md` | Stage C wrapper prompt for compact template, `lead_image`, and preview selection. |
| `config/runtime/mode-contracts/build_daily_digest_rendering.yaml` | Machine-readable rendering, template, length, and preview policy. |
| `config/runtime/mode-contracts/build_daily_digest_selection.yaml` | Selection limits for 3 top signals and preview-aware ordering. |
| `config/runtime/mode-contracts/scrape_and_enrich_output.yaml` | Enrichment output contract for `lead_image` passthrough. |
| `config/runtime/state_schemas.yaml` | Schema notes for `lead_image` and `telegram_preview` fields. |
| `config/runtime/schedule_bindings.yaml` | `telegram_digest` delivery profile: no duplicate title, preview enabled, large preview above text. |
| `tools/test_validate_runtime_artifacts.py` | Contract tests asserting template and preview policy are declared. |
| `digests/2026-05-04-daily-digest.md` | Regenerated production-like test digest. |
| `PLANS.md` | Active plan index entry. |

## Decisions

| Topic | Decision |
| --- | --- |
| Telegram method | Use `sendMessage` with `link_preview_options`, not `sendPhoto`, because Bot API media captions are limited to 1024 chars while text messages support 4096 chars after entity parsing. |
| Visual source | Use the first rendered top story's article URL as `link_preview_options.url` when Stage B found a usable `lead_image` for that story. |
| Image extraction | Extract metadata only: `og:image`, `twitter:image`, `link rel=image_src`, then first large article image fallback. Do not download or store image binaries in this milestone. |
| Fallback | If no top story has usable image metadata, deliver the same digest without preview and record `telegram_preview.status = unavailable`. |
| Digest title | The digest body owns the visible title: `# PropTech Monitor Daily | D month YYYY`; `telegram_digest.title_template` becomes an empty string to avoid duplicate titles. |
| Digest body | Use exactly one main section, `## ТОП СИГНАЛЫ`, with up to 3 cards. Do not render separate watchlist, weak-signal, Avito takeaway, or evidence-quality sections. |
| Story card | Each card uses `### <emoji> <title>`, `Score: XX | <topic/category> | <short regions> | [Источник](url)`, `analyst_summary`, `**Что это значит:** why_it_matters`, and `**Для Avito:** avito_implication`. |
| Run status | End with one `Статус запуска:` line containing source count, article count, and scrape quality/validity. |
| Length | Target <= 3000 raw markdown chars; hard max <= 3400 raw markdown chars before Telegram HTML conversion. |
| Russian-only | All editorial prose remains Russian. `Score:` is allowed as the fixed metadata label requested by the user; company/product/source names and region abbreviations may remain original. |

## Milestones

| Milestone | Goal | Scope | Dependencies | Risks | Acceptance Criteria | Verification | Non-Goals |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TDP-M1 | Declare fixed template and preview contract | Prompts, YAML contracts, state schema notes, schedule profile | Existing Russian digest gate | Prompt can still drift without validators | Contracts declare fixed template, 3-card limit, status line, lead image, and large preview behavior | `python3 tools/test_validate_runtime_artifacts.py`; `python3 tools/validate_runtime_artifacts.py --check all` | No code enforcement yet |
| TDP-M2 | Extract lead image metadata in Stage B | `article_fetch`, `shortlist_article_prefetch`, tests | Existing article fetch result manifest | Some sources omit OG images or block image metadata | Prefetch result entries include `lead_image` with available/unavailable status; no image binaries are stored | `python3 tools/test_article_fetch.py`; `python3 tools/test_shortlist_article_prefetch.py` | No image download/upload, resizing, cache, or copyright filtering beyond metadata |
| TDP-M3 | Enforce compact template and preview metadata in Stage C | `stage_c_finish`, tests | TDP-M1, TDP-M2 | Structural validation can only check markers, not editorial quality | Overlong/off-template drafts fail; valid drafts with `telegram_preview` materialize; non-telegram profiles unaffected | `python3 tools/test_stage_c_finish.py` | No semantic validator for whether emoji/category is perfect |
| TDP-M4 | Send one text post with large preview | `telegram_send`, schedule profile, tests | TDP-M1 | Telegram may choose not to render preview for some URLs despite requested options | Dry-run reports `parts_sent: 1` and `link_preview_options` with `prefer_large_media` and `show_above_text`; no duplicate title | `python3 tools/test_telegram_send.py` | No MTProto/client-session publisher |
| TDP-M5 | Production-like rerun | Regenerate 2026-05-04 weekday digest | TDP-M1..TDP-M4 | Live source variability may change selected stories or preview availability | Digest passes Russian, length, template, runtime leak, and Telegram dry-run checks; preview status is explicit | `ops/codex-cli/run_schedule.sh weekday_digest`; post-run gates | No live Telegram send unless explicitly requested |

## Coverage Matrix

| Requirement | Milestone |
| --- | --- |
| Stable digest template from run to run | TDP-M1, TDP-M3, TDP-M5 |
| Header `PropTech Monitor Daily | DD месяц ГГГГ` | TDP-M1, TDP-M3, TDP-M5 |
| Section `ТОП СИГНАЛЫ` | TDP-M1, TDP-M3, TDP-M5 |
| Card fields: emoji title, Score, topic/category, region, source link, summary, meaning, Avito implication | TDP-M1, TDP-M3, TDP-M5 |
| Final run status with source count, article count, scrape validity/quality | TDP-M1, TDP-M3, TDP-M5 |
| Shorter one-message digest | TDP-M1, TDP-M3, TDP-M4, TDP-M5 |
| Russian-only editorial prose | TDP-M1, TDP-M3, TDP-M5 |
| Parse image from first/top story | TDP-M2, TDP-M3, TDP-M5 |
| Send long text and image-like visual in one Telegram post | TDP-M4, TDP-M5 |
| Avoid Bot API caption limit problem | TDP-M1, TDP-M4 |
| Fallback cleanly when image preview is unavailable | TDP-M2, TDP-M3, TDP-M4 |
| Keep Telegram sender robust for manual long input | TDP-M4 |
| Do not change live delivery without explicit request | TDP-M5 |

## Task 1: Contract Tests for Template and Preview Policy

**Files:**
- Modify: `tools/test_validate_runtime_artifacts.py`

- [ ] **Step 1: Extend the contract test**

Modify `test_russian_language_contracts_are_declared()` to read the rendering contract, selection contract, scrape contract, state schemas, and schedule bindings:

```python
def test_russian_language_contracts_are_declared() -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    scrape = (root / "config/runtime/mode-contracts/scrape_and_enrich_output.yaml").read_text(encoding="utf-8")
    digest = (root / "config/runtime/mode-contracts/build_daily_digest_selection.yaml").read_text(encoding="utf-8")
    rendering = (root / "config/runtime/mode-contracts/build_daily_digest_rendering.yaml").read_text(encoding="utf-8")
    schemas = (root / "config/runtime/state_schemas.yaml").read_text(encoding="utf-8")
    schedule = (root / "config/runtime/schedule_bindings.yaml").read_text(encoding="utf-8")
    assert "language_policy" in scrape
    assert "telegram_digest" in scrape
    assert "Russian" in scrape or "русск" in scrape.lower()
    assert "lead_image" in scrape
    assert "language_policy" in digest
    assert "telegram_digest" in digest
    assert "Russian" in digest or "русск" in digest.lower()
    assert "length_policy" in digest
    assert "max_top_story_count: 3" in digest
    assert "max_watchlist_count: 0" in digest
    assert "preview_policy" in digest
    assert "length_policy" in rendering
    assert "target_markdown_chars: 3000" in rendering
    assert "hard_max_markdown_chars: 3400" in rendering
    assert "telegram_parts_target: 1" in rendering
    assert "template_policy" in rendering
    assert "PropTech Monitor Daily" in rendering
    assert "ТОП СИГНАЛЫ" in rendering
    assert "Статус запуска" in rendering
    assert "preview_policy" in rendering
    assert "link_preview_options" in rendering
    assert "lead_image" in schemas
    assert "telegram_preview" in schemas
    assert "title_template: \"\"" in schedule
    assert "link_preview:" in schedule
    assert "prefer_large_media: true" in schedule
    assert "show_above_text: true" in schedule
```

- [ ] **Step 2: Run the contract test and verify it fails**

Run:

```bash
python3 tools/test_validate_runtime_artifacts.py
```

Expected: FAIL in `test_russian_language_contracts_are_declared` because template, preview, and image contracts are not declared yet.

## Task 2: Declare Template, Lead Image, and Preview Contracts

**Files:**
- Modify: `cowork/modes/build_daily_digest.md`
- Modify: `ops/codex-cli/prompts/weekday_digest_finish.md`
- Modify: `config/runtime/mode-contracts/build_daily_digest_rendering.yaml`
- Modify: `config/runtime/mode-contracts/build_daily_digest_selection.yaml`
- Modify: `config/runtime/mode-contracts/scrape_and_enrich_output.yaml`
- Modify: `config/runtime/state_schemas.yaml`
- Modify: `config/runtime/schedule_bindings.yaml`
- Modify: `tools/test_validate_runtime_artifacts.py`

- [ ] **Step 1: Add fixed template to `cowork/modes/build_daily_digest.md`**

Insert after the current `**Language:**` subsection:

````md
**Template for `telegram_digest`:**
Use this exact visible structure so daily runs are stable:

```md
# PropTech Monitor Daily | D month YYYY

## ТОП СИГНАЛЫ

### <emoji> <title>
Score: XX | <topic/category> | <short regions> | [Источник](url)

<analyst_summary>

**Что это значит:** <why_it_matters>

**Для Avito:** <avito_implication>

Статус запуска: источники X/Y | статьи A/B | качество: <validated/warnings>; <short scrape-quality note>
```

Rules:
- Use a Russian month name in the title, for example `4 мая 2026`.
- Render up to 3 signal cards.
- Pick one relevant emoji per card; do not use emoji elsewhere.
- `Score:` is the only allowed English fixed label in the visible digest.
- Use compact Russian topic/category labels and short region labels such as `US`, `UK`, `AU`, `EU`, `GCC`, `Global`.
- The `Источник` link points to the article/source URL for that card.
- End with exactly one `Статус запуска:` line.
- Do not add separate `Стоит отслеживать`, `Слабые сигналы`, `Вывод для Авито`, or `Качество доказательств` sections in the compact Telegram daily template.

**Length budget for `telegram_digest`:**
- Target raw markdown length: <= 3000 characters before Telegram HTML conversion.
- Hard maximum raw markdown length: <= 3400 characters.
- `## ТОП СИГНАЛЫ`: up to 3 story cards.
- Each story field must be one short paragraph, with no nested story bullets.

If evidence is mixed or partial, keep the evidence-quality disclosure but compress it
into the final `Статус запуска:` line. Do not include source counts in multiple sections.

**Preview policy for `telegram_digest`:**
Prefer ordering the first rendered top signal so it has `lead_image.status = available`.
The first story source URL is used as the Telegram large link preview URL.
If no top signal has usable image metadata, render and deliver the digest without preview.
````

- [ ] **Step 2: Add Stage C finish requirements**

Insert after the existing Language Requirement section in `ops/codex-cli/prompts/weekday_digest_finish.md`:

```md
## Template, Length, and Preview Requirement

For `delivery_profile = telegram_digest`, `digest_markdown` must follow the compact
daily template:

- title line: `# PropTech Monitor Daily | D month YYYY` with a Russian month name;
- main section: `## ТОП СИГНАЛЫ`;
- at most 3 story cards;
- each card includes `### <emoji> <title>`, `Score: XX | <topic/category> | <short regions> | [Источник](url)`, `**Что это значит:**`, and `**Для Avito:**`;
- final line starts with `Статус запуска:`;
- no nested story bullets;
- raw markdown target <= 3000 characters; hard maximum <= 3400 characters.

Each enriched item and story card must include `lead_image`. Use
`lead_image.status = available` only when article prefetch found image metadata
for that same URL. Add `telegram_preview` to the finish draft:

```json
{
  "status": "available",
  "preview_url": "https://article-url.example",
  "source_story_id": "story_id",
  "lead_image_url": "https://image-url.example",
  "reason": "first_top_signal_has_lead_image"
}
```

If no selected top signal has image metadata, use:

```json
{
  "status": "unavailable",
  "preview_url": null,
  "source_story_id": null,
  "lead_image_url": null,
  "reason": "no_selected_top_signal_with_lead_image"
}
```
```

- [ ] **Step 3: Add YAML rendering policy**

Add under `markdown_output_contract` in `config/runtime/mode-contracts/build_daily_digest_rendering.yaml`:

```yaml
  length_policy:
    profiles: [telegram_digest]
    target_markdown_chars: 3000
    hard_max_markdown_chars: 3400
    telegram_parts_target: 1
    max_top_story_count: 3
    max_watchlist_count: 0
    story_item_style: one_sentence_no_nested_bullets
  template_policy:
    profiles: [telegram_digest]
    title_format: "PropTech Monitor Daily | D month YYYY"
    title_month_language: Russian
    required_main_section: "ТОП СИГНАЛЫ"
    max_signal_cards: 3
    card_heading: "### <emoji> <title>"
    metadata_line: "Score: XX | <topic/category> | <short regions> | [Источник](url)"
    required_card_labels:
      - "Что это значит:"
      - "Для Avito:"
    final_status_prefix: "Статус запуска:"
    final_status_fields:
      - source_count
      - article_count
      - scrape_quality
    forbidden_compact_sections:
      - "Стоит отслеживать"
      - "Слабые сигналы"
      - "Вывод для Авито"
      - "Качество доказательств"
  preview_policy:
    profiles: [telegram_digest]
    telegram_method: sendMessage
    preview_transport: link_preview_options
    url_mode: first_top_signal_article_url_with_lead_image
    prefer_large_media: true
    show_above_text: true
    fallback: deliver_without_preview
```

- [ ] **Step 4: Add selection policy**

Add after `selection_stage_outputs` in `config/runtime/mode-contracts/build_daily_digest_selection.yaml`:

```yaml
length_policy:
  profiles: [telegram_digest]
  max_top_story_count: 3
  max_watchlist_count: 0
  weak_signals_default: omit
  selection_rule: select harder rather than rendering every useful signal
  evidence_disclosure_rule: keep one compact scrape-quality note in the final status line when coverage is mixed or partial
  rendered_sections:
    - ТОП СИГНАЛЫ

preview_policy:
  profiles: [telegram_digest]
  preferred_first_card: highest-ranked selected top story with lead_image.status = available
  fallback_first_card: highest-ranked selected top story
  preview_url_source: story_card.url
```

- [ ] **Step 5: Add `lead_image` to scrape/enrich contract**

In `config/runtime/mode-contracts/scrape_and_enrich_output.yaml`, add `lead_image` to the compact enriched item fields and document:

```yaml
  lead_image:
    description: compact image metadata from Stage B article prefetch, used only for Telegram link preview selection
    required_fields:
      - status
      - url
      - source
      - alt
    allowed_statuses:
      - available
      - unavailable
    storage_rule: store metadata only; do not store image binaries
```

- [ ] **Step 6: Add state schema notes**

In `config/runtime/state_schemas.yaml`, add schema notes for `lead_image` on enriched/story card artifacts and `telegram_preview` on finish/delivery artifacts:

```yaml
      lead_image:
        type: object
        required: false
        fields:
          status: enum[available,unavailable]
          url: string|null
          source: enum[og_image,twitter_image,image_src,article_image,none]
          alt: string|null
          content_type: string|null
          width: integer|null
          height: integer|null
      telegram_preview:
        type: object
        required: false
        fields:
          status: enum[available,unavailable]
          preview_url: string|null
          source_story_id: string|null
          lead_image_url: string|null
          reason: string
```

- [ ] **Step 7: Update `telegram_digest` schedule profile**

In `config/runtime/schedule_bindings.yaml`, change only `telegram_digest`:

```yaml
    disable_web_page_preview: false
    title_template: ""
    link_preview:
      enabled: true
      url_mode: first_markdown_link
      prefer_large_media: true
      show_above_text: true
      only_first_part: true
```

Do not change `telegram_weekly_digest` or `telegram_alert`.

- [ ] **Step 8: Run contract validation**

Run:

```bash
python3 tools/test_validate_runtime_artifacts.py
python3 tools/validate_runtime_artifacts.py --check all
```

Expected: both pass.

- [ ] **Step 9: Commit**

Run:

```bash
git add cowork/modes/build_daily_digest.md ops/codex-cli/prompts/weekday_digest_finish.md config/runtime/mode-contracts/build_daily_digest_rendering.yaml config/runtime/mode-contracts/build_daily_digest_selection.yaml config/runtime/mode-contracts/scrape_and_enrich_output.yaml config/runtime/state_schemas.yaml config/runtime/schedule_bindings.yaml tools/test_validate_runtime_artifacts.py
git commit -m "Define telegram digest template and preview contract"
```

## Task 3: Extract Lead Image Metadata

**Files:**
- Modify: `tools/test_article_fetch.py`
- Modify: `tools/article_fetch.py`
- Modify: `tools/test_shortlist_article_prefetch.py`
- Modify: `tools/shortlist_article_prefetch.py`

- [ ] **Step 1: Add failing article image extraction test**

In `tools/test_article_fetch.py`, update `ARTICLE_HTML` head to include:

```html
<meta property="og:image" content="/images/lead.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:image" content="https://cdn.example.test/twitter.jpg">
```

Add assertions to `test_fetch_source_extracts_article_like_text_and_full_hint()`:

```python
    assert result["lead_image"] == {
        "status": "available",
        "url": "https://example.test/images/lead.jpg",
        "source": "og_image",
        "alt": None,
        "content_type": None,
        "width": 1200,
        "height": 630,
    }
```

Add a fallback test:

```python
def test_fetch_source_marks_lead_image_unavailable_when_missing() -> None:
    html = "<article><p>Short but useful snippet.</p></article>"
    with fake_request(FakeResponse(text=html, url="https://example.test/no-image")):
        result = article_fetch.fetch_source(article_spec(url="https://example.test/no-image"), min_full_chars=120)

    assert result["lead_image"] == {
        "status": "unavailable",
        "url": None,
        "source": "none",
        "alt": None,
        "content_type": None,
        "width": None,
        "height": None,
    }
```

Add the test to the `tests` list.

- [ ] **Step 2: Run and verify red**

Run:

```bash
python3 tools/test_article_fetch.py
```

Expected: FAIL because `lead_image` is not extracted yet.

- [ ] **Step 3: Implement `lead_image` parser**

In `tools/article_fetch.py`, import URL resolver:

```python
from urllib.parse import urljoin
```

Add parser near `ArticleTextParser`:

```python
class LeadImageParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.candidates: list[dict[str, Any]] = []
        self._og_width: int | None = None
        self._og_height: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key.lower(): value for key, value in attrs if key and value}
        if tag.lower() == "meta":
            prop = (attr.get("property") or attr.get("name") or "").lower()
            content = attr.get("content")
            if prop == "og:image:width":
                self._og_width = _safe_int(content)
            elif prop == "og:image:height":
                self._og_height = _safe_int(content)
            elif prop == "og:image" and content:
                self.candidates.append({
                    "status": "available",
                    "url": urljoin(self.base_url, content),
                    "source": "og_image",
                    "alt": None,
                    "content_type": None,
                    "width": self._og_width,
                    "height": self._og_height,
                })
            elif prop == "twitter:image" and content:
                self.candidates.append({
                    "status": "available",
                    "url": urljoin(self.base_url, content),
                    "source": "twitter_image",
                    "alt": None,
                    "content_type": None,
                    "width": None,
                    "height": None,
                })
        elif tag.lower() == "link" and (attr.get("rel") or "").lower() == "image_src" and attr.get("href"):
            self.candidates.append({
                "status": "available",
                "url": urljoin(self.base_url, attr["href"]),
                "source": "image_src",
                "alt": None,
                "content_type": None,
                "width": None,
                "height": None,
            })
        elif tag.lower() == "img" and attr.get("src") and not self.candidates:
            self.candidates.append({
                "status": "available",
                "url": urljoin(self.base_url, attr["src"]),
                "source": "article_image",
                "alt": attr.get("alt"),
                "content_type": None,
                "width": _safe_int(attr.get("width")),
                "height": _safe_int(attr.get("height")),
            })

    def best(self) -> dict[str, Any]:
        return self.candidates[0] if self.candidates else unavailable_lead_image()
```

Add helpers:

```python
def _safe_int(value: str | None) -> int | None:
    try:
        return int(str(value)) if value is not None and str(value).strip() else None
    except ValueError:
        return None


def unavailable_lead_image() -> dict[str, Any]:
    return {
        "status": "unavailable",
        "url": None,
        "source": "none",
        "alt": None,
        "content_type": None,
        "width": None,
        "height": None,
    }


def _extract_lead_image(body: str, *, base_url: str) -> dict[str, Any]:
    parser = LeadImageParser(base_url)
    parser.feed(body or "")
    return parser.best()
```

In `_base_result()`, add:

```python
        "lead_image": unavailable_lead_image(),
```

In `fetch_source()` after response text is available, set:

```python
    result["lead_image"] = _extract_lead_image(response.text, base_url=response.url or spec.get("url") or "")
```

- [ ] **Step 4: Run article fetch tests**

Run:

```bash
python3 tools/test_article_fetch.py
```

Expected: PASS.

- [ ] **Step 5: Add failing prefetch manifest test**

In `tools/test_shortlist_article_prefetch.py`, ensure the fake fetch result contains:

```python
"lead_image": {
    "status": "available",
    "url": "https://example.test/images/lead.jpg",
    "source": "og_image",
    "alt": None,
    "content_type": None,
    "width": 1200,
    "height": 630,
},
```

Assert the manifest entry preserves it:

```python
    assert result_doc["results"][0]["lead_image"]["status"] == "available"
    assert result_doc["results"][0]["lead_image"]["url"] == "https://example.test/images/lead.jpg"
    assert result_doc["summary"]["lead_image_available_count"] == 1
```

- [ ] **Step 6: Run prefetch tests and verify red**

Run:

```bash
python3 tools/test_shortlist_article_prefetch.py
```

Expected: FAIL because manifest entries and summary do not preserve `lead_image`.

- [ ] **Step 7: Preserve image metadata in prefetch**

In `tools/shortlist_article_prefetch.py`, add to `_manifest_entry()`:

```python
        "lead_image": result.get("lead_image") or article_fetch.unavailable_lead_image(),
```

Add to `_summary()`:

```python
        "lead_image_available_count": sum(
            1 for result in results if (result.get("lead_image") or {}).get("status") == "available"
        ),
```

- [ ] **Step 8: Run image metadata tests**

Run:

```bash
python3 tools/test_article_fetch.py
python3 tools/test_shortlist_article_prefetch.py
```

Expected: both pass.

- [ ] **Step 9: Commit**

Run:

```bash
git add tools/article_fetch.py tools/test_article_fetch.py tools/shortlist_article_prefetch.py tools/test_shortlist_article_prefetch.py
git commit -m "Extract lead image metadata for shortlisted articles"
```

## Task 4: Stage C Template and Preview Gate

**Files:**
- Modify: `tools/test_stage_c_finish.py`
- Modify: `tools/stage_c_finish.py`

- [ ] **Step 1: Update positive finish fixture**

In `tools/test_stage_c_finish.py`, add `lead_image` to `article_prefetch_doc()` result:

```python
"lead_image": {
    "status": "available",
    "url": "https://example.test/images/lead.jpg",
    "source": "og_image",
    "alt": None,
    "content_type": None,
    "width": 1200,
    "height": 630,
},
```

Add the same `lead_image` object to the fixture `enriched_items[0]` and `daily_brief.story_cards[0]`.

Replace `digest_markdown` in `finish_draft()` with:

```python
"digest_markdown": "# PropTech Monitor Daily | 4 мая 2026\n\n## ТОП СИГНАЛЫ\n\n### 🏢 Full Article\nScore: 72 | portal_strategy/product_signal | US | [Источник](https://example.test/full)\n\nExampleCo расширила портал функцией для качества инвентаря.\n\n**Что это значит:** Порталы конкурируют рабочими инструментами для профессиональных продавцов.\n\n**Для Avito:** Стоит сравнить подход со своей дорожной картой инструментов для профессионалов.\n\nСтатус запуска: источники 1/1 | статьи 1/1 | качество: warnings; покрытие достаточно для тестового запуска.\n",
```

Add `telegram_preview` to the fixture:

```python
"telegram_preview": {
    "status": "available",
    "preview_url": url,
    "source_story_id": "story_example_full_20260504",
    "lead_image_url": "https://example.test/images/lead.jpg",
    "reason": "first_top_signal_has_lead_image",
},
```

- [ ] **Step 2: Add failing overlong and off-template tests**

Add tests:

```python
def test_rejects_overlong_telegram_digest_markdown() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        url = "https://example.test/full"
        shortlist_path = root / ".state/shortlists/2026-05-04/monitor_sources__20260504T120000Z__daily_core.json"
        article_result_path = root / ".state/codex-runs/20260504T121000Z-weekday_digest-article-prefetch-result.json"
        draft_path = root / ".state/codex-runs/20260504T121000Z-weekday_digest-finish-draft.json"
        draft = finish_draft(url)
        long_sentence = "Это русское предложение намеренно повторяется, чтобы превысить лимит длины Telegram-дайджеста. "
        draft["digest_markdown"] = "# PropTech Monitor Daily | 4 мая 2026\n\n## ТОП СИГНАЛЫ\n\n" + (long_sentence * 80)
        write_json(shortlist_path, [shortlist_item(url)])
        write_json(article_result_path, article_prefetch_doc(url))
        write_json(draft_path, draft)

        try:
            stage_c_finish.materialize_finish(
                repo_root=root,
                run_id="20260504T121000Z-weekday_digest",
                run_date="2026-05-04",
                source_group="daily_core",
                delivery_profile="telegram_digest",
                shortlist_path=shortlist_path,
                article_prefetch_result_path=article_result_path,
                draft_path=draft_path,
            )
        except ValueError as exc:
            assert "digest markdown exceeds telegram_digest hard max" in str(exc)
        else:
            raise AssertionError("overlong telegram_digest markdown should be rejected")
```

```python
def test_rejects_off_template_telegram_digest_markdown() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        url = "https://example.test/full"
        shortlist_path = root / ".state/shortlists/2026-05-04/monitor_sources__20260504T120000Z__daily_core.json"
        article_result_path = root / ".state/codex-runs/20260504T121000Z-weekday_digest-article-prefetch-result.json"
        draft_path = root / ".state/codex-runs/20260504T121000Z-weekday_digest-finish-draft.json"
        draft = finish_draft(url)
        draft["digest_markdown"] = "# Проптех-дайджест — 4 мая 2026\n\n## Главное\n\n1. Старый свободный формат без строки статуса.\n"
        write_json(shortlist_path, [shortlist_item(url)])
        write_json(article_result_path, article_prefetch_doc(url))
        write_json(draft_path, draft)

        try:
            stage_c_finish.materialize_finish(
                repo_root=root,
                run_id="20260504T121000Z-weekday_digest",
                run_date="2026-05-04",
                source_group="daily_core",
                delivery_profile="telegram_digest",
                shortlist_path=shortlist_path,
                article_prefetch_result_path=article_result_path,
                draft_path=draft_path,
            )
        except ValueError as exc:
            assert "digest markdown missing telegram_digest template marker" in str(exc)
        else:
            raise AssertionError("off-template telegram_digest markdown should be rejected")
```

Add both tests to the `tests` list.

- [ ] **Step 3: Add failing preview validation test**

Add:

```python
def test_rejects_preview_url_not_in_first_source_link() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        url = "https://example.test/full"
        shortlist_path = root / ".state/shortlists/2026-05-04/monitor_sources__20260504T120000Z__daily_core.json"
        article_result_path = root / ".state/codex-runs/20260504T121000Z-weekday_digest-article-prefetch-result.json"
        draft_path = root / ".state/codex-runs/20260504T121000Z-weekday_digest-finish-draft.json"
        draft = finish_draft(url)
        draft["telegram_preview"]["preview_url"] = "https://example.test/different"
        write_json(shortlist_path, [shortlist_item(url)])
        write_json(article_result_path, article_prefetch_doc(url))
        write_json(draft_path, draft)

        try:
            stage_c_finish.materialize_finish(
                repo_root=root,
                run_id="20260504T121000Z-weekday_digest",
                run_date="2026-05-04",
                source_group="daily_core",
                delivery_profile="telegram_digest",
                shortlist_path=shortlist_path,
                article_prefetch_result_path=article_result_path,
                draft_path=draft_path,
            )
        except ValueError as exc:
            assert "telegram_preview.preview_url must match a rendered source link" in str(exc)
        else:
            raise AssertionError("preview URL outside rendered source links should be rejected")
```

- [ ] **Step 4: Run Stage C tests and verify red**

Run:

```bash
python3 tools/test_stage_c_finish.py
```

Expected: FAIL because Stage C has no length/template/preview validation yet.

- [ ] **Step 5: Implement Stage C validation**

In `tools/stage_c_finish.py`, add constants:

```python
TELEGRAM_DIGEST_HARD_MAX_MARKDOWN_CHARS = 3400
LENGTH_LIMITED_DELIVERY_PROFILES = {"telegram_digest"}
TEMPLATE_VALIDATED_DELIVERY_PROFILES = {"telegram_digest"}
```

Add helpers:

```python
SOURCE_LINK_RE = re.compile(r"\[Источник\]\(([^)]+)\)")


def validate_digest_length(markdown: str, delivery_profile: str) -> None:
    if delivery_profile not in LENGTH_LIMITED_DELIVERY_PROFILES:
        return
    length = len(markdown)
    if length > TELEGRAM_DIGEST_HARD_MAX_MARKDOWN_CHARS:
        raise ValueError(
            "digest markdown exceeds telegram_digest hard max: "
            f"{length}>{TELEGRAM_DIGEST_HARD_MAX_MARKDOWN_CHARS}"
        )


def validate_digest_template(markdown: str, delivery_profile: str) -> None:
    if delivery_profile not in TEMPLATE_VALIDATED_DELIVERY_PROFILES:
        return
    required_markers = [
        "# PropTech Monitor Daily |",
        "## ТОП СИГНАЛЫ",
        "Score:",
        "| [Источник](",
        "**Что это значит:**",
        "**Для Avito:**",
        "Статус запуска:",
    ]
    for marker in required_markers:
        if marker not in markdown:
            raise ValueError(f"digest markdown missing telegram_digest template marker: {marker}")
    for marker in ("## Стоит отслеживать", "## Слабые сигналы", "## Вывод для Авито", "## Качество доказательств"):
        if marker in markdown:
            raise ValueError(f"digest markdown contains forbidden compact telegram section: {marker}")


def validate_telegram_preview(draft: dict, delivery_profile: str) -> None:
    if delivery_profile != "telegram_digest":
        return
    preview = draft.get("telegram_preview")
    if not isinstance(preview, dict):
        raise ValueError("finish draft telegram_preview must be an object")
    status = preview.get("status")
    if status not in {"available", "unavailable"}:
        raise ValueError("telegram_preview.status must be available or unavailable")
    if status == "available":
        preview_url = str(preview.get("preview_url") or "")
        if not preview_url:
            raise ValueError("telegram_preview.preview_url is required when preview is available")
        rendered_urls = SOURCE_LINK_RE.findall(str(draft.get("digest_markdown", "")))
        if preview_url not in rendered_urls:
            raise ValueError("telegram_preview.preview_url must match a rendered source link")
        if not preview.get("lead_image_url"):
            raise ValueError("telegram_preview.lead_image_url is required when preview is available")
    else:
        if preview.get("preview_url") is not None:
            raise ValueError("telegram_preview.preview_url must be null when preview is unavailable")
```

Call helpers in `validate_draft()` immediately after the existing `validate_digest_markdown(str(draft["digest_markdown"]))` line:

```python
    validate_digest_markdown(str(draft["digest_markdown"]))
    validate_digest_length(str(draft["digest_markdown"]), delivery_profile)
    validate_digest_template(str(draft["digest_markdown"]), delivery_profile)
    validate_telegram_preview(draft, delivery_profile)
    validate_russian_delivery_text(draft, delivery_profile)
```

Also add `telegram_preview` to required draft keys for `telegram_digest` by checking it inside `validate_telegram_preview`, not globally for weekly/other profiles.

- [ ] **Step 6: Preserve preview in materialized manifests**

In `build_digest_manifest()`, add under `operator_report`:

```python
            "telegram_preview": draft.get("telegram_preview", {"status": "unavailable"}),
```

In `build_daily_brief()`, add:

```python
        "telegram_preview": draft.get("telegram_preview", {"status": "unavailable"}),
```

- [ ] **Step 7: Run Stage C tests**

Run:

```bash
python3 tools/test_stage_c_finish.py
```

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```bash
git add tools/stage_c_finish.py tools/test_stage_c_finish.py
git commit -m "Validate compact telegram digest template and preview"
```

## Task 5: Telegram Sender Large Link Preview

**Files:**
- Modify: `tools/test_telegram_send.py`
- Modify: `tools/telegram_send.py`

- [ ] **Step 1: Add failing sender tests**

In `tools/test_telegram_send.py`, import `_load_profile` and `_build_link_preview_options` from `telegram_send`.

Add:

```python
def test_telegram_digest_profile_uses_body_title_and_large_preview() -> None:
    profile = _load_profile("telegram_digest")
    assert profile.get("title_template") == ""
    assert profile.get("disable_web_page_preview") is False
    assert profile.get("link_preview", {}).get("enabled") is True
    assert profile.get("link_preview", {}).get("prefer_large_media") is True
    assert profile.get("link_preview", {}).get("show_above_text") is True


def test_build_link_preview_options_from_first_markdown_source_link() -> None:
    body = (
        "# PropTech Monitor Daily | 4 мая 2026\n\n"
        "## ТОП СИГНАЛЫ\n\n"
        "### 🏢 Full Article\n"
        "Score: 72 | portal_strategy | US | [Источник](https://example.test/full)\n\n"
        "Русский текст дайджеста.\n"
    )
    profile = {
        "link_preview": {
            "enabled": True,
            "url_mode": "first_markdown_link",
            "prefer_large_media": True,
            "show_above_text": True,
        }
    }
    assert _build_link_preview_options(body, profile) == {
        "url": "https://example.test/full",
        "prefer_large_media": True,
        "show_above_text": True,
    }
```

Add both tests to the `tests` list.

- [ ] **Step 2: Run sender tests and verify red**

Run:

```bash
python3 tools/test_telegram_send.py
```

Expected: FAIL because preview helper/profile behavior is not implemented.

- [ ] **Step 3: Implement link preview extraction**

In `tools/telegram_send.py`, add:

```python
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^)\s]+)\)")


def _build_link_preview_options(raw_markdown: str, profile: dict) -> dict | None:
    cfg = profile.get("link_preview") or {}
    if not cfg.get("enabled"):
        return None
    if cfg.get("url_mode") != "first_markdown_link":
        return None
    match = _MARKDOWN_LINK_RE.search(raw_markdown)
    if not match:
        return None
    return {
        "url": match.group(1),
        "prefer_large_media": bool(cfg.get("prefer_large_media", True)),
        "show_above_text": bool(cfg.get("show_above_text", True)),
    }
```

Update `_send_chunk()` signature:

```python
def _send_chunk(
    bot_token: str,
    chat_id: str,
    text: str,
    *,
    thread_id: str | None,
    parse_mode: str | None,
    disable_preview: bool,
    link_preview_options: dict | None = None,
    timeout: int = 30,
) -> dict:
```

Inside payload creation:

```python
    if link_preview_options:
        payload["link_preview_options"] = link_preview_options
    else:
        payload["disable_web_page_preview"] = disable_preview
```

In `main()`, preserve raw markdown before HTML conversion:

```python
    raw_markdown_body = body
    link_preview_options = _build_link_preview_options(raw_markdown_body, profile)
```

For dry-run report, add:

```python
            "link_preview_options": link_preview_options,
```

When sending chunks, pass preview only to the first part:

```python
                link_preview_options=link_preview_options if idx == 0 else None,
```

- [ ] **Step 4: Run sender tests**

Run:

```bash
python3 tools/test_telegram_send.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add tools/telegram_send.py tools/test_telegram_send.py
git commit -m "Send telegram digest with large link preview"
```

## Task 6: Regenerate and Verify Weekday Digest

**Files:**
- Modify: `digests/2026-05-04-daily-digest.md`

- [ ] **Step 1: Run production-like weekday digest**

Run:

```bash
CODEX_ENV_FILE=/private/tmp/codex-empty-env ops/codex-cli/run_schedule.sh weekday_digest
```

Expected: command exits `0` and prints a line matching `Codex schedule run complete: 20260504T*Z-weekday_digest`.

If the command fails because Codex cannot access session files or network from the sandbox, rerun the same command with approved escalation. Do not change code to bypass that environment issue.

- [ ] **Step 2: Verify Russian gate**

Run:

```bash
python3 -c "from pathlib import Path; import sys; sys.path.insert(0, 'tools'); import russian_text_gate; text = Path('digests/2026-05-04-daily-digest.md').read_text(encoding='utf-8'); russian_text_gate.require_russian_text(text, field_path='digests/2026-05-04-daily-digest.md'); print('russian_digest_gate=pass')"
```

Expected:

```text
russian_digest_gate=pass
```

- [ ] **Step 3: Verify no runtime leakage**

Run:

```bash
rg -n -- '\.state/|__[0-9]{8}T[0-9]{6}Z__|operator notes|run id|article_file' digests/2026-05-04-daily-digest.md
```

Expected: exit code `1` and no matches.

- [ ] **Step 4: Verify length**

Run:

```bash
python3 -c "from pathlib import Path; text = Path('digests/2026-05-04-daily-digest.md').read_text(encoding='utf-8'); print(len(text)); raise SystemExit(0 if len(text) <= 3400 else 1)"
```

Expected: prints a number <= `3400` and exits `0`.

- [ ] **Step 5: Verify template markers**

Run:

```bash
python3 -c "from pathlib import Path; text = Path('digests/2026-05-04-daily-digest.md').read_text(encoding='utf-8'); markers = ['# PropTech Monitor Daily |', '## ТОП СИГНАЛЫ', 'Score:', '| [Источник](', '**Что это значит:**', '**Для Avito:**', 'Статус запуска:']; missing = [m for m in markers if m not in text]; print({'missing': missing}); raise SystemExit(1 if missing else 0)"
```

Expected:

```text
{'missing': []}
```

- [ ] **Step 6: Verify Telegram dry-run preview**

Run:

```bash
python3 tools/telegram_send.py --profile telegram_digest --date 2026-05-04 --dry-run < digests/2026-05-04-daily-digest.md
```

Expected: JSON has `dry_run: true`, `parts_sent: 1`, `errors: []`, and either a non-empty HTTPS `link_preview_options.url` with `prefer_large_media: true` and `show_above_text: true`, or `link_preview_options: null` when the materialized `telegram_preview.status` is `unavailable`.

When `link_preview_options` is `null`, inspect `.state/briefs/daily/2026-05-04__telegram_digest.json` and require `telegram_preview.status = unavailable` with a clear `reason`.

- [ ] **Step 7: Commit regenerated digest**

Run:

```bash
git add digests/2026-05-04-daily-digest.md
git commit -m "Regenerate compact preview-enabled weekday digest"
```

## Task 7: Final Verification and Report

**Files:**
- No planned file changes.

- [ ] **Step 1: Run full relevant checks**

Run:

```bash
python3 tools/test_article_fetch.py
python3 tools/test_shortlist_article_prefetch.py
python3 tools/test_russian_text_gate.py
python3 tools/test_stage_c_finish.py
python3 tools/test_telegram_send.py
python3 tools/test_codex_cli_run_schedule.py
python3 tools/test_validate_runtime_artifacts.py
python3 tools/validate_runtime_artifacts.py --check all
PYTHONPYCACHEPREFIX=.pycache-local python3 -m py_compile tools/article_fetch.py tools/shortlist_article_prefetch.py tools/russian_text_gate.py tools/stage_c_finish.py tools/telegram_send.py
git diff --check
git status --short
```

Expected:

- all tests pass;
- runtime validator prints `PASS all`;
- compile check has no output;
- `git diff --check` has no output;
- `git status --short` is empty.

- [ ] **Step 2: End-of-milestone report**

Report:

```md
Summary:
- Stable compact weekday Telegram digest template added.
- Stage B extracts lead image metadata for shortlisted articles.
- Stage C rejects over-budget or off-template `telegram_digest` markdown before materialization.
- Telegram digest delivery uses `sendMessage` with large link preview options when a preview URL is available.
- Regenerated weekday digest passes Russian, template, length, leak, and Telegram dry-run checks.

Validation:
- python3 tools/test_article_fetch.py
- python3 tools/test_shortlist_article_prefetch.py
- python3 tools/test_russian_text_gate.py
- python3 tools/test_stage_c_finish.py
- python3 tools/test_telegram_send.py
- python3 tools/test_codex_cli_run_schedule.py
- python3 tools/test_validate_runtime_artifacts.py
- python3 tools/validate_runtime_artifacts.py --check all
- Telegram dry-run parts_sent=1
- Preview payload status reported

Incomplete:
- Live Telegram delivery not sent unless explicitly requested.
- Preview rendering is ultimately controlled by Telegram; even with `prefer_large_media`, Telegram may suppress preview for a source URL.
```

## Self-Review

| Check | Result |
| --- | --- |
| Spec coverage | Covered: fixed template, compact length, Russian-only prose, final run status, image parsing, large one-post preview, fallback without preview, deterministic gates, and production-like rerun. |
| Completeness scan | No banned incomplete markers or vague validation steps remain. |
| Type consistency | Uses existing `delivery_profile`, `digest_markdown`, `validate_draft()`, article prefetch result manifests, and Telegram profile config patterns. |
| Scope control | Does not add MTProto publishing, image uploads, image binary cache, proxying, CAPTCHA bypass, paywall bypass, or live Telegram delivery. |
