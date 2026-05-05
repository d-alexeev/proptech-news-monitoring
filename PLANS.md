# Active Plans Index

This file is the compact active-plan entry point for runner-facing work. Archived
plans are retained for human review and traceability under `docs/plans/archive/`;
they are not required runtime context for implementing RT-M2 through RT-M7.

## Active Plan

| Title | Status | Stable heading | Notes |
| --- | --- | --- | --- |
| Minimal Codex Runner Scraping Tooling | completed through RT-M7; RT-M8 also completed | `## Addendum: Minimal Codex Runner Scraping Tooling` | Current runner scraping tooling plan and live scrape test are complete. |
| Source Group Corrections After Live Test | completed | `## Addendum: Source Group Corrections After Live Test` | Corrected REA Group to media releases and promoted Inman into `daily_core`. |
| Weekday Digest Launch Hardening | completed through WLH-M8; externally blocked in recovery run | `docs/plans/weekday-digest-launch-hardening.md` | Follow-up plan for launch wrapper, env parsing, Telegram redaction, digest path/status semantics, and recovery dry-run. WLH-M8 reached the agent through the canonical wrapper and recorded the run as externally blocked by runner DNS plus missing non-interactive browser support. |
| Source Discovery Runner Prefetch | completed through SD-M4; recovery run partial before browser-runner follow-up | `docs/plans/source-discovery-runner-prefetch.md` | Static source network I/O now runs in deterministic runner prefetch before the inner `codex exec`. The original recovery run generated a partial digest with source-level Rightmove DNS, CoStar timeout, pre-HBR browser coverage gap, and Telegram env not configured; browser coverage was addressed by the Headless Browser Runner plan below. |
| Headless Browser Runner | completed through HBR-M5; recovery run partial | `docs/plans/headless-browser-runner.md` | Playwright-backed browser runner is installed and integrated into scheduled prefetch. Recovery run produced browser evidence, but remained partial because Similarweb returned 403, OnlineMarketplaces yielded no listing items, static sources had CoStar timeout/Rightmove DNS, and Telegram env is not configured. |
| Shortlist Full-Text Enrichment Runner | active; completed through SFE-M5; SFE-M6 optional | `docs/plans/shortlist-fulltext-enrichment-runner.md` | Article fetch helper, direct shortlist article prefetch, and `scrape_and_enrich` manifest contracts are implemented. The staged wrapper uses direct Stage B rather than a separate elevated Codex runner. |
| Victory Digest Production Readiness | completed through VD-M7; latest rerun is `production_candidate_95` | `docs/plans/victory-digest-production-readiness.md` | Staged weekday wrapper, direct Stage B, synthetic fallback, offline gate, and current-run finish-artifact guard are implemented. Live run `20260504T142209Z` completed with deterministic Stage C materialization and passed the 95% gate, with residual source-discovery and live Telegram caveats. |
| Deterministic Stage C Finish | completed; live rerun passed 95% production-ready gate | `docs/superpowers/plans/2026-05-04-deterministic-stage-c-finish.md` | Stage C emits a strict compact draft; `tools/stage_c_finish.py` materializes current-run enrichment/digest artifacts and finish summary. Live rerun `20260504T142209Z` passed artifact validation, article prefetch gate, QA gate, digest safety scans, and Telegram dry-run. |
| Inman Visible Paywall Text | completed; live Inman check passed | `## Addendum: Inman Visible Paywall Text` | Preserves publicly visible article text on Inman paywall pages as `snippet_fallback` evidence through source-scoped public browser fallback, without login, CAPTCHA, subscription, or paywall bypass. |
| Russian Telegram Digest | planned | `docs/superpowers/plans/2026-05-04-russian-telegram-digest.md` | Enforce Russian-only editorial prose for `telegram_digest` through prompt/contracts, Stage C materializer gate, and Telegram pre-send gate. |
| Telegram Digest Template and Preview | planned | `docs/superpowers/plans/2026-05-04-telegram-digest-length-budget.md` | Add a stable compact one-message template for weekday `telegram_digest`, parse top-story lead image metadata, deliver via large Telegram link preview, enforce Stage C hard length/template/preview gates, and verify a regenerated digest with Telegram dry-run `parts_sent=1`. |
| Runner Telegram Delivery Retry | completed through TDR-M1 | `## Addendum: Runner Telegram Delivery Retry` | Final weekday Telegram delivery retry now runs in the schedule wrapper after deterministic materialization, so DNS/network delivery failures can be retried without rerunning discovery, enrichment, or digest generation. |
| Documentation Refresh After Runner Work | completed | `docs/superpowers/plans/2026-05-05-documentation-refresh.md` | Updated root, operator, tool, onboarding, and benchmark docs after the last 100 commits introduced the staged Codex weekday runner, Playwright/browser prefetch, Stage B article prefetch, deterministic Stage C, Russian Telegram gates, compact template, and benchmark judge additions. |

## Archived and Inactive Plans

