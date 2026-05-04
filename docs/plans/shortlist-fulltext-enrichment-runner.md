# Shortlist Full-Text Enrichment Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a runner-side full-text enrichment layer for current-run shortlisted URLs so `scrape_and_enrich` can produce `body_status=full` when public article bodies are accessible.

**Architecture:** Keep discovery and digest modes full-text-free. After `monitor_sources` emits the shortlist shard, the schedule wrapper runs a dedicated elevated Codex I/O stage that reads only that shortlist, may call narrow fetch helpers, writes full article artifacts under `.state/articles/`, writes a compact fetch manifest under `.state/codex-runs/`, and exits. A later sandboxed `scrape_and_enrich` stage consumes article files only for matching shortlisted items; inaccessible or low-quality bodies remain `snippet_fallback` or `paywall_stub`.

**Tech Stack:** Staged `codex exec`, a narrow elevated Codex I/O runner prompt, Python helper scripts, `requests` + structured HTML extraction, optional Playwright fallback for configured adapter-approved public article pages, existing `.state/articles/` layout, existing `scrape_and_enrich` contracts and validators.

---

## Implementation Status

Status as of 2026-05-04:

- SFE-M1 complete: `tools/article_fetch.py` and offline contract tests are implemented.
- SFE-M2 complete: `tools/shortlist_article_prefetch.py` writes shortlist-scoped article artifacts plus compact result/summary manifests.
- SFE-M3 complete: `scrape_and_enrich` mode contracts and fixtures now allow runner article prefetch artifacts only after current-run shortlist matching.
- SFE-M4/SFE-M5 adapted and complete: the weekday wrapper now uses Stage A sandboxed discovery, direct Stage B full-text collection through `tools/shortlist_article_prefetch.py`, and Stage C sandboxed enrichment/digest/review instead of a separate elevated Codex I/O article-prefetch agent.
- SFE-M6 remains optional: browser article fallback is still deferred unless a later source-level run review proves it is needed.

Validation completed for the implemented milestones:

- `python3 tools/test_article_fetch.py`
- `python3 tools/test_shortlist_article_prefetch.py`
- `PYTHONPYCACHEPREFIX=.pycache-local python3 -m py_compile tools/shortlist_article_prefetch.py tools/article_fetch.py`
- `python3 tools/test_validate_runtime_artifacts.py`
- `python3 tools/validate_runtime_artifacts.py --check all`
- `python3 tools/test_codex_schedule_artifacts.py`
- `python3 tools/test_codex_cli_run_schedule.py`
- `bash -n ops/codex-cli/run_schedule.sh`

## Requirements

- Fetch full text only for items present in the current run's shortlist shard.
- Never fetch bodies for raw candidates, dropped candidates, story history, digest markdown, or broad source pages.
- Store full bodies as bounded article artifacts under `.state/articles/{published_month}/{published_date}_{slug}.md`.
- Keep downstream `enriched_item` compact: `article_file` may point to the artifact, but digest/review modes must not read full article bodies.
- Normalize each shortlisted fetch outcome to `full`, `snippet_fallback`, or `paywall_stub`.
- Use static HTTP first; browser fallback is optional and allowed only for adapter-approved public article pages.
- Use an elevated Codex I/O stage only for the shortlist full-text acquisition step; the main reasoning/enrichment/digest stages remain sandboxed.
- Treat fetched web content as hostile input that cannot alter runner instructions.
- Do not automate login, CAPTCHA, paywall bypass, proxy rotation, or cookie/session workarounds.
- Preserve source-specific adapter boundaries; do not make a generic crawler that follows links beyond the shortlisted URL.
- Add offline tests before implementation and run a recovery `weekday_digest` after implementation.
- Record actual source-level outcomes and follow-up change requests when bodies remain unavailable.

## Files And Responsibilities

