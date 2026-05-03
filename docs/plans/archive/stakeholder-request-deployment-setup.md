<!-- Archived from PLANS.md by RT-M8 Plan Context Hygiene. Human review history only; not runtime context. -->

## Addendum: Stakeholder Request Deployment Setup

### Summary

Этот addendum добавляет план для первичной настройки мониторинга под конкретного
стейкхолдера при deployment.

Текущие stakeholder profiles в `config/runtime/stakeholder-profiles/*.yaml`
описывают функцию или аудиторию, но не отделяют свободный тематический запрос
стейкхолдера от runtime config. Новая схема должна позволить нескольким
стейкхолдерам с разными business-unit интересами использовать тот же monitoring
source universe, но получать разную post-scrape selection, scoring and delivery.

Ключевой boundary: список источников и первичный source monitoring остаются
общими. Stakeholder request начинает влиять после первичного scraping/enrichment:
на reranking, selection, scoring adjustments, daily/weekly output emphasis and
stakeholder-specific delivery. Full-text policy не меняется.

### Decisions Already Made

| Topic | Decision |
| --- | --- |
| Stakeholder cardinality | Deployment may support multiple stakeholders, not only functional profiles like product/strategy. |
| Example target | A stakeholder can represent a real-estate business unit such as long-term rentals. |
| Source universe | Monitoring resources remain the same across stakeholders. |
| Request format | Stakeholder thematic request is free-form Markdown text. |
| Request location | Use a directory of Markdown request files, proposed as `config/runtime/stakeholder-requests/`. |
| Guide example | Include only one guide/example request based on the current default Avito monitor request. Do not include alternate examples in the guide. |
| Setup workflow | Initial deployment setup is manual: create a request file from the guide/template. |
| Runtime default | Server launch has a default stakeholder ID. |
| Runtime override | Server launch can run with an alternative stakeholder ID. |
| Delivery | Stakeholders may need separate Telegram chats or forum topics. |
| Same-instance multiple dailies | One server instance must be able to run multiple daily digests sequentially for different stakeholders. |
| Shared scrape optimization | Sequential stakeholder daily runs should reuse source discovery/scrape/enrichment artifacts and avoid duplicate scraping; later runs may perform only an incremental update check for new source changes before stakeholder-specific selection/rendering. |
| Weekly stream isolation | Weekly digests must not aggregate all stakeholder daily digests together; each weekly run must use one selected stakeholder stream, or the default stream, explicitly. |

### Requirements

| ID | Requirement |
| --- | --- |
| SR-R1 | Stakeholder thematic requests must live in standalone Markdown files, one file per stakeholder/request profile. |
| SR-R2 | The same source groups and source adapters must remain reusable across stakeholders. |
| SR-R3 | Stakeholder request must influence post-scrape selection and scoring, not only downstream copy personalization. |
| SR-R4 | Stakeholder request must not expand full article body usage beyond `scrape_and_enrich`. |
| SR-R5 | There must be a default stakeholder ID for server launch. |
| SR-R6 | Server launch must support overriding the stakeholder ID per run. |
| SR-R7 | Stakeholder delivery must allow separate Telegram chat and/or topic bindings. |
| SR-R8 | Initial deployment setup must be manual and documented, using a guide/template plus one default example request. |
| SR-R9 | Runtime contracts must make clear which modes may read stakeholder profile/request files and which modes may not. |
| SR-R10 | Existing ordinary/default monitoring should remain backward compatible when no alternative stakeholder is selected. |
| SR-R11 | One instance must support sequential daily runs for two or more stakeholder IDs without requiring separate deployments. |
| SR-R12 | Sequential stakeholder daily runs must reuse existing source-facing artifacts and avoid duplicate scraping when the source window has already been checked. |
| SR-R13 | Weekly digests must aggregate only the selected stakeholder's daily/brief stream, or the default stream, and must never mix daily briefs from all stakeholders by default. |

### Proposed Runtime Model

The recommended MVP model is:

- `config/runtime/stakeholder-requests/{stakeholder_id}.md`
  - free-form thematic request written for the stakeholder;
  - default request is based on the current global Avito monitor mission;
  - alternative requests are created manually by operators and referenced by profile ID.
