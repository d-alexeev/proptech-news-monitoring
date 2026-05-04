# Headless Browser Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a narrow non-interactive browser runner for configured `chrome_scrape` sources so scheduled runs can produce reviewable browser evidence without depending on an interactive desktop browser.

**Architecture:** Keep static source fetching in `tools/source_discovery_prefetch.py`, and add a separate runner-owned headless helper that only handles configured `chrome_scrape` sources. The wrapper/prefetch layer writes compact `.state/codex-runs/` browser evidence artifacts and passes paths to the inner `monitor_sources` prompt; the inner agent still runs sandboxed and does not perform live browser navigation itself.

**Tech Stack:** Python helper scripts, Playwright for headless browser automation, existing YAML source-group config, `.state/codex-runs/` evidence artifacts, existing mode fixtures and validator tests.

---

## Requirements

- Run only for sources whose source-group config declares `fetch_strategy: chrome_scrape`.
- Do not use browser automation for `rss`, `html_scrape`, `itunes_api`, blocked/manual-only, login, CAPTCHA, paywall, proxy, or broad crawl flows.
- Emit compact, reviewable JSON evidence compatible with `tools/chrome_notes.md`.
- Keep large HTML out of prompt context; use visible text and optional small fragments only.
- Integrate browser evidence into scheduled `weekday_digest` prefetch so `monitor_sources` no longer marks browser sources `not_attempted` when artifacts exist.
- Preserve partial-run semantics: browser failure is source-level soft-fail unless every required source path is unavailable.
- Install and verify Playwright as an explicit runner dependency before live browser scraping is expected to work.
- Add offline tests before implementation and run one live recovery scrape after implementation.
- Document runtime footprint, dependency expectations, and remaining caveats.

## Files And Responsibilities

- Create `tools/browser_fetch.py`: low-level JSON-in/JSON-out browser fetch helper for explicit URLs; no `.state` writes.
- Create `tools/test_browser_fetch.py`: offline unit tests for eligibility, output shape, compact text limits, and soft-fail mapping.
- Modify dependency/operator docs to install Playwright and its Chromium browser payload for the runner environment.
- Modify `tools/source_discovery_prefetch.py`: include browser source specs, call `browser_fetch.py`, write browser result artifact, and summarize attempted/success counts.
- Modify `tools/test_source_discovery_prefetch.py`: cover browser runner integration and fallback when the helper is unavailable.
- Modify `ops/codex-cli/run_schedule.sh`: pass browser artifact paths into the generated prompt only when prefetch produced them.
- Modify `tools/test_codex_cli_run_schedule.py`: wrapper regression coverage for browser artifact prompt wiring.
- Modify `cowork/modes/monitor_sources.md`: consume browser artifacts as discovery evidence and keep them bounded to snippets/listing metadata.
- Modify `config/runtime/mode-contracts/monitor_sources.yaml`: add scheduled browser prefetch artifact fields and handling rules.
- Modify `config/runtime/mode-fixtures/*`: add a fixture where browser artifacts are available for `onlinemarketplaces` and `similarweb_global_real_estate`.
- Modify `config/runtime/runtime_manifest.yaml`: register new fixtures.
- Modify `tools/README.md` and `ops/codex-cli/README.md`: document helper contract, dependencies, and scheduled-run footprint.
- Modify `docs/run-reviews/2026-05-04-weekday-digest.md`: after live recovery, record actual browser source outcomes.

## Milestone HBR-M1: Browser Helper Contract And Offline Tests

**Goal:** Define a low-level browser helper with the same bounded semantics as `tools/chrome_notes.md`.

**Scope:**
- Create `tools/browser_fetch.py`.
- Create `tools/test_browser_fetch.py`.
- Do not wire it into scheduled runs yet.

**Acceptance Criteria:**
- Helper accepts `{"sources":[{"source_id","url","source_group","fetch_strategy"}]}` via stdin.
- Helper rejects or soft-fails any source whose `fetch_strategy` is not `chrome_scrape`.
- Output contains `fetched_at`, `results[]`, `batch_status`, `failure_class`, and per-result `browser`.
- Visible text is compacted to a fixed maximum length.
- On unavailable browser dependency, helper exits with a stable environment failure instead of crashing.

**Tests / Verification:**
- `python3 tools/test_browser_fetch.py`
- `python3 -m py_compile tools/browser_fetch.py`