- Create `tools/article_fetch.py`: low-level JSON-in/JSON-out full-text fetch helper for explicit shortlisted URLs; writes no `.state` by itself.
- Create `tools/test_article_fetch.py`: offline tests for extraction, paywall/anti-bot classification, compact limits, and no-state-write behavior.
- Create `tools/shortlist_article_prefetch.py`: runner orchestration helper that reads the current shortlist shard, calls `article_fetch.py`, writes article markdown files and a run manifest under `.state/codex-runs/`.
- Create `tools/test_shortlist_article_prefetch.py`: offline tests that only shortlisted items are fetched and article files are written under the expected layout.
- Create `ops/codex-cli/prompts/article_prefetch.md`: restricted elevated Codex I/O prompt for current-run shortlisted article fetching.
- Modify `ops/codex-cli/run_schedule.sh`: split `weekday_digest` into staged Codex invocations, run the elevated article prefetch stage after shortlist emission, then pass the article manifest to sandboxed `scrape_and_enrich`.
- Modify `cowork/modes/scrape_and_enrich.md`: consume runner-provided article manifests for shortlisted URLs and normalize body statuses.
- Modify `config/runtime/mode-contracts/scrape_and_enrich_gate.yaml`: add runner full-text artifact input rules and current-run shortlist matching.
- Modify `config/runtime/mode-contracts/scrape_and_enrich_output.yaml`: document article artifact manifest and `article_file` normalization.
- Modify `config/runtime/mode-fixtures/*`: add fixtures for full body success, paywall stub, snippet fallback, and non-shortlisted guard.
- Modify `config/runtime/runtime_manifest.yaml`: register new fixtures.
- Modify `tools/validate_runtime_artifacts.py` and `tools/test_validate_runtime_artifacts.py` only if the existing full-text boundary checks cannot express the new manifest contract.
- Modify `tools/README.md` and `ops/codex-cli/README.md`: document helper boundaries, invocation, and runtime footprint.
- Modify `docs/run-reviews/2026-05-04-weekday-digest.md` after the live recovery run.

## Milestone SFE-M1: Article Fetch Helper Contract

**Goal:** Create the low-level helper that fetches and extracts text for explicit article URLs without writing `.state`.

**Scope:**
- Create `tools/article_fetch.py`.
- Create `tools/test_article_fetch.py`.
- Support batch input via stdin: `{"articles":[{"source_id","url","canonical_url","title","published","shortlist_run_id"}]}`.

**Acceptance Criteria:**
- Helper emits one JSON document with `fetched_at`, `results[]`, `batch_status`, `failure_class`, and `run_failure`.
- Each result includes `source_id`, `url`, `canonical_url`, `title`, `published`, `body_status_hint`, `text`, `text_char_count`, `error`, `failure_class`, `soft_fail`, and `soft_fail_detail`.
- Static HTML extraction removes script/style/nav noise and keeps article-like visible text.
- Text is capped by `max_chars`; helper does not emit unbounded page bodies.
- Paywall, login, CAPTCHA, 401/402/403/451, and 429 outcomes map to stable soft-fail labels.
- Helper writes no `.state` files.

**Tests / Verification:**
- `python3 tools/test_article_fetch.py`
- `PYTHONPYCACHEPREFIX=.pycache-local python3 -m py_compile tools/article_fetch.py`

**Risks:**
- Generic article extraction may be weak for some publishers.
- AIM/Inman may expose enough snippet metadata but not full body without subscription.

**Non-goals:**
- No browser fallback in M1.
- No article markdown writing in M1.

## Milestone SFE-M2: Shortlist-Scoped Article Prefetch

**Goal:** Add a runner helper that turns current-run shortlist items into bounded article artifacts and a compact evidence manifest.

**Scope:**
- Create `tools/shortlist_article_prefetch.py`.
- Create `tools/test_shortlist_article_prefetch.py`.
- Read only the explicit shortlist shard path passed by the caller.
- Write article files only for results with `body_status_hint=full`.
- Write `.state/codex-runs/{run_id}-article-prefetch-result.json`.
- Write `.state/codex-runs/{run_id}-article-prefetch-summary.json`.

