# Russian Telegram Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every `telegram_digest` daily digest sent to Telegram is written in Russian only, with deterministic gates that reject English-only output before delivery.

**Architecture:** Keep source titles, company names, URLs, and short source names in their original language, but require all editorial prose for `telegram_digest` to be Russian. Add the language requirement at the prompt/contract layer, validate Stage C finish drafts before materialization, and add a last-mile Telegram pre-send language gate so an English digest cannot be delivered even if an upstream prompt regresses.

**Tech Stack:** Python stdlib validation helpers, existing Stage C materializer, Codex CLI prompt files, runtime contract YAML/Markdown, Telegram sender, offline fixture tests.

---

## Pipeline Audit

| Pipeline point | Current behavior | Required change |
| --- | --- | --- |
| `cowork/shared/mission_brief.md` | Says "write in Russian unless downstream artifact explicitly requires another language"; this is too general and was not enforced. | Keep as shared principle; add mode/profile-specific rules where the output is produced and delivered. |
| `cowork/modes/scrape_and_enrich.md` | Requires `analyst_summary`, `why_it_matters`, `avito_implication`, and `evidence_points`, but does not explicitly require Russian for downstream digest fields. | Require those compact editorial fields to be Russian for `telegram_digest` runs; allow names/titles/source quotes to remain original. |
| `config/runtime/mode-contracts/scrape_and_enrich_output.yaml` | Defines fields and body-status policy; no language contract. | Add `language_policy` for downstream editorial fields. |
| `cowork/modes/build_daily_digest.md` | Rendering constraints cover paths, run IDs, and Telegram formatting; no Russian-only requirement. | Require Russian headings, labels, story prose, selection notes visible in digest, and footer. |
| `config/runtime/mode-contracts/build_daily_digest_selection.yaml` | Selection contract has no language requirement. | Add render/output language policy for `telegram_digest`. |
| `ops/codex-cli/prompts/weekday_digest_finish.md` | Stage C finish draft contract requires `digest_markdown`, but not Russian. | Require Stage C to translate/summarize all digest prose into Russian before writing finish draft. |
| `tools/stage_c_finish.py` | Validates schema, URL matching, body statuses, QA, and forbidden runtime markers; does not validate language. | Add deterministic `telegram_digest` Russian gate for `digest_markdown`, `daily_brief.story_cards`, `selection_notes`, `enriched_items` editorial fields, and `qa_review.summary`. |
| `tools/telegram_send.py` | Converts markdown to Telegram HTML and sends it; no language gate. | Add pre-send Russian gate for `telegram_digest` and `telegram_weekly_digest`, with `--allow-non-russian` escape hatch for explicit operator override. |
| Tests/fixtures | Several Stage C fixtures use English prose and would allow English digest to pass. | Update tests to include Russian-positive fixture and English-negative fixture. |

## Language Boundary

Russian-only applies to human-facing editorial prose:

- digest headings and body labels;
- story summaries;
- `analyst_summary`;
- `why_it_matters`;
- `avito_implication`;
- digest-visible `evidence_points` / `evidence_notes`;
- `selection_notes`;
- QA summary when exposed in operator reports.

Russian-only does not require translating:

- source article titles inside links when the title itself is the source title;
- company/product/person names;
- source names such as `Inman`, `AIM Group`, `CoStar`;
- URLs;
- `source_id`, `run_id`, mode names, file paths in internal JSON manifests;
- short quoted source fragments when they are explicitly marked as source evidence.

## Deterministic Gate

Add a shared helper in `tools/russian_text_gate.py`.

Proposed behavior:

- strip URLs, Markdown links, inline code, HTML tags, numeric/date punctuation, and known proper nouns before scoring;
- count Cyrillic and Latin alphabetic characters in remaining prose;
- pass when `cyrillic_chars >= 80` and `cyrillic_chars / (cyrillic_chars + latin_chars) >= 0.55`;
- fail when visible digest prose contains common English-only section labels such as `Top Signals`, `Worth Tracking`, `Evidence note`, `Avito lens`, `Source:`, `Read Next`;
- return structured diagnostics: `status`, `cyrillic_chars`, `latin_chars`, `ratio`, `english_markers`, `field_path`.

This is intentionally a production guard, not a translation engine. Translation remains the Stage C Codex responsibility.