| Title | Status | Path | Notes |
| --- | --- | --- | --- |
| Claude Cowork Agent Refactor | completed/inactive | `docs/plans/archive/claude-cowork-agent-refactor.md` | Preserves base refactor requirements, milestone progress, detailed M0-M19 plan, coverage, dependency graph, guardrails, and cutover checklist. |
| Codex CLI Server Launch Mode | completed/inactive | `docs/plans/archive/codex-cli-server-launch-mode.md` | Preserves CLI-M1..CLI-M3 launch-mode requirements, coverage, and implementation status. |
| Stakeholder Request Deployment Setup | inactive prior addendum | `docs/plans/archive/stakeholder-request-deployment-setup.md` | Preserves stakeholder deployment setup requirements, milestones, acceptance tests, weak spot audit, and status. |

## Context Hygiene Notes

- RT-M2 through RT-M7 should use the active scraping tooling plan below, not the
  archived human-history files.
- The archive paths above are stable review references and should not become
  `Claude Cowork` runtime dependencies.
- Historical requirement traceability is preserved in the archive files by keeping
  the moved plan bodies intact with their original headings and tables.

## Addendum: Runner Telegram Delivery Retry

### Goal

Make `weekday_digest` Telegram delivery recoverable when the inner Stage C
`codex exec` sandbox cannot resolve or reach `api.telegram.org`, without
rerunning source discovery, article prefetch, enrichment, or digest generation.

### Scope

Likely files/artifacts to change:

- `ops/codex-cli/run_schedule.sh`
- `tools/codex_schedule_delivery.py`
- `tools/test_codex_schedule_delivery.py`
- `PLANS.md`

### Milestones

| Milestone | Goal | Acceptance criteria | Verification |
| --- | --- | --- | --- |
| TDR-M1 | Add wrapper-level Telegram delivery retry after Stage C materialization | If Stage C already reports `delivered: true`, wrapper delivery is skipped; otherwise the wrapper sends the materialized markdown through `tools/telegram_send.py`; DNS/HTTP/API failures are retried by rerunning only delivery; a delivery report is written under `.state/codex-runs/`; digest manifest and finish summary expose the final delivery status; failed delivery does not invalidate already materialized digest artifacts. | New helper fixture tests pass; schedule self-test still passes; Python compile checks pass. |

Status: completed on 2026-05-05.

### Coverage Matrix

| Requirement | Milestone |
| --- | --- |
| Retry Telegram delivery after DNS failure | TDR-M1 |
| Do not rerun discovery/enrichment/digest just to retry delivery | TDR-M1 |
| Avoid duplicate sends when Stage C already delivered | TDR-M1 |
| Preserve reviewable delivery status in artifacts | TDR-M1 |
| Keep non-delivery from corrupting materialized digest artifacts | TDR-M1 |

### Non-Goals

- No changes to source discovery, article prefetch, enrichment, digest scoring,
  digest template, or Russian-language gates.
- No proxy, alternate DNS, CAPTCHA, login, or Telegram API workaround.
- No automatic resend of historical failed runs beyond the current wrapper run.

### Current Milestone Acceptance Criteria

- `weekday_digest` calls the wrapper delivery helper after
  `tools/stage_c_finish.py`.
- The helper reads the materialized markdown path from the finish summary.
- The helper does not send when the finish draft already contains
  `telegram_delivery.delivered: true`.
- The helper retries delivery attempts without rerunning upstream stages.
- The helper writes `.state/codex-runs/<run_id>-telegram-delivery-report.json`.
- The helper updates the digest manifest operator report and finish summary with
  the final delivery status.
- Delivery failure remains a downstream delivery status, not a wrapper failure.

## Addendum: Inman Visible Paywall Text

### Goal

Preserve the public article text that is visible on Inman article pages even
when the same page also contains subscription or login UI.

### Scope

Likely files/artifacts to change:

- `tools/article_fetch.py`
- `tools/shortlist_article_prefetch.py`
- `tools/test_article_fetch.py`
- `tools/test_shortlist_article_prefetch.py`
- `cowork/adapters/source_map.md`
- `cowork/adapters/inman_public_partial_text.md`
- `PLANS.md`

### Milestones

| Milestone | Goal | Acceptance criteria | Verification |
| --- | --- | --- | --- |
| IPT-M1 | Add failing tests for visible Inman paywall text | Inman HTML with article text plus subscription marker is expected to produce `snippet_fallback` with text; shortlist prefetch is expected to persist a snippet article artifact. | `python3 tools/test_article_fetch.py` and `python3 tools/test_shortlist_article_prefetch.py` fail before implementation. |
| IPT-M2 | Implement source-scoped extraction, public browser fallback, and persistence | Inman public text is retained as `snippet_fallback`; static 403 may use public Playwright observation; empty/blocked paywall pages remain `paywall_stub`; no login, CAPTCHA, subscription, proxy, or paywall bypass is introduced. | Article fetch and shortlist prefetch tests pass; one live Inman browser observation confirms public text availability. |
| IPT-M3 | Document adapter behavior | Source map resolves Inman to a compact adapter note describing RSS discovery and public partial text handling. | Runtime validator and relevant tests pass. |