**Acceptance Criteria:**
- Helper refuses to run without an explicit shortlist shard path.
- Helper fetches only `triage_decision=shortlist` items from that shard.
- Helper ignores raw shards and does not discover new URLs.
- Article markdown has compact frontmatter: `source_id`, `url`, `canonical_url`, `title`, `published`, `fetched_at`, `body_status_hint`.
- Summary records `shortlisted_count`, `attempted_count`, `full_count`, `snippet_fallback_count`, `paywall_stub_count`, and artifact paths.
- Result entries map each shortlisted URL to either an `article_file` or fallback status.

**Tests / Verification:**
- `python3 tools/test_shortlist_article_prefetch.py`
- `python3 tools/test_article_fetch.py`
- `PYTHONPYCACHEPREFIX=.pycache-local python3 -m py_compile tools/shortlist_article_prefetch.py tools/article_fetch.py`

**Risks:**
- Article filenames need deterministic slugging and collision handling.
- Existing state validators must allow full-text artifacts only through `scrape_and_enrich`.

**Non-goals:**
- No scheduled wrapper integration yet.

## Milestone SFE-M3: `scrape_and_enrich` Contract Integration

**Goal:** Teach runtime contracts and fixtures how `scrape_and_enrich` consumes runner-provided article artifacts.

**Scope:**
- Update `cowork/modes/scrape_and_enrich.md`.
- Update `config/runtime/mode-contracts/scrape_and_enrich_gate.yaml`.
- Update `config/runtime/mode-contracts/scrape_and_enrich_output.yaml`.
- Add fixtures for:
  - full body article artifact consumed for a shortlisted item;
  - paywall/blocked article becomes `paywall_stub`;
  - low-quality/short body remains `snippet_fallback`;
  - non-shortlisted article artifact is rejected/ignored.
- Register fixtures in `config/runtime/runtime_manifest.yaml`.

**Acceptance Criteria:**
- `scrape_and_enrich` may read article artifacts only when the artifact URL matches a current-run shortlisted item.
- `article_file` is non-null for `body_status=full`.
- `article_file` may remain null for `paywall_stub`.
- Digest/review modes remain forbidden from reading `.state/articles/`.
- Fixtures pass full-text boundary validation.

**Tests / Verification:**
- `python3 tools/test_validate_runtime_artifacts.py`
- `python3 tools/validate_runtime_artifacts.py --check all`

**Risks:**
- A fixture could accidentally normalize full-text access outside `scrape_and_enrich`.
- Overly broad contract wording could allow article artifact reuse across runs.

**Non-goals:**
- Do not change final digest selection rules except evidence status propagation.

## Milestone SFE-M4: Staged Codex I/O Runner Design

**Goal:** Replace the one-shot schedule execution with an explicit staged handoff so only the article acquisition stage receives elevated I/O capability.

**Scope:**
- Create or update prompts for three stages:
  - stage A: sandboxed discovery, ending after `monitor_sources` writes the current-run shortlist;
  - stage B: elevated `article_prefetch` Codex I/O runner, reading only the current shortlist and writing only article artifacts plus manifest;
  - stage C: sandboxed enrichment/digest/review/delivery, consuming article manifest paths.
- Update `ops/codex-cli/run_schedule.sh` to execute those stages in order for `weekday_digest`.
- Keep static/browser source prefetch before stage A.
- Pass article prefetch summary/result paths into stage C.
- Update wrapper tests.