**Risks:**
- Playwright may not be installed in the runner environment.
- Browser install/download may require network or local package setup outside this repo.

**Non-goals:**
- No login, CAPTCHA solving, proxy rotation, screenshot archival, or source-specific item normalization.

## Milestone HBR-M2: Playwright Runner Installation

**Goal:** Make Playwright an explicit, verifiable dependency of the scheduled runner environment.

**Scope:**
- Add a repo-local dependency note for the Python Playwright package.
- Add a documented install command for the Chromium browser payload.
- Add a self-test command that proves Playwright can launch Chromium headlessly.
- Do not hide installation inside `weekday_digest`; dependency setup should be operator-visible.

**Acceptance Criteria:**
- `python3 -c "import playwright"` succeeds in the runner environment.
- `python3 -m playwright install chromium` has been run for the same Python environment used by scheduled jobs.
- A headless Chromium smoke test can open `about:blank` and exit cleanly.
- If Playwright is absent, `tools/browser_fetch.py` reports `browser_runtime_unavailable` instead of crashing.
- Docs identify that initial browser installation may require network access.

**Tests / Verification:**
- `python3 -c "from playwright.sync_api import sync_playwright; print('playwright import ok')"`
- `python3 -m playwright install chromium`
- `python3 - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("about:blank")
    print(page.title())
    browser.close()
PY`
- `python3 tools/test_browser_fetch.py`

**Risks:**
- Installing the Chromium payload requires network access and filesystem writes outside pure repo edits.
- The scheduled environment may use a different Python interpreter than the install command.
- macOS quarantine or CI/container restrictions may prevent Chromium launch even when the package imports.

**Non-goals:**
- Do not add automatic dependency installation to every scheduled run.
- Do not vendor browser binaries into the repository.

## Milestone HBR-M3: Prefetch Integration

**Goal:** Make `source_discovery_prefetch.py` attempt configured browser sources when the helper is available and preserve explicit skipped/failed evidence when it is not.

**Scope:**
- Extend prefetch plan to separate `static_source_specs` and `browser_source_specs`.
- Call `tools/browser_fetch.py --stdin --pretty` after static prefetch.
- Write `*-source-prefetch-browser-result.json`.
- Add summary fields:
  - `browser_result_path`
  - `browser_attempted_count`
  - `browser_success_count`
  - `browser_batch_status`
  - `browser_failure_class`

**Acceptance Criteria:**
- `chrome_scrape` sources are no longer automatically `not_attempted` when the browser helper is available.
- If the browser helper is unavailable, summary remains partial and explains `no_headless_browser_runner`.
- Static source prefetch behavior is unchanged.
- Browser failures do not erase successful static evidence.

**Tests / Verification:**
- Update and run `python3 tools/test_source_discovery_prefetch.py`.
- Run `python3 tools/test_browser_fetch.py`.

**Risks:**
- Summary schema drift could break `monitor_sources` expectations.
- Mixed static/browser partiality needs clear status semantics.

**Non-goals:**
- Do not make browser output canonical full-text enrichment.

## Milestone HBR-M4: Scheduled Wrapper And Mode Contract

**Goal:** Pass browser artifact paths to the inner agent and teach `monitor_sources` how to consume them.

**Scope:**
- Update generated prompt in `ops/codex-cli/run_schedule.sh`.
- Update `ops/codex-cli/prompts/weekday_digest.md`.
- Update `cowork/modes/monitor_sources.md`.
- Update `config/runtime/mode-contracts/monitor_sources.yaml`.
- Add/adjust fixtures for browser evidence present and browser evidence failed.

**Acceptance Criteria:**
- Generated prompt includes browser artifact path when present.
- `monitor_sources` consumes browser artifacts only as listing/snippet evidence.
- Existing static prefetch instructions still say not to repeat static network fetches inside sandbox.
- Browser artifact absence still produces explicit `not_attempted`, not silent omission.

**Tests / Verification:**
- `python3 tools/test_codex_cli_run_schedule.py`
- `python3 tools/test_validate_runtime_artifacts.py`
- `python3 tools/validate_runtime_artifacts.py --check all`
- `CODEX_RUN_SCHEDULE_SELF_TEST=1 ops/codex-cli/run_schedule.sh weekday_digest`