### Coverage Matrix

| Requirement | Milestone |
| --- | --- |
| Retain visible Inman article text from paywall pages | IPT-M1, IPT-M2 |
| Do not treat partial visible text as full article access | IPT-M1, IPT-M2 |
| Do not bypass login, CAPTCHA, subscription, or paywall controls | IPT-M2, IPT-M3 |
| Persist usable partial text for Stage C handoff | IPT-M1, IPT-M2 |
| Keep source-specific behavior documented in adapter files | IPT-M3 |
| Use browser fallback only when static Inman fetch cannot see public text | IPT-M2, IPT-M3 |

### Non-Goals

- No new `body_status_hint` enum.
- No interactive or credentialed browser automation for Inman article pages.
- No browser login, CAPTCHA solving, subscription flow, cookie seeding, or proxy rotation.
- No credentialed Inman access.
- No changes to historical run artifacts.

## Addendum: Source Group Corrections After Live Test

### Summary

This addendum covers two post-RT-M7 source-group corrections:

- replace the REA Group manual-only investor-centre source with the public
  media releases page at
  `https://www.rea-group.com/about-us/news-and-insights/media-releases/`;
- move `inman_tech_innovation` from `weekly_context` into `daily_core`.

### Scope

Likely files/artifacts to change:

- `config/runtime/source-groups/daily_core.yaml`
- `config/runtime/source-groups/weekly_context.yaml`
- `config/runtime/mode-fixtures/runner_integration_map.yaml`
- `config/runtime/mode-fixtures/runner_fetcher_contract_inman.yaml`
- `cowork/adapters/source_map.md`
- `cowork/adapters/blocked_manual_access.md`
- `monitor-list.json`
- `COMPLETION_AUDIT.md`
- `docs/runner-live-scrape-test-report.md`
- `tools/test_validate_runtime_artifacts.py`

Explicit non-goals:

- do not edit historical digest outputs;
- do not add a new scraper path beyond existing HTTP/RSS fetcher behavior;
- do not introduce browser, CAPTCHA, login, proxy, or full-body expansion.

### Acceptance Criteria

- `daily_core` includes `inman_tech_innovation`.
- `weekly_context` no longer includes `inman_tech_innovation`.
- `daily_core` includes a REA Group media releases source using
  `fetch_strategy: html_scrape` and the requested media releases URL.
- The old REA investor-centre manual-only source is not listed as an active
  runner source.
- Runner integration validation maps every configured source exactly once.
- Documentation/audit artifacts no longer describe the old REA manual-only
  source as the current runtime behavior.
- Validation passes:
  `python3 tools/validate_runtime_artifacts.py --check all`,
  `python3 tools/test_validate_runtime_artifacts.py`,
  and relevant Python compile checks.

### Status

Completed on 2026-05-04.

## Addendum: Minimal Codex Runner Scraping Tooling

### Summary

Этот addendum фиксирует минимально необходимый набор инструментов для
source-facing scraping/fetching, если фактическим runtime runner является Codex,
а source-specific поведение остаётся в `cowork/adapters`.

Цель не в том, чтобы построить универсальный crawler. Цель — дать Codex ровно
достаточно I/O-инструментов, чтобы исполнять существующие mode contracts:
`monitor_sources` открывает только discovery/snippet surfaces, а
`scrape_and_enrich` получает full text только для shortlisted items.

### Decisions Already Made

| Topic | Decision |
| --- | --- |
| Runner | Codex is the active runner and can perform adapter-aware reasoning. |
| Source knowledge | Source-specific behavior remains in `cowork/adapters`, resolved through `cowork/adapters/source_map.md`. |
| Default fetch path | Prefer static RSS/HTTP/API fetch over browser automation whenever an adapter permits it. |
| Browser scope | Browser automation is a narrow fallback for `chrome_scrape`/UI-driven pages, not the default fetch method. |
| Full text | Full article body remains allowed only in `scrape_and_enrich` and only for shortlisted items. |
| Blocked sources | No CAPTCHA, login, paywall bypass, or proxy rotation in the MVP; emit `change_request` or manual reminders according to adapter policy. |
| State writes | Tools may return JSON, but the runner/mode layer owns `.state/` artifact writing and schema validation. |
| Inman coverage | Inman must be treated as a regular scraping-analysis source, covered by the same runner tooling and validation as other recurring sources. |
| Plan context hygiene | `PLANS.md` should not become a large runtime context dependency for Codex or `Claude Cowork`; old/completed plan blocks should be indexed or archived before implementation work depends on this plan. |

### Minimal Tool Set

