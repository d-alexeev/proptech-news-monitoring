# Victory Digest Completion Audit: 2026-05-04

## Verdict

Status: deterministic Stage C implemented; live rerun passed the 95% production-ready gate.

The repository-side staged runner now has deterministic Stage C materialization:
Stage C Codex writes a strict compact finish draft, `tools/stage_c_finish.py`
validates it against the current shortlist and article prefetch result, and the
helper writes current-run enrichment, digest, brief, manifest, and finish-summary
artifacts.

The live Victory run `20260504T142209Z-weekday_digest` completed successfully
and passed the defined 95% production-ready test-run gate. It remains a
production candidate, not a fully production-clean run, because source discovery
is still partial and live Telegram delivery was not attempted without
credentials.

## Original Requirements Audit

| Requirement | Status | Evidence |
| --- | --- | --- |
| One wrapper invocation for staged weekday digest | Implemented | `ops/codex-cli/run_schedule.sh weekday_digest` stages source prefetch, Stage A, Stage B, and Stage C. |
| Stage A and Stage C use `workspace-write` | Implemented | wrapper `codex exec` calls use `-s workspace-write`. |
| Stage B calls `tools/shortlist_article_prefetch.py` directly | Implemented | wrapper calls the helper against the current-run shortlist. |
| Stage B is shortlist-scoped | Implemented | helper input is the current-run shortlist shard; live run attempted all 15 shortlisted URLs. |
| Stage B writes article artifacts and manifests | Implemented | live run wrote article-prefetch result/summary, 9 full article entries, 4 paywall stubs, and 2 snippet fallbacks. |
| Synthetic Stage B fallback exists | Implemented | `tools/codex_schedule_artifacts.py synthetic-article-prefetch`. |
| Stage C receives source and article prefetch artifacts | Implemented as prompt handoff | generated finish prompt includes source prefetch and article prefetch paths. |
| Stage C writes strict compact finish draft | Implemented | finish prompt requires `.state/codex-runs/{run_id}-finish-draft.json`; live run produced a valid draft. |
| Deterministic Stage C materializer writes final artifacts | Implemented | `tools/stage_c_finish.py` wrote current-run enriched, brief, digest, run manifest, and finish-summary artifacts. |
| Digest/review must not read `.state/articles/` | Implemented as contract | Stage C prompt forbids article-body access outside `scrape_and_enrich`. |
| Offline tests and validators pass | Implemented | latest local verification covers wrapper, helper, artifact validator, compile, syntax, and diff checks. |
| Live Victory Digest run executed | Implemented | run `20260504T142209Z` completed wrapper execution and wrote current-run finish artifacts. |
| 95% production-ready test-run gate passed | Implemented | finish validation, article prefetch gate, QA gate, digest safety scans, and Telegram dry-run all passed. |
| Run review records sanitized results | Implemented | `docs/run-reviews/2026-05-04-weekday-digest.md`. |
| Completion audit exists | Implemented | this file. |

## Live Run Findings

| Stage | Result | Notes |
| --- | --- | --- |
| Source prefetch | Partial classified | static fetch 6/8 usable; source-level failures recorded for CoStar, Rightmove, OnlineMarketplaces, and Similarweb. |
| Stage A discovery | Partial success | 59 raw candidates and 15 shortlisted items. |
| Stage B article prefetch | Partial success | 9 `full`, 4 `paywall_stub`, 2 `snippet_fallback`; all shortlisted URLs attempted. |
| Stage C finish | Materialized | strict finish draft validated; deterministic helper wrote current-run artifacts. |
| QA | Passed with warnings | `qa_review.status = warnings`; `critical_findings_count = 0`. |
| Telegram | Dry-run passed | generated digest rendered into 2 dry-run message parts; no live delivery attempted. |

## Residual Gaps

- Source discovery remains partial: Rightmove DNS, CoStar timeout,
  OnlineMarketplaces empty listing, Similarweb 403.
- Telegram delivery is still unverified because credentials were intentionally
  absent from the test env.
- Some `body_status_hint = full` AIM Group article files include subscriber
  teaser text rather than unrestricted complete bodies; the digest keeps those
  summaries conservative.

## Changes Added After The Live Finding

- Added `validate-finish-artifacts` to `tools/codex_schedule_artifacts.py`.
- Wired the wrapper to fail after Stage C if current-run finish manifests are
  missing.
- Strengthened the Stage C prompt to require current-run artifact names based
  on the schedule run id timestamp.
- Added `tools/stage_c_finish.py` and offline tests.
- Reworked Stage C so Codex emits a compact draft while deterministic code writes
  final artifacts.
- Updated run review and plan status to mark the rerun as `production_candidate_95`.

## Follow-Ups

1. Add a post-run operator report artifact summarizing Stage A/B/C readiness in
   one compact JSON document.
2. Re-run Victory Digest with real Telegram env only after operator approval for
   live delivery credentials.
3. Resolve or downgrade persistent source blockers:
   `rightmove_plc`, `costar_homes`, `onlinemarketplaces`, and
   `similarweb_global_real_estate`.

## Compatibility Notes

- `.state/articles/` remains local-only and is not a digest/review input.
- Existing date-level digest paths are preserved, but staged-run success is
  proven only by current-run manifests plus finish summary.
- The finish-artifact guard remains intentionally fail-fast for missing or
  invalid Stage C drafts/materialized outputs.