**Risks:**
- Prompt may accidentally invite full page dumps into context.
- Fixtures may need validator extensions for browser artifact fields.

**Non-goals:**
- Do not change digest format except source status wording required by real browser outcomes.

## Milestone HBR-M5: Live Browser Scrape And Recovery Digest

**Goal:** Run a scheduled recovery scrape and document what worked, what failed, and what remains partial.

**Scope:**
- Run `weekday_digest` through `ops/codex-cli/run_schedule.sh`.
- Inspect browser prefetch artifacts for `onlinemarketplaces` and `similarweb_global_real_estate`.
- Update run review and plan status.
- Generate/update the daily digest only if the run reaches digest generation.

**Acceptance Criteria:**
- Run review records per-browser-source status.
- Digest status reflects actual evidence quality: canonical only if all required source and enrichment gates pass; otherwise partial.
- No secrets, raw Telegram bot URLs, bulky HTML, or full article bodies appear in tracked docs/digest.
- Change requests are emitted or referenced for persistent browser source failures.

**Tests / Verification:**
- `ops/codex-cli/run_schedule.sh weekday_digest`
- `rg --count-matches 'api\\.telegram\\.org/bot|/bot[0-9]+:[A-Za-z0-9_-]+' docs/run-reviews/2026-05-04-weekday-digest.md digests/2026-05-04-daily-digest.md`
- `rg -n -- '\\.state/|__[0-9]{8}T[0-9]{6}Z__|operator notes|run id' digests/2026-05-04-daily-digest.md`
- `python3 tools/validate_runtime_artifacts.py --check all`

**Risks:**
- Live sites may block headless browsers or serve consent/login/CAPTCHA pages.
- Similarweb may expose less useful visible text than expected.
- Telegram may remain `not_configured` if env vars are absent.

**Non-goals:**
- Do not bypass anti-bot controls.
- Do not claim production-clean delivery unless Telegram and evidence gates are actually satisfied.

## Coverage Matrix

| Requirement | Milestone |
| --- | --- |
| Only configured `chrome_scrape` sources use browser runner | HBR-M1, HBR-M3 |
| Playwright installed and verified before live scraping | HBR-M2 |
| No login/CAPTCHA/paywall/proxy/manual-only automation | HBR-M1, HBR-M4, HBR-M5 |
| JSON output matches browser contract | HBR-M1 |
| Large HTML excluded from prompt context | HBR-M1, HBR-M4, HBR-M5 |
| Scheduled `weekday_digest` receives browser evidence | HBR-M3, HBR-M4 |
| Partial-run semantics preserved | HBR-M3, HBR-M4, HBR-M5 |
| Offline tests before implementation | HBR-M1, HBR-M3, HBR-M4 |
| Live recovery scrape after implementation | HBR-M5 |
| Runtime docs and footprint updated | HBR-M2, HBR-M4, HBR-M5 |

## Current Recommendation

Completed through HBR-M5 on 2026-05-04.

Implementation status:

- HBR-M1 added `tools/browser_fetch.py` and offline contract tests.
- HBR-M2 installed and verified Playwright Chromium in the runner environment;
  Chromium launch works outside the inner sandbox.
- HBR-M3 integrated browser fetching into `tools/source_discovery_prefetch.py`
  and wrote browser evidence artifacts under `.state/codex-runs/`.
- HBR-M4 wired browser artifact paths into the scheduled prompt and
  `monitor_sources` contracts/fixtures.
- HBR-M5 recovery run `20260504T111039Z-weekday_digest` generated
  `digests/2026-05-04-daily-digest.md` as `partial_digest`.

Recovery run findings:

- static prefetch: `6/8` usable; `costar_homes` timed out and `rightmove_plc`
  failed DNS;
- browser prefetch: `1/2` usable; `onlinemarketplaces` loaded but produced no
  article listing items, while `similarweb_global_real_estate` returned 403
  blocked/paywall;
- enrichment: all `14` shortlisted items used `snippet_fallback`;
- Telegram delivery: `not_configured` because required env vars are absent.

Remaining follow-ups:

- improve or replace OnlineMarketplaces extraction target/selectors;
- treat Similarweb as blocked source unless a compliant public evidence path is
  found;
- retry/remediate `rightmove_plc` DNS and monitor `costar_homes` timeouts;
- configure Telegram env before expecting live delivery.