| Tool | Purpose | Required For |
| --- | --- | --- |
| HTTP/RSS/API fetcher | Fetch RSS/Atom, static HTML, and simple JSON API responses with timeouts, retries, soft-fail labels, and response metadata. | `rss`, `html_scrape`, `itunes_api`; already mostly covered by `tools/rss_fetch.py`. |
| Browser fallback | Read JS/UI-driven public pages when static fetch is insufficient. | `similarweb_*`, Google Play app pages, OnlineMarketplaces/Property Portal Watch if static extraction is insufficient. |
| PDF text extractor | Extract title/date/body text from downloaded public PDFs. | Rightmove PLC RNS PDF enrichment. |
| Artifact/schema validator | Validate compact runtime artifacts, source adapter resolution, full-text boundaries, and change-request shape. | All source-facing modes and dry-run acceptance checks. |

Everything else is intentionally out of scope for the MVP unless a later
adapter-backed `change_request` proves it is necessary.

### Requirements

| ID | Requirement |
| --- | --- |
| RT-R1 | The runner must support RSS/Atom feed fetch and static HTTP page fetch through one JSON-in/JSON-out interface. |
| RT-R2 | The same fetch interface must support iTunes lookup JSON endpoints without introducing a separate API client. |
| RT-R3 | Static fetch results must include HTTP metadata, final URL, soft-fail labels, and enough raw body/item data for Codex to apply adapter rules. |
| RT-R4 | Browser automation must be available only as a bounded fallback for sources whose configured strategy or adapter requires UI-driven access. |
| RT-R5 | Browser automation must not be used to automate login, CAPTCHA, paywall bypass, or manual-only sources. |
| RT-R6 | PDF extraction must be available for shortlisted/enrichment cases such as Rightmove RNS PDFs. |
| RT-R7 | The runner must resolve source adapters from `source_map.md` and load only adapters relevant to the current source group or shortlist. |
| RT-R8 | `monitor_sources` must not fetch or consume full article bodies, even if HTTP/browser tools could do so. |
| RT-R9 | `scrape_and_enrich` must fetch full text only from current-run shortlisted items and normalize outcomes to `full`, `snippet_fallback`, or `paywall_stub`. |
| RT-R10 | Tool failures that require persistent changes must become `change_request` artifacts rather than silent runtime workarounds. |
| RT-R11 | Acceptance checks must be runnable without live source fetch, Telegram delivery, secrets, proxy services, or CAPTCHA-solving. |
| RT-R12 | Inman must remain in the regular source coverage for scraping analysis, with explicit dry-run or fixture validation of its RSS/feed-based discovery path. |
| RT-R13 | After RT-M2..RT-M6 are implemented, Codex must run a bounded live test scraping pass, record what works and fails per source/tool path, and propose follow-up changes or change requests. |
| RT-R14 | Before implementing the scraping tooling milestones, reduce active plan context load by making the current runner scraping plan easy to load independently from old/completed tasks while preserving reviewable history. |

### Source Strategy Fit

| Source family | Minimal tool path | Notes |
| --- | --- | --- |
| Baseline RSS sources | HTTP/RSS fetcher | AIM, Zillow Mediaroom, CoStar, Redfin. |
| Inman regular scraping-analysis source | HTTP/RSS fetcher | Inman must be covered as a recurring source in scraping-analysis validation, using feed-based discovery and preserving paywall/snippet fallback behavior for downstream enrichment. |
| Static HTML discovery | HTTP fetcher + Codex adapter reasoning | Mike DelPrete articles index, Rightmove PLC homepage. |
| Listing-style HTML | HTTP fetcher first, browser fallback if needed | OnlineMarketplaces and Property Portal Watch. |
| Similarweb overview pages | Browser fallback | Public overview pages only; no gated category ranking scrape. |
| App Store | HTTP fetcher as JSON/API fetch | iTunes lookup API for iOS release metadata. |
| Google Play | Browser fallback | UI-driven app page extraction; no unofficial API in MVP. |
| Rightmove RNS PDFs | HTTP fetcher + PDF extractor | Discovery can remain static; PDF text only during enrichment when needed. |
| Manual/blocked sources | No fetch | Follow `blocked_manual_access` policy. |

### Milestones

Recommended implementation order: RT-M1 -> RT-M8 -> RT-M2 -> RT-M3 -> RT-M4
-> RT-M5 -> RT-M6 -> RT-M7. RT-M8 is listed later because it was added after
the initial plan, but it is a pre-implementation hygiene milestone.

#### RT-M1. Plan and Boundary

- Goal: lock the reduced tool set and runtime boundaries before changing any
  scripts, prompts, adapters, or contracts.
- Scope: `PLANS.md` only.
- Likely files/artifacts to change: `PLANS.md`.
- Dependencies:
  - `cowork/adapters/source_map.md`
  - `cowork/modes/monitor_sources.md`
  - `cowork/modes/scrape_and_enrich.md`
  - `config/runtime/mode-contracts/monitor_sources.yaml`
  - `config/runtime/mode-contracts/scrape_and_enrich_gate.yaml`
  - `config/runtime/mode-contracts/scrape_and_enrich_output.yaml`