- `config/runtime/stakeholder-profiles/{stakeholder_id}.yaml`
  - keeps structured controls: thresholds, max items, lens weights, format, delivery;
  - gains `request_path` pointing to exactly one Markdown request file;
  - can represent either a function (`product`) or a business unit (`long_term_rentals`).
- server launch config/prompt
  - has a default stakeholder ID;
  - accepts a per-run override;
  - passes only the selected profile and selected request to stakeholder-aware stages;
  - supports sequential runs for different stakeholder IDs on the same instance.

The selection architecture should become two-layer:

1. Base source-facing pipeline remains shared:
   `monitor_sources -> scrape_and_enrich`.
2. Stakeholder-aware post-scrape pipeline applies selected profile/request:
   selection, scoring adjustment, daily/weekly rendering emphasis and optional
   stakeholder fanout/delivery.

For same-instance multi-stakeholder daily usage, the optimized path should be:

1. Run or reuse a shared source-facing window check for the target digest date.
2. If new or changed source candidates exist, run `scrape_and_enrich` only for
   the new shortlist delta.
3. For each requested stakeholder ID, run stakeholder-aware selection/scoring and
   rendering from the compact enriched/story artifacts.
4. Record each stakeholder output separately while preserving shared run
   provenance, so reviewers can see whether two digests came from the same
   source-facing check.

Weekly aggregation should be stream-isolated:

- `build_weekly_digest` receives an explicit selected stakeholder ID or defaults
  to the default stakeholder stream.
- It includes only daily briefs/output refs matching that stakeholder stream and
  target ISO week.
- It must not scan `digests/profiles/` or `.state/briefs/daily/` and aggregate
  every stakeholder's daily output together.
- If a selected stakeholder has missing daily briefs for the week, weekly should
  report missing days for that stakeholder rather than filling gaps from another
  stakeholder.

### Open Design Assumptions To Validate During Implementation

| Assumption | Default for MVP |
| --- | --- |
| Default stakeholder ID location | Add an explicit field in Codex CLI launch config or prompt pack rather than hard-coding only in shell. |
| Existing `default` profile | Preserve it and attach the default Avito request file. |
| Alternative stakeholder output path | Include stakeholder ID in digest/state paths only when a non-default stakeholder is selected, or document any path change before implementation. |
| Daily/weekly base compatibility | Existing `telegram_digest` daily/weekly paths remain available for default runs. |
| Stakeholder-aware scoring | Implement as bounded reranking/score adjustment over enriched compact artifacts, not as source refetch. |
| Telegram overrides | Support env-var based overrides first; consider profile-level explicit delivery fields if needed. |
| Shared scrape cache key | Use digest date/window plus source group scope as the shared source-facing reuse key; include stakeholder ID only in downstream output keys. |
| Incremental second run | A second stakeholder daily run on the same instance should check whether source-facing artifacts for the window are fresh enough before doing any fetch, then reuse them if valid. |
| Weekly stream key | Use week ID plus selected stakeholder ID plus delivery profile as the weekly aggregation key; default weekly remains compatible with the existing default stream. |

### Milestones

#### SR-M1. Plan and Contract Boundary

- Goal: lock requirements, assumptions, and behavioral boundaries before
  changing runtime artifacts.
- Scope: `PLANS.md` only.
- Likely files/artifacts to change: `PLANS.md`.
- Dependencies:
  - existing stakeholder profiles;
  - `build_daily_digest` selection contract;
  - `build_weekly_digest` contracts;
  - Codex CLI launch pack.
- Risks:
  - accidentally turning stakeholder requests into source discovery inputs;
  - breaking default daily/weekly outputs by introducing stakeholder-specific paths too early.
- Acceptance criteria:
  - SR-R1..SR-R13 are captured;
  - user decisions are recorded explicitly;
  - milestones map every requirement;
  - non-goals are explicit.
- Tests or verification steps:
  - manual review of this plan addendum.
  - acceptance test:
    `rg -n "SR-R1|SR-R13|Coverage Matrix|Weak Spot Audit|Final Integration Test" PLANS.md`
- Explicit non-goals:
  - no runtime prompt/config edits beyond the plan;
  - no new source groups or source adapters;
  - no implementation of server CLI flags in this milestone.