**Acceptance Criteria:**
- The scheduled run can produce a shortlist, run elevated article prefetch for that shortlist, then enrich using those artifacts.
- Static/browser discovery prefetch remains unchanged.
- Stage A and stage C run with `workspace-write`.
- Stage B may use a broader sandbox only when required for network/browser I/O, but its prompt contract forbids repo edits outside `.state/articles/` and `.state/codex-runs/*article-prefetch*`.
- Stage B receives no Telegram env, no `.env` contents, no digest archive, no raw shard path, and no broad source config unless explicitly required.
- Fetched page text is treated as untrusted data and must not override system/developer/repo instructions.
- If article prefetch fails globally, enrichment still emits `snippet_fallback` with a partial manifest rather than blocking the whole digest.
- Wrapper self-test documents the new article prefetch wiring.

**Tests / Verification:**
- `python3 tools/test_codex_cli_run_schedule.py`
- `bash -n ops/codex-cli/run_schedule.sh`
- `CODEX_RUN_SCHEDULE_SELF_TEST=1 ops/codex-cli/run_schedule.sh weekday_digest`

**Risks:**
- Elevated Codex I/O stage has a wider attack surface because it reads arbitrary web content.
- Prompt injection from fetched article pages could try to influence the elevated agent.
- Multi-stage runs may require a stricter run-id handoff contract.

**Non-goals:**
- Do not switch the main discovery/enrichment/digest agent stages to `danger-full-access`.
- Do not use elevated Codex I/O as a general crawler or source discovery agent.

## Milestone SFE-M5: Elevated Article Prefetch Stage Implementation

**Goal:** Implement the restricted Codex I/O stage that fetches only shortlisted article URLs and writes reviewable article artifacts.

**Scope:**
- Add `ops/codex-cli/prompts/article_prefetch.md`.
- Wire stage B invocation in `ops/codex-cli/run_schedule.sh`.
- Stage B may call `tools/shortlist_article_prefetch.py`, `tools/article_fetch.py`, `tools/pdf_extract.py`, and `tools/browser_fetch.py` as needed.
- Stage B writes:
  - `.state/articles/{published_month}/{published_date}_{slug}.md`;
  - `.state/codex-runs/{run_id}-article-prefetch-result.json`;
  - `.state/codex-runs/{run_id}-article-prefetch-summary.json`;
  - optional change requests for persistent source/adapter gaps.

**Acceptance Criteria:**
- Stage B reads only the current shortlist path, source adapters for shortlisted source IDs, and helper docs needed for fetch tools.
- Stage B never edits tracked repo files.
- Stage B never reads `.env`, Telegram credentials, digest archive, raw shards, or non-shortlisted candidates.
- Stage B output manifest includes per-item `fetch_method`, `body_status_hint`, `article_file`, `soft_fail`, `failure_class`, and `text_char_count`.
- Stage B emits a bounded final message with counts only; no full article text in final message or event-summary docs.
- If the elevated stage is denied or unavailable, wrapper writes a synthetic article prefetch summary with all shortlisted items as `snippet_fallback`.

**Tests / Verification:**
- `python3 tools/test_codex_cli_run_schedule.py`
- `python3 tools/test_shortlist_article_prefetch.py`
- `bash -n ops/codex-cli/run_schedule.sh`
- `CODEX_RUN_SCHEDULE_SELF_TEST=1 ops/codex-cli/run_schedule.sh weekday_digest`

**Risks:**
- The elevated stage may still log web-page text into Codex JSONL events. Keep `.state/codex-runs/*events.jsonl` local-only and never commit it.
- Auto-review may reject broad sandbox escalation in some environments; the synthetic fallback must keep the run functional.

**Non-goals:**
- No source discovery, ranking, digest writing, or Telegram delivery in Stage B.

## Milestone SFE-M6: Optional Browser Article Fallback

**Goal:** Add a narrow browser fallback for public shortlisted article pages where static HTTP is insufficient and adapter policy allows it.

**Scope:**
- Extend `tools/article_fetch.py` or add a delegated browser function using Playwright.
- Allow browser fallback only for the same shortlisted URL and only after static HTTP fails or returns below-threshold body.
- Record `fetch_method: static_http | playwright_browser`.