- Risks:
  - overbuilding a crawler instead of honoring adapter-scoped source access;
  - accidentally expanding full-text usage into discovery mode.
- Acceptance criteria:
  - RT-R1..RT-R14 are recorded;
  - the minimal tool set is exactly four tool classes;
  - Inman is explicitly covered as a regular scraping-analysis source;
  - plan context hygiene is recorded as a required pre-implementation step;
  - browser fallback and blocked-source boundaries are explicit;
  - coverage matrix maps every requirement.
- Tests or verification steps:
  - manual review of this addendum;
  - acceptance test:
    `rg -n "RT-R1|RT-R14|Inman regular scraping-analysis source|Plan Context Hygiene|Minimal Tool Set|Coverage Matrix" PLANS.md`
- Explicit non-goals:
  - no implementation in this milestone;
  - no source config, adapter, prompt, or state schema edits;
  - no live network fetch.

#### RT-M2. Fetcher Contract Consolidation

- Goal: make the existing HTTP/RSS fetcher the single minimal interface for
  RSS, static HTML, and simple JSON/API fetches.
- Scope:
  - document or adjust fetcher invocation for `rss`, `html_scrape`, and
    `itunes_api`;
  - preserve JSON stdout and no-state-write contract.
- Likely files/artifacts to change:
  - `tools/rss_fetch.py`
  - `tools/README.md`
  - `tools/requirements.txt` only if a required parser dependency is missing
  - fixture or smoke docs under `config/runtime/mode-fixtures/` if needed
- Dependencies: RT-M1, RT-M8.
- Risks:
  - adding source-specific parsing into the generic fetcher;
  - making the fetcher write `.state/` directly;
  - changing exit-code semantics used by existing docs.
- Acceptance criteria:
  - one fetcher interface supports `kind=rss` and `kind=http`;
  - iTunes lookup URLs can be handled through the HTTP path and parsed by Codex
    or a narrow adapter-aware normalization step;
  - Inman feed discovery is represented by an offline fixture or dry-run sample
    as a regular recurring source, not an optional one-off check;
  - soft-fail labels remain explicit for blocked/paywall/rate-limited/timeout
    outcomes;
  - fetcher still writes no runtime state.
- Tests or verification steps:
  - syntax/import check for `tools/rss_fetch.py`;
  - fixture-based unit tests using local saved RSS, HTML, and JSON bodies if
    live network is not appropriate;
  - no test should require external network access.
- Explicit non-goals:
  - no browser automation;
  - no source-specific selector library inside `rss_fetch.py`;
  - no proxy or CAPTCHA handling.

##### WLH-M4. Batch Hard-Failure Exit Status

- Goal: align `rss_fetch.py` process exit status with emitted
  `batch_status="failed"` for multi-source hard failures.
- Scope:
  - change CLI exit handling only after the JSON document is emitted;
  - add deterministic offline coverage for one hard source error plus one
    successful source in the same batch;
  - clarify exit-code documentation if needed.
- Likely files/artifacts to change:
  - `tools/rss_fetch.py`
  - `tools/test_rss_fetch.py`
  - `tools/README.md`
- Dependencies: existing RT-M2 fetcher contract and offline test harness.
- Risks:
  - accidentally treating source-level soft fails as hard process failures;
  - changing the documented all-soft-fail exit code `10`;
  - broadening the diff beyond the WLH-M4 fetcher contract files.
- Acceptance criteria:
  - a multi-source batch with at least one non-soft source error exits nonzero;
  - the emitted JSON `batch_status` remains the source of truth for hard batch
    failure classification;
  - source-level soft-fail behavior is preserved, including all-soft-fail exit
    code `10`;
  - documentation clearly distinguishes hard batch failures from soft-fail
    outcomes.
- Tests or verification steps:
  - `python3 tools/test_rss_fetch.py`
  - `python3 tools/validate_runtime_artifacts.py --check all`
  - `git diff --check`
- Explicit non-goals:
  - no new source adapters or source-specific parsing;
  - no live network fetches;
  - no state schema or runtime artifact writes.

Coverage matrix for WLH-M4:

| Requirement | Milestone |
|---|---|
| Align exit status with `batch_status` for multi-source hard failures. | WLH-M4 |
| Preserve source-level soft-fail behavior and all-soft-fail behavior. | WLH-M4 |
| Add deterministic multi-source hard-error plus success test expecting nonzero exit. | WLH-M4 |
| Update docs if exit-code behavior changes or needs clarification. | WLH-M4 |

#### RT-M3. Browser Fallback Interface

- Goal: define the narrow browser fallback path for Codex-run scraping without
  turning it into the default fetch method.
- Scope:
  - choose the operational browser interface for runner use;
  - document when browser fallback is allowed;
  - define output shape equivalent to HTTP fetch results where practical.