#### SR-M2. Stakeholder Request Artifact Contract

- Goal: add the file contract for standalone Markdown stakeholder requests.
- Scope:
  - define request directory;
  - add default request example based on the current Avito monitor mission;
  - link profiles to request files.
- Likely files/artifacts to change:
  - `config/runtime/stakeholder-requests/default.md`
  - `config/runtime/stakeholder-profiles/default.yaml`
  - `config/runtime/stakeholder-profiles/index.yaml`
  - `config/runtime/runtime_manifest.yaml`
  - documentation for request file structure.
- Dependencies: SR-M1.
- Risks:
  - making long narrative request files required in every runtime mode;
  - duplicating mission brief content in a way that drifts.
- Acceptance criteria:
  - a default Markdown request file exists;
  - stakeholder profile points to exactly one request path;
  - runtime manifest lists the request directory or index as config source;
  - only the default example request is included in docs/guide.
- Tests or verification steps:
  - static path resolution check for profile `request_path`;
  - review that request files are not referenced by source-facing modes.
  - acceptance test:
    `python3 tools/validate_stakeholder_setup.py --check request-paths`
- Explicit non-goals:
  - no long-term rentals request example in the guide yet;
  - no scoring behavior change yet;
  - no Telegram delivery changes yet.

#### SR-M3. Stakeholder-Aware Selection and Scoring Contract

- Goal: define how selected stakeholder request/profile influences post-scrape
  selection and scoring.
- Scope:
  - update daily selection contract;
  - update weekly aggregation/trend contracts if stakeholder-specific weekly
    output is in scope;
  - define allowed request/profile inputs and forbidden raw/full-text inputs.
- Likely files/artifacts to change:
  - `config/runtime/mode-contracts/build_daily_digest_selection.yaml`
  - `config/runtime/mode-contracts/build_weekly_digest_aggregation.yaml`
  - `config/runtime/mode-contracts/build_weekly_digest_trends.yaml`
  - `cowork/modes/build_daily_digest.md`
  - `cowork/modes/build_weekly_digest.md`
  - mode fixtures for stakeholder-aware selection.
- Dependencies: SR-M2.
- Risks:
  - breaking R13-era separation where stakeholder personalization was downstream-only;
  - letting stakeholder requests alter upstream scraping or source lists;
  - producing incomparable scores without recording adjusted-vs-base score provenance;
  - recomputing enrichment for every stakeholder instead of reusing shared enriched artifacts.
- Acceptance criteria:
  - stakeholder request/profile is allowed only after enrichment;
  - source discovery and scraping contracts remain stakeholder-agnostic;
  - score adjustment provenance is explicit, e.g. base score plus stakeholder relevance note/adjustment;
  - default stakeholder produces behavior compatible with current default monitor;
  - stakeholder-specific scoring works from compact enriched artifacts and does not require a second scrape for a second stakeholder;
  - weekly aggregation contract explicitly filters daily briefs by selected stakeholder stream and forbids all-stakeholder aggregation.
- Tests or verification steps:
  - fixture with default request should preserve current-style selection;
  - fixture with a rentals-oriented request should promote rentals-relevant enriched items without changing source inputs;
  - fixture or dry-run review should show two stakeholder selections from the same enriched input set;
  - weekly fixture should prove that default and alternative stakeholder daily briefs are not mixed in one weekly digest;
  - contract review that full article bodies remain forbidden outside `scrape_and_enrich`.
  - acceptance test:
    `python3 tools/validate_stakeholder_setup.py --check selection-fixtures`
- Explicit non-goals:
  - no source-list personalization;
  - no full-text expansion;
  - no automatic generation of stakeholder requests from free text.

#### SR-M4. Deployment and Server Launch Integration

- Goal: allow server launch to use a default stakeholder ID and per-run override.
- Scope:
  - update Codex CLI launch docs and prompts;
  - update wrapper interface if needed;
  - define default stakeholder ID configuration;
  - define sequential same-instance daily runs for one or more stakeholder IDs.