Implementation adjustment discovered during test run: the gate must also reject
common English editorial jargon inside otherwise Russian prose. Source titles,
company names, product names, and URLs remain allowed, but visible prose should
translate terms such as `agent tooling`, `lead quality`, `profit pools`,
`pre-market`, `source discovery`, `snippet fallback`, `paywall stubs`,
`unit economics`, `tech stack`, and `traffic monetization`.

## Acceptance Criteria

- `telegram_digest` finish drafts with English-only digest prose fail materialization.
- `telegram_digest` finish drafts with Russian digest prose pass materialization.
- `telegram_digest` finish drafts with Russian digest prose but English article titles/company names pass.
- `tools/telegram_send.py --profile telegram_digest` rejects English-only digest markdown before hitting the Telegram API.
- `tools/telegram_send.py --profile telegram_digest --dry-run` also runs the language gate.
- `--allow-non-russian` exists and is documented as an explicit operator override, not default behavior.
- Stage C finish prompt explicitly requires Russian digest output.
- `scrape_and_enrich` and `build_daily_digest` contracts explicitly require Russian editorial fields for Telegram digest profiles.
- Runtime validation and focused tests pass.

## Task 1: Add Shared Russian Language Gate

**Files:**
- Create: `tools/russian_text_gate.py`
- Create: `tools/test_russian_text_gate.py`

- [ ] **Step 1: Write the failing tests**

Create `tools/test_russian_text_gate.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import russian_text_gate


def test_russian_digest_passes_with_english_names_and_links() -> None:
    text = """# PropTech Monitor | 04.05.2026

## Главное

1. **[CoStar claims inventory shift](https://example.test/story)**
   - Сигнал: CoStar заявил о росте предложения OnTheMarket в Великобритании.
   - Почему важно: глубина инвентаря остается ключевым конкурентным рычагом порталов.
   - Для Avito: стоит отдельно отслеживать полноту базы, свежесть объявлений и работу с брокерами.

mode: build_daily_digest | 04.05.2026
"""
    result = russian_text_gate.check_russian_text(text, field_path="digest_markdown")
    assert result["status"] == "pass", result


def test_english_digest_fails_on_ratio_and_markers() -> None:
    text = """# PropTech Monitor | 04.05.2026

## Top Signals

Evidence note: this digest is non-canonical.

Avito lens: challenger pressure starts with inventory.

Source: AIM Group
"""
    result = russian_text_gate.check_russian_text(text, field_path="digest_markdown")
    assert result["status"] == "fail", result
    assert "Top Signals" in result["english_markers"]
    assert result["cyrillic_ratio"] < 0.55


def test_short_internal_strings_are_skipped() -> None:
    result = russian_text_gate.check_russian_text("mode: build_daily_digest | 04.05.2026", field_path="footer")
    assert result["status"] == "skip", result


def main() -> None:
    tests = [
        test_russian_digest_passes_with_english_names_and_links,
        test_english_digest_fails_on_ratio_and_markers,
        test_short_internal_strings_are_skipped,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python3 tools/test_russian_text_gate.py
```

Expected: fails with `ModuleNotFoundError: No module named 'russian_text_gate'`.

- [ ] **Step 3: Implement the helper**