- Likely files/artifacts to change:
  - `tools/chrome_notes.md` or a successor browser runner note
  - `tools/README.md`
  - optional browser helper script only if needed for repeatable headless runs
- Dependencies: RT-M1, RT-M8.
- Risks:
  - browser fallback becomes a hidden bypass for blocked/manual sources;
  - browser output lacks enough provenance to review extraction failures;
  - cron/server runner depends on an interactive browser session.
- Acceptance criteria:
  - browser fallback is allowed only for configured `chrome_scrape` sources or
    explicit adapter fallback cases;
  - manual-only sources still skip fetch and follow blocked-source policy;
  - output includes URL, final URL when available, page text or relevant HTML,
    timing/status-like metadata when available, and soft-fail reason when blocked;
  - docs distinguish interactive Codex/browser use from headless server use.
- Tests or verification steps:
  - static review of source strategy table against `config/runtime/source-groups/`;
  - fixture or dry-run output sample for one browser-backed source;
  - no test should automate login, CAPTCHA, or paywall flows.
- Explicit non-goals:
  - no proxy rotation;
  - no broad web crawling;
  - no replacement of RSS/static fetch where static fetch is sufficient.

#### RT-M4. PDF Extraction Helper

- Goal: add or document a tiny PDF-to-text path for enrichment-only PDF cases.
- Scope:
  - support public PDF download/text extraction for shortlisted items;
  - return compact text plus metadata for Codex classification.
- Likely files/artifacts to change:
  - `tools/pdf_extract.py` or equivalent documented helper
  - `tools/requirements.txt`
  - `tools/README.md`
  - fixture PDF or small text fixture if storing a binary fixture is unsuitable
- Dependencies: RT-M1, RT-M2, RT-M8.
- Risks:
  - PDF extraction leaks into `monitor_sources`;
  - large PDF text becomes downstream digest context instead of enrichment input;
  - binary fixtures add unnecessary repo weight.
- Acceptance criteria:
  - helper can extract text from a local PDF fixture or downloaded public PDF
    passed by the runner;
  - helper does not write `.state/`;
  - `monitor_sources` remains discovery-only and does not call PDF text
    extraction;
  - extracted text can be normalized by `scrape_and_enrich` into existing
    `body_status` policy.
- Tests or verification steps:
  - local fixture test or dry-run extraction sample;
  - contract review that PDF helper is referenced only for enrichment paths.
- Explicit non-goals:
  - no OCR requirement in MVP;
  - no PDF table reconstruction;
  - no bulk archive download.

#### RT-M5. Artifact and Schema Validation

- Goal: provide validation so Codex-run outputs are reviewable from artifacts,
  not just from runner narration.
- Scope:
  - validate adapter resolution;
  - validate mode artifact shape;
  - validate full-text boundary and change-request rules.
- Likely files/artifacts to change:
  - `tools/validate_runtime_artifacts.py` or extend an existing validator if one
    exists by then
  - `config/runtime/mode-fixtures/*`
  - `tools/README.md`
- Dependencies: RT-M1, RT-M8.
- Risks:
  - validator becomes too broad and reimplements runtime logic;
  - validation silently accepts missing fields needed by downstream modes.
- Acceptance criteria:
  - validator can check that every configured `source_id` resolves through
    `source_map.md` or `none`;
  - validator can check sample `raw_candidate`, `shortlisted_item`,
    `enriched_item`, `run_manifest`, and `change_request` fixtures against
    required fields;
  - validator detects full-text/body fields in forbidden mode fixtures;
  - validator can run offline.
- Tests or verification steps:
  - `python3 tools/validate_runtime_artifacts.py --check adapters`
  - `python3 tools/validate_runtime_artifacts.py --check fixtures`
  - `python3 tools/validate_runtime_artifacts.py --check full-text-boundary`
- Explicit non-goals:
  - no live source fetch;
  - no digest editorial scoring validation;
  - no Telegram send validation.

#### RT-M6. Dry-Run Integration and Completion Audit

- Goal: prove the reduced tool set can cover current adapters and document any
  remaining offline-contract gaps before live testing.
- Scope:
  - offline dry-run plan for current daily and weekly source groups;
  - fixture coverage for each fetch strategy family;
  - completion audit.
- Likely files/artifacts to change:
  - `config/runtime/mode-fixtures/*runner*`
  - `COMPLETION_AUDIT.md` or structured final milestone report
  - optional docs update if the runner footprint changes
- Dependencies: RT-M2, RT-M3, RT-M4, RT-M5.
- Risks:
  - dry-run passes but live sources still fail due to remote changes;
  - unsupported sources are hidden instead of recorded as known gaps.
- Acceptance criteria:
  - dry-run source plan covers `daily_core` and `weekly_context`;
  - Inman is listed in the runner integration map as a regular source with
    primary tool path `HTTP/RSS fetcher`;
  - each source is mapped to exactly one primary minimal tool path and optional
    fallback;
  - manual/blocked sources are represented explicitly and not fetched;
  - completion audit compares RT-R1..RT-R12 against implemented behavior;
  - any live-fetch risk is documented as residual risk, not silently ignored.