- Likely files/artifacts to change:
  - `ops/codex-cli/run_schedule.sh`
  - `ops/codex-cli/prompts/*.md`
  - `ops/codex-cli/README.md`
  - `docs/codex-cli-server-launch.md`
  - optional `ops/codex-cli/config.example.env` or documented env vars.
- Dependencies: SR-M2, SR-M3.
- Risks:
  - hidden default stakeholder assumptions in shell script;
  - accidental fanout for all stakeholders instead of one selected stakeholder;
  - path collisions between default and non-default outputs;
  - second stakeholder run triggering duplicate source scraping.
- Acceptance criteria:
  - server launch has a documented default stakeholder ID;
  - server launch can run one alternative stakeholder ID explicitly;
  - server launch can run two stakeholder daily outputs sequentially on the same instance;
  - server launch can run weekly for one selected stakeholder stream without aggregating other stakeholder daily outputs;
  - prompts require reuse of a fresh shared source-facing window before scraping again;
  - prompts instruct Codex to load only selected stakeholder profile/request;
  - ordinary no-override run remains valid.
- Tests or verification steps:
  - `bash -n ops/codex-cli/run_schedule.sh`;
  - dry-run/static invocation check for default and override argument parsing if implemented;
  - dry-run/static invocation check for sequential stakeholder IDs if implemented;
  - dry-run/static invocation check for weekly selected stakeholder stream if implemented;
  - prompt review for selected-stakeholder-only loading.
  - acceptance test:
    `ops/codex-cli/run_schedule.sh --dry-run weekday_digest --stakeholder default --stakeholder product`
- Explicit non-goals:
  - no multi-stakeholder batch fanout by default unless explicitly requested in the server launch command;
  - no production secret manager integration.

#### SR-M5. Stakeholder Delivery Binding

- Goal: support stakeholder-specific Telegram chat/topic routing.
- Scope:
  - define delivery override fields or env-var mapping;
  - document fallback behavior to existing delivery profile.
- Likely files/artifacts to change:
  - `config/runtime/stakeholder-profiles/*.yaml`
  - `config/runtime/schedule_bindings.yaml` only if a shared delivery contract change is needed;
  - `tools/README.md` or delivery docs;
  - Codex CLI launch docs.
- Dependencies: SR-M4.
- Risks:
  - leaking secrets into git-managed profile files;
  - making delivery profile resolution ambiguous.
- Acceptance criteria:
  - profile can select default schedule delivery or override chat/topic through env-var names;
  - no Telegram tokens or chat IDs are committed;
  - fallback path is explicit when stakeholder-specific env vars are absent.
- Tests or verification steps:
  - dry-run Telegram delivery profile resolution review;
  - static review that no secrets are present.
  - acceptance test:
    `python3 tools/validate_stakeholder_setup.py --check delivery-routing`
- Explicit non-goals:
  - no change to Telegram message formatting unless required by routing;
  - no non-Telegram delivery channel.

#### SR-M6. Validation and Completion Audit

- Goal: verify the full stakeholder request MVP and document compatibility.
- Scope:
  - mode fixtures;
  - path/schema checks;
  - final audit.
- Likely files/artifacts to change:
  - `config/runtime/mode-fixtures/*stakeholder*`
  - `COMPLETION_AUDIT.md` or structured final report.
- Dependencies: SR-M2, SR-M3, SR-M4, SR-M5.
- Risks:
  - fixture coverage proves only default behavior and misses alternative stakeholder behavior.
- Acceptance criteria:
  - every stakeholder profile request path resolves;
  - default stakeholder path preserves ordinary launch behavior;
  - alternative stakeholder run path is documented and fixture-covered;
  - two sequential stakeholder daily outputs can be produced from one shared enriched input set;
  - weekly integration fixture proves one selected stakeholder stream is aggregated and other stakeholder streams are ignored;
  - delivery fallback behavior is documented;
  - completion audit compares SR-R1..SR-R13 to implementation.
- Tests or verification steps:
  - fixture-based stakeholder-aware selection review;
  - config path validation;
  - shell syntax checks for launch scripts;
  - markdown/doc link review.
  - acceptance test:
    `python3 tools/validate_stakeholder_setup.py --check all`
  - final integration test:
    `python3 tools/validate_stakeholder_setup.py --check integration`