Create `tools/russian_text_gate.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any


ENGLISH_MARKERS = [
    "Top Signals",
    "Worth Tracking",
    "Evidence note",
    "Avito lens",
    "Source:",
    "Read Next",
]

MIN_RELEVANT_CHARS = 80
MIN_CYRILLIC_RATIO = 0.55


def _strip_noise(text: str) -> str:
    cleaned = re.sub(r"https?://\\S+", " ", text or "")
    cleaned = re.sub(r"\\[[^\\]]+\\]\\([^)]*\\)", " ", cleaned)
    cleaned = re.sub(r"`[^`]*`", " ", cleaned)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"mode:\\s*[a-z_]+\\s*\\|\\s*\\d{2}\\.\\d{2}\\.\\d{4}", " ", cleaned, flags=re.I)
    return cleaned


def check_russian_text(text: str, *, field_path: str) -> dict[str, Any]:
    cleaned = _strip_noise(text)
    cyrillic_chars = len(re.findall(r"[А-Яа-яЁё]", cleaned))
    latin_chars = len(re.findall(r"[A-Za-z]", cleaned))
    relevant_chars = cyrillic_chars + latin_chars
    markers = [marker for marker in ENGLISH_MARKERS if marker.lower() in (text or "").lower()]
    ratio = cyrillic_chars / relevant_chars if relevant_chars else 0.0
    if relevant_chars < MIN_RELEVANT_CHARS and not markers:
        status = "skip"
    elif markers or ratio < MIN_CYRILLIC_RATIO:
        status = "fail"
    else:
        status = "pass"
    return {
        "status": status,
        "field_path": field_path,
        "cyrillic_chars": cyrillic_chars,
        "latin_chars": latin_chars,
        "cyrillic_ratio": ratio,
        "english_markers": markers,
    }


def require_russian_text(text: str, *, field_path: str) -> None:
    result = check_russian_text(text, field_path=field_path)
    if result["status"] == "fail":
        raise ValueError(
            "Russian language gate failed for "
            f"{field_path}: ratio={result['cyrillic_ratio']:.2f}, "
            f"markers={result['english_markers']}"
        )
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
python3 tools/test_russian_text_gate.py
```

Expected: `3 tests passed`.

- [ ] **Step 5: Commit**

Run:

```bash
git add tools/russian_text_gate.py tools/test_russian_text_gate.py
git -c user.name=Codex -c user.email=codex@local commit -m "Add Russian text gate"
```

## Task 2: Gate Stage C Finish Drafts

**Files:**
- Modify: `tools/stage_c_finish.py`
- Modify: `tools/test_stage_c_finish.py`

- [ ] **Step 1: Write failing tests**

Modify `tools/test_stage_c_finish.py`:

1. Change `finish_draft()` fixture prose to Russian:

```python
"analyst_summary": "ExampleCo расширила портал функцией, которая влияет на качество инвентаря.",
"why_it_matters": "Порталы конкурируют не только трафиком, но и рабочими инструментами для профессиональных продавцов.",
"avito_implication": "Avito стоит сравнить этот подход со своей дорожной картой инструментов для профессионалов.",
```

2. Change `digest_markdown` fixture to Russian:

```python
"digest_markdown": "# PropTech Monitor | 04.05.2026\n\n## Главное\n\n1. **[Full Article](https://example.test/full)**\n   - Сигнал: ExampleCo расширила портал функцией для качества инвентаря.\n   - Почему важно: порталы конкурируют рабочими инструментами для профессиональных продавцов.\n   - Для Avito: стоит сравнить подход со своей дорожной картой.\n   - Доказательство: статья описывает запуск функции для профессионального workflow.\n\nmode: build_daily_digest | 04.05.2026\n",
```

3. Add this negative test:

```python
def test_rejects_english_telegram_digest_markdown() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir)
        url = "https://example.test/full"
        shortlist_path = root / ".state/shortlists/2026-05-04/monitor_sources__20260504T120000Z__daily_core.json"
        article_result_path = root / ".state/codex-runs/20260504T121000Z-weekday_digest-article-prefetch-result.json"
        draft_path = root / ".state/codex-runs/20260504T121000Z-weekday_digest-finish-draft.json"
        draft = finish_draft(url)
        draft["digest_markdown"] = "# PropTech Monitor | 04.05.2026\n\n## Top Signals\n\nAvito lens: challenger pressure starts with inventory.\n"
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
            assert "Russian language gate failed" in str(exc)
        else:
            raise AssertionError("English telegram_digest markdown should be rejected")
```

Add the test to `main()`.

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python3 tools/test_stage_c_finish.py
```

Expected: negative English markdown test fails because no Russian gate exists yet.

- [ ] **Step 3: Implement Stage C gate**

Modify `tools/stage_c_finish.py`:

```python
import russian_text_gate
```

Add:

```python
RUSSIAN_DELIVERY_PROFILES = {"telegram_digest", "telegram_weekly_digest"}


def validate_russian_delivery_text(draft: dict, delivery_profile: str) -> None:
    if delivery_profile not in RUSSIAN_DELIVERY_PROFILES:
        return
    russian_text_gate.require_russian_text(str(draft.get("digest_markdown", "")), field_path="digest_markdown")
    for index, item in enumerate(draft.get("enriched_items", [])):
        for key in ("analyst_summary", "why_it_matters", "avito_implication"):
            russian_text_gate.require_russian_text(str(item.get(key, "")), field_path=f"enriched_items[{index}].{key}")
        for evidence_index, evidence in enumerate(item.get("evidence_points", [])):
            russian_text_gate.require_russian_text(str(evidence), field_path=f"enriched_items[{index}].evidence_points[{evidence_index}]")
    daily = draft.get("daily_brief", {})
    for index, note in enumerate(daily.get("selection_notes", [])):
        russian_text_gate.require_russian_text(str(note), field_path=f"daily_brief.selection_notes[{index}]")
    for index, card in enumerate(daily.get("story_cards", [])):
        for key in ("analyst_summary", "why_it_matters", "avito_implication"):
            russian_text_gate.require_russian_text(str(card.get(key, "")), field_path=f"daily_brief.story_cards[{index}].{key}")
        for evidence_index, evidence in enumerate(card.get("evidence_notes", [])):
            russian_text_gate.require_russian_text(str(evidence), field_path=f"daily_brief.story_cards[{index}].evidence_notes[{evidence_index}]")
```

Call it inside `validate_draft()` after `validate_digest_markdown(...)`:

```python
    validate_russian_delivery_text(draft, delivery_profile)
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
python3 tools/test_stage_c_finish.py
```

Expected: all Stage C tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add tools/stage_c_finish.py tools/test_stage_c_finish.py
git -c user.name=Codex -c user.email=codex@local commit -m "Require Russian Stage C digest drafts"
```

## Task 3: Add Telegram Pre-Send Russian Gate

**Files:**
- Modify: `tools/telegram_send.py`
- Modify: `tools/test_telegram_send.py`

- [ ] **Step 1: Write failing tests**

Modify `tools/test_telegram_send.py`:

Add import:

```python
from telegram_send import validate_delivery_language
```

Add tests:

```python
def test_telegram_digest_language_gate_rejects_english_body() -> None:
    try:
        validate_delivery_language(
            "# PropTech Monitor\n\n## Top Signals\n\nAvito lens: challenger pressure starts with inventory.",
            profile_name="telegram_digest",
            allow_non_russian=False,
        )
    except ValueError as exc:
        assert "Russian language gate failed" in str(exc)
    else:
        raise AssertionError("English telegram_digest body should be rejected")


def test_telegram_digest_language_gate_accepts_russian_body() -> None:
    validate_delivery_language(
        "# PropTech Monitor\n\n## Главное\n\nСигнал: CoStar заявил о росте предложения. Для Avito это повод сравнить глубину инвентаря.",
        profile_name="telegram_digest",
        allow_non_russian=False,
    )
```

Add both tests to the local test runner list.

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python3 tools/test_telegram_send.py
```

Expected: fails because `validate_delivery_language` does not exist.

- [ ] **Step 3: Implement pre-send gate**

Modify `tools/telegram_send.py`:

```python
import russian_text_gate
```

Add CLI arg:

```python
p.add_argument("--allow-non-russian", action="store_true", help="operator override for non-Russian digest bodies")
```

Add:

```python
RUSSIAN_DELIVERY_PROFILES = {"telegram_digest", "telegram_weekly_digest"}


def validate_delivery_language(body: str, *, profile_name: str, allow_non_russian: bool) -> None:
    if allow_non_russian or profile_name not in RUSSIAN_DELIVERY_PROFILES:
        return
    russian_text_gate.require_russian_text(body, field_path=f"{profile_name}.body")
```

In `main()`, after `body = sys.stdin.read()` and empty-body check, before HTML conversion:

```python
    validate_delivery_language(body, profile_name=args.profile, allow_non_russian=args.allow_non_russian)
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
python3 tools/test_telegram_send.py
```

Expected: all Telegram tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add tools/telegram_send.py tools/test_telegram_send.py
git -c user.name=Codex -c user.email=codex@local commit -m "Block non-Russian Telegram digests"
```

## Task 4: Update Runtime Prompts and Contracts

**Files:**
- Modify: `ops/codex-cli/prompts/weekday_digest_finish.md`
- Modify: `cowork/modes/scrape_and_enrich.md`
- Modify: `cowork/modes/build_daily_digest.md`
- Modify: `config/runtime/mode-contracts/scrape_and_enrich_output.yaml`
- Modify: `config/runtime/mode-contracts/build_daily_digest_selection.yaml`
- Modify: `tools/test_codex_cli_run_schedule.py`
- Modify: `tools/test_validate_runtime_artifacts.py`

- [ ] **Step 1: Add prompt/contract assertions**

Add to `tools/test_codex_cli_run_schedule.py` in the existing finish-prompt contract test:

```python
    assert "Russian" in prompt_text or "русск" in prompt_text.lower()
    assert "telegram_digest" in prompt_text
    assert "English-only" in prompt_text or "англ" in prompt_text.lower()