- Tests or verification steps:
  - offline dry-run source strategy validation;
  - validator checks from RT-M5;
  - syntax checks for touched scripts;
  - no Telegram delivery, secrets, CAPTCHA, or proxy required.
- Explicit non-goals:
  - no promise that every external website is reachable on every future run;
  - no permanent adapter fixes during scheduled runner execution;
  - no broad crawler launch.

#### RT-M7. Live Test Scraping and Follow-Up Proposal

- Goal: after the minimal tooling is implemented and offline checks pass, run a
  bounded live scraping test to see what works, what fails, and what should be
  changed next.
- Scope:
  - one controlled test pass across current `daily_core` and `weekly_context`
    source groups;
  - at least one representative fetch per source or landing/feed URL, respecting
    adapter policies;
  - no Telegram delivery;
  - no automated login, CAPTCHA, paywall bypass, or proxy rotation;
  - produce a structured scraping test report with follow-up recommendations.
- Likely files/artifacts to change:
  - `docs/runner-live-scrape-test-report.md` or dated report under an agreed
    docs/ops location
  - optional `./.state/runs/{run_date}/{run_id}.json` test run manifest if the
    runner execution path is already writing state artifacts
  - optional `./.state/change-requests/{request_date}/{request_id}.json` for
    persistent adapter/config/tooling gaps discovered during the test
- Dependencies: RT-M2, RT-M3, RT-M4, RT-M5, RT-M6.
- Risks:
  - live source behavior changes between test and production runs;
  - a test accidentally fetches full article bodies during `monitor_sources`;
  - failures get described informally but not converted into actionable follow-up
    changes;
  - blocked/manual sources are retried despite explicit policy.
- Acceptance criteria:
  - every configured `daily_core` and `weekly_context` source is listed with
    status `pass`, `soft_fail`, `blocked_manual`, `adapter_gap`, or `not_tested`
    with reason;
  - Inman is included in the live test report as a regular scraping-analysis
    source, not optional context;
  - each tested source records primary tool path, URL used, outcome, soft-fail
    label if any, and whether discovery/snippet extraction was sufficient;
  - no full article body is fetched during discovery-mode checks;
  - enrichment/full-text checks, if any are included, are limited to an explicit
    tiny shortlist sample and record `body_status`;
  - report separates transient source/network failures from persistent changes
    that require adapter/config/tool updates;
  - persistent gaps produce either concrete proposed plan updates or
    `change_request` artifacts with suggested target files and tests to add.
- Tests or verification steps:
  - run the live scrape test command or manual runner procedure defined by
    RT-M6 tooling;
  - run offline validator after the live test to confirm any written artifacts
    still satisfy contracts;
  - manually review report for source coverage, full-text boundary, and
    actionable follow-up recommendations.
- Explicit non-goals:
  - no delivery to Telegram;
  - no permanent fixes inside the live scraping milestone unless explicitly
    opened as a separate implementation milestone;
  - no attempt to bypass blocked/manual/paywalled/login-protected access;
  - no claim that live pass guarantees future source availability.

#### RT-M8. Plan Context Hygiene and Active-Plan Index

- Goal: keep this plan usable as runner input by separating the active scraping
  tooling plan from old or completed task blocks without losing review history.
- Scope:
  - make the active `Minimal Codex Runner Scraping Tooling` addendum directly
    findable and loadable without reading the whole `PLANS.md`;
  - either archive old/completed large plan blocks under a stable docs location
    or add a compact active-plan index that points to them;
  - preserve requirement traceability for archived plans.
- Likely files/artifacts to change:
  - `PLANS.md`
  - optional `docs/plans/archive/*.md` if old plan bodies are moved out of
    `PLANS.md`
- Dependencies: RT-M1.
- Risks:
  - losing historical traceability while reducing context load;
  - moving old plan text in a way that obscures prior user changes;
  - making `Claude Cowork` depend on a long human planning file.
- Acceptance criteria:
  - the active scraping tooling plan can be located by one stable heading or
    index entry;
  - old/completed plan blocks are not required context for implementing RT-M2
    through RT-M7;
  - archived or indexed plans retain enough title/status/path information for
    review;
  - any pre-existing uncommitted user changes in `PLANS.md` are preserved.
- Tests or verification steps:
  - `rg -n "Minimal Codex Runner Scraping Tooling|RT-M2|RT-M8|docs/plans/archive" PLANS.md`
  - manual review that active milestones RT-M2..RT-M7 remain intact after any
    archive/index change;
  - `git diff -- PLANS.md docs/plans/archive` review before reporting
    completion.
- Explicit non-goals:
  - no implementation of scraping tools in this milestone;
  - no deletion of historical planning content;
  - no runtime prompt/config/adapter changes.

### Coverage Matrix