- Explicit non-goals:
  - no real Telegram send required for completion;
  - no live source fetch required for contract validation.

### Coverage Matrix

| Requirement | Covered by |
| --- | --- |
| SR-R1 | SR-M2 |
| SR-R2 | SR-M1, SR-M3 |
| SR-R3 | SR-M3 |
| SR-R4 | SR-M3, SR-M6 |
| SR-R5 | SR-M4 |
| SR-R6 | SR-M4 |
| SR-R7 | SR-M5 |
| SR-R8 | SR-M2, SR-M4 |
| SR-R9 | SR-M3, SR-M6 |
| SR-R10 | SR-M2, SR-M3, SR-M4, SR-M6 |
| SR-R11 | SR-M4, SR-M6 |
| SR-R12 | SR-M3, SR-M4, SR-M6 |
| SR-R13 | SR-M3, SR-M4, SR-M6 |

### Milestone Acceptance Test Matrix

Each milestone must leave a runnable acceptance test behind. Tests should be
static, fixture-based, or dry-run only unless the milestone explicitly says
otherwise. No milestone acceptance test should require live source fetch,
Telegram delivery, or secrets.

| Milestone | Acceptance Test Command | What It Proves |
| --- | --- | --- |
| SR-M1 | `rg -n "SR-R1|SR-R13|Coverage Matrix|Weak Spot Audit|Final Integration Test" PLANS.md` | The plan captures the stakeholder request requirements, coverage, weak-spot review, and final integration test. |
| SR-M2 | `python3 tools/validate_stakeholder_setup.py --check request-paths` | Every indexed stakeholder profile has exactly one `request_path`, every path exists, and `runtime_manifest.yaml` exposes the request config source. |
| SR-M3 | `python3 tools/validate_stakeholder_setup.py --check selection-fixtures` | Stakeholder-aware selection fixtures run from compact enriched/story artifacts, preserve default behavior, promote an alternative stakeholder-relevant item, isolate weekly streams, and do not require raw/full-text inputs. |
| SR-M4 | `ops/codex-cli/run_schedule.sh --dry-run weekday_digest --stakeholder default --stakeholder product` | Server launch can resolve a default plus an alternative stakeholder sequentially, reuse one source-facing window, avoid duplicate scrape/enrich steps, and keep weekly stream selection explicit in dry-run mode. |
| SR-M5 | `python3 tools/validate_stakeholder_setup.py --check delivery-routing` | Stakeholder delivery routing resolves Telegram env-var names for chat/topic overrides, falls back to schedule delivery, and contains no committed secrets. |
| SR-M6 | `python3 tools/validate_stakeholder_setup.py --check all` | Full static/fixture validation is green across request paths, selection/scoring contracts, server launch dry-run expectations, delivery routing, and compatibility guards. |

Acceptance test implementation expectations:

- SR-M2 should introduce `tools/validate_stakeholder_setup.py` with at least the
  `request-paths` check.
- Later milestones should extend the same validator rather than adding unrelated
  one-off scripts.
- `ops/codex-cli/run_schedule.sh --dry-run` must not call `codex exec`, fetch
  sources, or send Telegram messages. It should print the resolved schedule,
  selected stakeholder IDs, source-facing reuse key, prompt path, and expected
  output/delivery bindings.
- Fixture tests must use small deterministic fixture files under
  `config/runtime/mode-fixtures/` and must not read `.state/articles/`.

### Weak Spot Audit