```

Add to `tools/test_validate_runtime_artifacts.py`:

```python
def test_russian_language_contracts_are_declared() -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    scrape = (root / "config/runtime/mode-contracts/scrape_and_enrich_output.yaml").read_text(encoding="utf-8")
    digest = (root / "config/runtime/mode-contracts/build_daily_digest_selection.yaml").read_text(encoding="utf-8")
    assert "language_policy" in scrape
    assert "telegram_digest" in scrape
    assert "Russian" in scrape or "русск" in scrape.lower()
    assert "language_policy" in digest
    assert "telegram_digest" in digest
    assert "Russian" in digest or "русск" in digest.lower()
```

Add the test to that file's test list.

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python3 tools/test_codex_cli_run_schedule.py
python3 tools/test_validate_runtime_artifacts.py
```

Expected: new assertions fail before docs/contracts are updated.

- [ ] **Step 3: Update Stage C finish prompt**

Add this section to `ops/codex-cli/prompts/weekday_digest_finish.md` before `## Required Finish Draft`:

```markdown
## Language Requirement

For `delivery_profile = telegram_digest`, all final human-facing digest prose
must be in Russian.

Translate or summarize English source material into Russian before writing:

- `enriched_items[].analyst_summary`
- `enriched_items[].why_it_matters`
- `enriched_items[].avito_implication`
- `enriched_items[].evidence_points`
- `daily_brief.selection_notes`
- `daily_brief.story_cards[].analyst_summary`
- `daily_brief.story_cards[].why_it_matters`
- `daily_brief.story_cards[].avito_implication`
- `daily_brief.story_cards[].evidence_notes`
- `digest_markdown`

Do not emit an English-only `telegram_digest`. Source titles, company names,
product names, URLs, and short source names may remain in their original
language, but headings, labels, summaries, implications, and evidence notes must
be Russian.
```

- [ ] **Step 4: Update mode prompts**

Add to `cowork/modes/scrape_and_enrich.md` after downstream-ready field rule:

```markdown
For `telegram_digest` and `telegram_weekly_digest` downstream profiles, emit
editorial prose fields in Russian: `analyst_summary`, `why_it_matters`,
`avito_implication`, and digest-visible `evidence_points`. Source titles,
company names, product names, and URLs may remain in the original language.
```

Add to `cowork/modes/build_daily_digest.md` under Delivery constraints:

```markdown
**Language:**
For `telegram_digest`, the digest body must be Russian-only editorial prose.
Translate or summarize English source evidence into Russian. Keep source names,
company names, product names, article titles in links, and URLs in their
original language when needed, but do not render English section headings,
labels, summaries, or Avito implications.
```

- [ ] **Step 5: Update YAML contracts**

Add to `config/runtime/mode-contracts/scrape_and_enrich_output.yaml`:

```yaml
language_policy:
  profiles:
    - telegram_digest
    - telegram_weekly_digest
  required_language: Russian
  applies_to_fields:
    - analyst_summary
    - why_it_matters
    - avito_implication
    - evidence_points
  allowed_original_language_fields:
    - title
    - companies
    - source_id
    - url
    - canonical_url
```

Add to `config/runtime/mode-contracts/build_daily_digest_selection.yaml`:

```yaml
language_policy:
  profiles:
    - telegram_digest
    - telegram_weekly_digest
  required_language: Russian
  applies_to_visible_digest_prose:
    - headings
    - labels
    - story_summaries
    - why_it_matters
    - avito_implication
    - evidence_notes
    - selection_notes
  allowed_original_language_fragments:
    - source article titles
    - company names
    - product names
    - source names
    - URLs
```

- [ ] **Step 6: Run tests to verify GREEN**

Run:

```bash
python3 tools/test_codex_cli_run_schedule.py
python3 tools/test_validate_runtime_artifacts.py
```