| Requirement | Covered by |
| --- | --- |
| RT-R1 | RT-M2, RT-M6 |
| RT-R2 | RT-M2, RT-M6 |
| RT-R3 | RT-M2, RT-M5 |
| RT-R4 | RT-M3, RT-M6 |
| RT-R5 | RT-M3, RT-M5 |
| RT-R6 | RT-M4, RT-M6 |
| RT-R7 | RT-M5, RT-M6 |
| RT-R8 | RT-M4, RT-M5, RT-M6 |
| RT-R9 | RT-M4, RT-M5, RT-M6 |
| RT-R10 | RT-M2, RT-M3, RT-M5 |
| RT-R11 | RT-M5, RT-M6 |
| RT-R12 | RT-M2, RT-M6 |
| RT-R13 | RT-M7 |
| RT-R14 | RT-M8 |

### Milestone Acceptance Test Matrix

| Milestone | Acceptance Test Command | What It Proves |
| --- | --- | --- |
| RT-M1 | `rg -n "RT-R1|RT-R14|Inman regular scraping-analysis source|Plan Context Hygiene|Minimal Tool Set|Coverage Matrix" PLANS.md` | The plan captures the reduced tool set, Inman regular-source requirement, plan context hygiene requirement, and coverage. |
| RT-M2 | `python3 -m py_compile tools/rss_fetch.py` plus offline fetcher fixtures | The fetcher remains syntactically valid and supports RSS/HTML/JSON fixture handling without state writes. |
| RT-M3 | Browser fallback dry-run fixture or documented output sample | Browser use is bounded to configured/adapter-approved cases and does not bypass blocked/manual policy. |
| RT-M4 | Local PDF fixture extraction test | PDF text extraction exists for enrichment-only cases and does not write state. |
| RT-M5 | `python3 tools/validate_runtime_artifacts.py --check all` | Adapter resolution, artifact shapes, full-text boundary, and change-request fixtures validate offline. |
| RT-M6 | `python3 tools/validate_runtime_artifacts.py --check runner-integration` | Current source groups map onto the minimal tool set with explicit blocked/manual handling and no hidden source gaps. |
| RT-M7 | live scraping command/procedure from RT-M6 plus post-run validation | Implemented tooling has been exercised against current live sources, with pass/fail/gap results and follow-up recommendations. |
| RT-M8 | `rg -n "Minimal Codex Runner Scraping Tooling|RT-M2|RT-M8|docs/plans/archive" PLANS.md` plus manual diff review | The active scraping plan is findable without loading old/completed plan bodies, while archived history remains reviewable. |

### Weak Spot Audit

| Weak Spot | Requirements At Risk | How The Plan Guards It | Milestone That Must Prove It |
| --- | --- | --- | --- |
| Codex convenience leads to browser use for every source. | RT-R1, RT-R4 | Static RSS/HTTP/API is primary; browser fallback has explicit eligibility rules. | RT-M3, RT-M6 |
| Full text leaks into `monitor_sources`. | RT-R8, RT-R9 | PDF/body extraction is enrichment-only; validator checks forbidden body fields. | RT-M4, RT-M5 |
| iTunes support grows into a separate app-store subsystem. | RT-R2 | iTunes lookup stays under the HTTP/JSON fetch path. | RT-M2 |
| Blocked/manual sources get retried every run. | RT-R5, RT-R10 | Blocked policy is enforced by strategy validation and change-request/manual reminder handling. | RT-M3, RT-M5 |
| Generic fetcher starts embedding source-specific selectors. | RT-R3, RT-R7 | Fetcher returns raw compact data; Codex applies adapter rules after source_map resolution. | RT-M2, RT-M5 |
| PDF extraction becomes a bulk document pipeline. | RT-R6, RT-R8 | PDF helper is narrow, enrichment-only, and no-OCR in MVP. | RT-M4 |
| Offline validation hides live-source risk. | RT-R11, RT-R13 | Completion audit must list live-fetch residual risks, and RT-M7 performs a bounded live scraping pass after offline checks. | RT-M6, RT-M7 |
| Inman is accidentally treated as ad-hoc context rather than a recurring scraping-analysis source. | RT-R12 | Inman gets its own source strategy row and must appear in offline runner integration mapping. | RT-M2, RT-M6 |
| Live failures produce vague notes instead of actionable next changes. | RT-R10, RT-R13 | Live report must classify transient vs persistent failures and emit proposed plan updates or `change_request` artifacts for persistent gaps. | RT-M7 |
| Old tasks in `PLANS.md` inflate runner context and hide the active plan. | RT-R14 | Plan hygiene milestone must make the active scraping tooling plan loadable independently from old/completed plan bodies while preserving archive traceability. | RT-M8 |

### Current Implementation Status

| Milestone | Status |
| --- | --- |
| RT-M1 | completed |
| RT-M8 | completed |
| RT-M2 | completed |
| RT-M3 | completed |
| RT-M4 | completed |
| RT-M5 | completed |
| RT-M6 | completed |
| RT-M7 | completed |