| Weak Spot | Requirements At Risk | How The Plan Guards It | Milestone That Must Prove It |
| --- | --- | --- | --- |
| Stakeholder request accidentally becomes an input to `monitor_sources` or source adapters. | SR-R2, SR-R4, SR-R9, SR-R12 | Source-facing contracts remain stakeholder-agnostic; request/profile inputs are allowed only after enrichment. | SR-M3, SR-M6 |
| A second stakeholder daily run repeats scraping instead of reusing enriched artifacts. | SR-R11, SR-R12 | Shared source-facing reuse key excludes stakeholder ID; dry-run must show one source-facing check and multiple downstream selections. | SR-M4, SR-M6 |
| Default stakeholder path changes existing digest filenames or delivery behavior unexpectedly. | SR-R10 | Default profile gets a request file but existing default daily/weekly behavior remains compatible; path changes must be explicitly documented before implementation. | SR-M2, SR-M3, SR-M6 |
| Free-text request becomes too large and turns into a broad runtime dependency. | SR-R1, SR-R8, SR-R9 | Request files are loaded only for selected stakeholder-aware stages; source-facing modes do not read the request directory. | SR-M2, SR-M3 |
| Alternative stakeholder scoring overwrites base score, making decisions hard to audit. | SR-R3 | Scoring provenance must preserve base score plus stakeholder adjustment/relevance rationale. | SR-M3, SR-M6 |
| Long-term rentals or another business-unit stakeholder changes source groups by implication. | SR-R2, SR-R12 | Stakeholder request affects post-scrape selection/scoring only; source groups stay in schedule bindings. | SR-M3, SR-M4 |
| Delivery override commits chat IDs or secrets into git-managed profile files. | SR-R7 | Profiles may reference env-var names, not secret values; validator checks for likely committed secrets. | SR-M5 |
| Server launch accidentally fans out to every stakeholder profile. | SR-R6, SR-R11 | Server launch loads only selected stakeholder IDs; multi-stakeholder run is explicit via repeated `--stakeholder`. | SR-M4 |
| Weekly behavior is underspecified after daily becomes stakeholder-aware. | SR-R3, SR-R10, SR-R13 | SR-M3 must decide whether weekly is stakeholder-specific in MVP and update weekly contracts or explicitly defer with compatibility notes. | SR-M3 |
| Weekly digest mixes all stakeholder daily briefs in one aggregate. | SR-R10, SR-R13 | Weekly aggregation key includes selected stakeholder ID; weekly fixtures must include another stakeholder's daily brief and prove it is ignored. | SR-M3, SR-M6 |
| Completion audit misses new requirements because only SR-R1..SR-R10 were checked. | SR-R11, SR-R12, SR-R13 | Audit scope is SR-R1..SR-R13 and final integration test includes sequential daily reuse and weekly stream isolation. | SR-M6 |

### Final Integration Test

The final integration test must be added by SR-M6 and must be runnable without
network, secrets, or Telegram delivery.

Recommended command:

```bash
python3 tools/validate_stakeholder_setup.py --check integration
```

The integration fixture should model one digest date, one shared source group
scope, and two stakeholder IDs: `default` and one alternative business-unit
stakeholder such as `long_term_rentals`.

Required setup:

- a shared source-facing fixture with raw/shortlist/enriched compact artifacts;
- a default stakeholder request based on the current Avito monitor mission;
- an alternative stakeholder request fixture that emphasizes long-term rentals;
- two stakeholder profiles pointing to exactly one request file each;
- daily brief fixtures for both stakeholders in the same ISO week;
- delivery routing fixture with default delivery and one chat/topic override via
  env-var names only.

Required assertions:

- only one source-facing window/reuse key is produced for the fixture date and
  source group scope;
- both stakeholder daily outputs reference the same source-facing run or reuse
  key;
- no second scrape/enrich step is planned for the second stakeholder when the
  shared artifacts are fresh;
- default stakeholder selection remains compatible with current default monitor
  expectations;
- alternative stakeholder selection promotes at least one rentals-relevant item
  that the default output does not promote as strongly;
- both outputs preserve base score plus stakeholder-specific score/rationale;
- full article bodies and `.state/articles/` are not used by selection,
  rendering, delivery, or validation;
- Telegram routing resolves env-var names without requiring or exposing token,
  chat ID, or topic ID values;
- output paths do not collide across stakeholders;
- weekly aggregation for the default stakeholder ignores alternative stakeholder
  daily briefs;
- weekly aggregation for the alternative stakeholder ignores default stakeholder
  daily briefs;
- missing daily briefs for one stakeholder are reported as missing for that
  stakeholder, not backfilled from another stakeholder;
- completion audit maps SR-R1..SR-R13 to pass/fail status.

### Current Implementation Status

| Milestone | Status |
| --- | --- |
| SR-M1 | completed |
| SR-M2 | pending |
| SR-M3 | pending |
| SR-M4 | pending |
| SR-M5 | pending |
| SR-M6 | pending |
