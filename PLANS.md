# Active Plans Index

This file is the compact active-plan entry point for runner-facing work. Archived
plans are retained for human review and traceability under `docs/plans/archive/`;
they are not required runtime context for implementing RT-M2 through RT-M7.

## Active Plan

| Title | Status | Stable heading | Notes |
| --- | --- | --- | --- |
| Minimal Codex Runner Scraping Tooling | completed through RT-M7; RT-M8 also completed | `## Addendum: Minimal Codex Runner Scraping Tooling` | Current runner scraping tooling plan and live scrape test are complete. |

## Archived and Inactive Plans

| Title | Status | Path | Notes |
| --- | --- | --- | --- |
| Claude Cowork Agent Refactor | completed/inactive | `docs/plans/archive/claude-cowork-agent-refactor.md` | Preserves base refactor requirements, milestone progress, detailed M0-M19 plan, coverage, dependency graph, guardrails, and cutover checklist. |
| Codex CLI Server Launch Mode | completed/inactive | `docs/plans/archive/codex-cli-server-launch-mode.md` | Preserves CLI-M1..CLI-M3 launch-mode requirements, coverage, and implementation status. |
| Stakeholder Request Deployment Setup | inactive prior addendum | `docs/plans/archive/stakeholder-request-deployment-setup.md` | Preserves stakeholder deployment setup requirements, milestones, acceptance tests, weak spot audit, and status. |
| CR Fix: cr_telegram_formatting__20260422 | inactive/unresolved | `docs/plans/archive/cr-telegram-formatting-20260422.md` | Preserves root-cause notes, CR milestones, and unchecked acceptance criteria for Telegram formatting. |

## Context Hygiene Notes

- RT-M2 through RT-M7 should use the active scraping tooling plan below, not the
  archived human-history files.
- The archive paths above are stable review references and should not become
  `Claude Cowork` runtime dependencies.
- Historical requirement traceability is preserved in the archive files by keeping
  the moved plan bodies intact with their original headings and tables.

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