Expected: both pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add ops/codex-cli/prompts/weekday_digest_finish.md cowork/modes/scrape_and_enrich.md cowork/modes/build_daily_digest.md config/runtime/mode-contracts/scrape_and_enrich_output.yaml config/runtime/mode-contracts/build_daily_digest_selection.yaml tools/test_codex_cli_run_schedule.py tools/test_validate_runtime_artifacts.py
git -c user.name=Codex -c user.email=codex@local commit -m "Document Russian telegram digest contract"
```

## Task 5: Regenerate Russian Digest and Verify Telegram

**Files:**
- Modify after run: `digests/2026-05-04-daily-digest.md`
- Modify after run: `.state/` local artifacts only, not committed unless policy changes
- Optional tracked update: `docs/run-reviews/2026-05-04-weekday-digest.md`

- [ ] **Step 1: Run offline checks**

Run:

```bash
python3 tools/test_russian_text_gate.py
python3 tools/test_stage_c_finish.py
python3 tools/test_telegram_send.py
python3 tools/test_codex_cli_run_schedule.py
python3 tools/test_validate_runtime_artifacts.py
python3 tools/validate_runtime_artifacts.py --check all
PYTHONPYCACHEPREFIX=.pycache-local python3 -m py_compile tools/russian_text_gate.py tools/stage_c_finish.py tools/telegram_send.py
git diff --check
```

Expected: all commands exit `0`.

- [ ] **Step 2: Run production-like weekday digest rerun**

Run:

```bash
CODEX_ENV_FILE=/private/tmp/codex-empty-env ops/codex-cli/run_schedule.sh weekday_digest
```

If sandbox DNS/session access blocks the nested Codex run, rerun with the same command using the approved escalation path.

Expected:

- wrapper exits `0`;
- `Codex schedule run complete: <run_id>` appears;
- Stage C materializer does not reject language;
- generated `digests/2026-05-04-daily-digest.md` is Russian.

- [ ] **Step 3: Run language and safety gates on generated digest**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, "tools")
import russian_text_gate
text = Path("digests/2026-05-04-daily-digest.md").read_text(encoding="utf-8")
russian_text_gate.require_russian_text(text, field_path="digests/2026-05-04-daily-digest.md")
print("russian_digest_gate=pass")
PY
rg -n -- '\.state/|__[0-9]{8}T[0-9]{6}Z__|operator notes|run id|article_file' digests/2026-05-04-daily-digest.md
```

Expected:

- Python command prints `russian_digest_gate=pass`;
- `rg` returns exit `1` with no matches.

- [ ] **Step 4: Run Telegram dry-run**

Run:

```bash
python3 tools/telegram_send.py --profile telegram_digest --date 2026-05-04 --dry-run < digests/2026-05-04-daily-digest.md
```

Expected:

- exit `0`;
- JSON report has `dry_run: true`;
- `parts_sent >= 1`;
- `errors: []`.

- [ ] **Step 5: Live Telegram send only after explicit operator decision**

Run only after the user confirms live resend:

```bash
set -a
. ./.env
set +a
python3 tools/telegram_send.py --profile telegram_digest --date 2026-05-04 < digests/2026-05-04-daily-digest.md
```

Expected:

- exit `0`;
- JSON report has `delivery_status: delivered`;
- `errors: []`.

- [ ] **Step 6: Commit generated tracked Russian digest and review note**

Run:

```bash
git add digests/2026-05-04-daily-digest.md docs/run-reviews/2026-05-04-weekday-digest.md
git -c user.name=Codex -c user.email=codex@local commit -m "Regenerate Russian weekday digest"
```

## Completion Gate

Before reporting completion, run:

```bash
git status --short
python3 tools/test_russian_text_gate.py
python3 tools/test_stage_c_finish.py
python3 tools/test_telegram_send.py
python3 tools/test_codex_cli_run_schedule.py
python3 tools/test_validate_runtime_artifacts.py
python3 tools/validate_runtime_artifacts.py --check all
git diff --check
```

Completion can be claimed only if:

- all tests pass;
- latest generated digest passes Russian language gate;
- Telegram dry-run passes;
- live Telegram send is either explicitly completed or explicitly deferred by operator decision;
- no English-only digest is committed or sent.

## Self-Review

- Spec coverage: every pipeline point that can create, validate, or deliver Telegram digest prose is covered by at least one task.
- Complexity reduction: no translation service, no LLM post-processor, no new state schema enum; the plan uses prompt contracts plus deterministic language gates.
- Critical risk: the heuristic language gate can produce false positives for heavily named English entities, so it strips URLs/code and allows source titles/names. The last-mile Telegram gate intentionally blocks by default for digest profiles.