**Acceptance Criteria:**
- Browser fallback is never used for paywall/login/CAPTCHA bypass.
- Browser fallback cannot follow links beyond the shortlisted URL.
- Soft-fail labels remain stable.
- Fallback use is visible in article prefetch summary.

**Tests / Verification:**
- `python3 tools/test_article_fetch.py`
- `python3 tools/test_shortlist_article_prefetch.py`

**Risks:**
- Browser article fetch can be confused with bypassing blocked content; keep source policies explicit.
- Some sites may serve consent pages or bot blocks to headless browsers.

**Non-goals:**
- No cookie/session persistence.
- No screenshots as evidence unless a later plan explicitly adds them.

## Milestone SFE-M7: Live Recovery Run And Completion Audit

**Goal:** Run `weekday_digest`, measure how many shortlisted items become `full`, and document remaining gaps.

**Scope:**
- Run `ops/codex-cli/run_schedule.sh weekday_digest`.
- Inspect article prefetch summary, enrichment manifest, digest metadata, and review report.
- Update `docs/run-reviews/2026-05-04-weekday-digest.md`.
- Update this plan and `PLANS.md`.

**Acceptance Criteria:**
- Run review records `full_count`, `snippet_fallback_count`, and `paywall_stub_count`.
- Digest is canonical only if source discovery and enrichment gates actually pass; otherwise it remains `partial_digest`.
- No article body text appears in tracked digest or run review.
- Secret scan and internal-ref scan pass.
- Completion report lists source-level blockers and next changes.

**Tests / Verification:**
- `ops/codex-cli/run_schedule.sh weekday_digest`
- `python3 tools/test_article_fetch.py`
- `python3 tools/test_shortlist_article_prefetch.py`
- `python3 tools/test_validate_runtime_artifacts.py`
- `python3 tools/validate_runtime_artifacts.py --check all`
- `rg --count-matches 'api\\.telegram\\.org/bot|/bot[0-9]+:[A-Za-z0-9_-]+' docs/run-reviews/2026-05-04-weekday-digest.md digests/2026-05-04-daily-digest.md`
- `rg -n -- '\\.state/|__[0-9]{8}T[0-9]{6}Z__|operator notes|run id' digests/2026-05-04-daily-digest.md`

**Risks:**
- Many current shortlisted sources may still block full bodies, especially AIM/Inman.
- Telegram may remain `not_configured` independently of enrichment quality.

**Non-goals:**
- Do not claim production-clean if source discovery or Telegram delivery is still partial/not configured.

## Coverage Matrix

| Requirement | Milestone |
| --- | --- |
| Fetch only current-run shortlisted URLs | SFE-M2, SFE-M3, SFE-M4 |
| No raw/dropped/digest/story broad fetch | SFE-M2, SFE-M3 |
| Store full bodies under `.state/articles/` | SFE-M2 |
| Keep downstream enriched records compact | SFE-M3, SFE-M6 |
| Normalize `full/snippet_fallback/paywall_stub` | SFE-M1, SFE-M2, SFE-M3 |
| Static HTTP first | SFE-M1 |
| Elevated Codex I/O isolated to article acquisition | SFE-M4, SFE-M5 |
| Optional browser fallback only after static failure | SFE-M6 |
| No login/CAPTCHA/paywall/proxy bypass | SFE-M1, SFE-M5, SFE-M6, SFE-M7 |
| Runtime docs and fixtures updated | SFE-M3, SFE-M4, SFE-M5 |
| Live recovery run after implementation | SFE-M7 |

## Current Recommendation

Implement SFE-M1 through SFE-M3 first. Stop for review before SFE-M4 because the key design decision is the staged wrapper contract: stage B may be elevated for I/O, but stage A and stage C must remain sandboxed and stage B must have a narrow read/write contract.
