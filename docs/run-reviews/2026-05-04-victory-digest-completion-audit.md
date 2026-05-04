# Victory Digest Completion Audit: 2026-05-04

## Verdict

Status: partially implemented, not production-clean.

The repository-side staged runner is implemented through the offline gate:
Stage A discovery, direct Stage B article prefetch, synthetic fallback, Stage C
handoff prompts, docs, tests, and current-run finish-artifact validation exist.

The live Victory run `20260504T131334Z-weekday_digest` did not complete as a
clean production-like daily run. It proved Stage A and Stage B, but Stage C did
not create current-run enrichment or digest manifests and did not write a finish
last-message before the inner `codex exec` was stopped.

## Original Requirements Audit

| Requirement | Status | Evidence |
| --- | --- | --- |
| One wrapper invocation for staged weekday digest | Implemented | `ops/codex-cli/run_schedule.sh weekday_digest` stages source prefetch, Stage A, Stage B, and Stage C. |
| Stage A and Stage C use `workspace-write` | Implemented | wrapper `codex exec` calls use `-s workspace-write`. |
| Stage B calls `tools/shortlist_article_prefetch.py` directly | Implemented | wrapper calls the helper against the current-run shortlist. |
| Stage B is shortlist-scoped | Implemented | helper input is the current-run shortlist shard; live run attempted 14 shortlisted URLs. |
| Stage B writes article artifacts and manifests | Implemented | live run wrote article-prefetch result/summary and 8 local article files. |
| Synthetic Stage B fallback exists | Implemented | `tools/codex_schedule_artifacts.py synthetic-article-prefetch`. |
| Stage C receives source and article prefetch artifacts | Implemented as prompt handoff | generated finish prompt includes source prefetch and article prefetch paths. |
| Digest/review must not read `.state/articles/` | Implemented as contract | Stage C prompt forbids article-body access outside `scrape_and_enrich`. |
| Offline tests and validators pass | Implemented | latest local verification covers wrapper, helper, artifact validator, compile, syntax, and diff checks. |
| Live Victory Digest run executed | Partial | run `20260504T131334Z` reached Stage A/B and Stage C startup but did not cleanly finish. |
| Run review records sanitized results | Implemented | `docs/run-reviews/2026-05-04-weekday-digest.md`. |
| Completion audit exists | Implemented | this file. |

## Live Run Findings

| Stage | Result | Notes |
| --- | --- | --- |
| Source prefetch | Partial | static fetch 6/8 usable; browser fetch 1/2 usable. |
| Stage A discovery | Partial success | 59 raw candidates and 14 shortlisted items. |
| Stage B article prefetch | Partial success | 8 `full`, 4 `paywall_stub`, 2 `snippet_fallback`. |
| Stage C finish | Blocked | no current-run `scrape_and_enrich__20260504T131334Z__daily_core` or `build_daily_digest__20260504T131334Z__telegram_digest` manifests. |
| Telegram | Not configured | test run used an empty env file; no live delivery attempted. |

## Critical Gaps

- Stage C is still too agentic: it can fail to materialize fresh current-run
  mode artifacts even when Stage A/B handoff artifacts exist.
- Date-level digest and brief paths can mask stale output unless current-run
  manifests are checked.
- Inner `codex exec` emitted repeated plugin/analytics warnings and did not
  complete cleanly in the live run.
- Source discovery remains partial: Rightmove DNS, CoStar timeout,
  OnlineMarketplaces empty listing, Similarweb 403.
- Telegram delivery is still unverified because credentials were intentionally
  absent from the test env.

## Changes Added After The Live Finding

- Added `validate-finish-artifacts` to `tools/codex_schedule_artifacts.py`.
- Wired the wrapper to fail after Stage C if current-run finish manifests are
  missing.
- Strengthened the Stage C prompt to require current-run artifact names based
  on the schedule run id timestamp.
- Updated run review and plan status to mark VD-M7 as partial/blocked, not done.

## Deterministic Stage C Plan

Follow-up work is tracked in
`docs/superpowers/plans/2026-05-04-deterministic-stage-c-finish.md`.
The intended fix is to keep Codex responsible for compact analysis, but move
artifact writes to `tools/stage_c_finish.py`.

## Follow-Ups

1. Convert Stage C enrichment/digest artifact creation from freeform agent work
   into a narrower deterministic helper or a stricter mode runner contract.
2. Add a post-run operator report artifact summarizing Stage A/B/C readiness in
   one compact JSON document.
3. Re-run Victory Digest with real Telegram env only after current-run Stage C
   manifests are produced and validated.
4. Resolve or downgrade persistent source blockers:
   `rightmove_plc`, `costar_homes`, `onlinemarketplaces`, and
   `similarweb_global_real_estate`.

## Compatibility Notes

- `.state/articles/` remains local-only and is not a digest/review input.
- Existing date-level digest paths are preserved, but no longer prove a staged
  run succeeded without current-run manifests.
- The new finish-artifact guard is intentionally fail-fast and may mark the next
  live run failed until Stage C reliably writes timestamped mode artifacts.
