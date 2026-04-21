# Adapter: Blocked Manual Access

Applies to:

- `rea_group_investor_centre` (permanent manual-only)
- any future source declared with `fetch_strategy: blocked`

Use this adapter when the source requires manual, out-of-band, or
authenticated access that is not available inside the Claude Cowork runtime.

## Two modes

A blocked source is in exactly one of these states at any time:

### 1. `manual_only_permanent` — policy-by-design, no retry, no per-run CR

Use this when the source is known-blocked and the decision has been ratified
("we do not automate fetching this"). The runner must not attempt a fetch and
must not emit a `change_request` on every run; instead the `run_manifest`
records a single `manual_intake_reminder` entry at the declared cadence.

Current members:

- `rea_group_investor_centre` — investor centre explicitly forbids automated
  fetching in `config/runtime/source-groups/daily_core.yaml`; ratified as
  permanent manual-only on 2026-04-22 after the fourth consecutive
  per-run change_request. Cadence for manual intake: **monthly**.

Runner behavior:

- skip the fetch stage entirely;
- record the source as `source_quality=manual_blocked` with `body_status=null`
  in the run manifest;
- emit a `manual_intake_reminder` only when `now >= last_checked + cadence`
  (the reminder is a lightweight artifact — not a full `change_request`);
- do not emit a `change_request` unless the cadence policy itself becomes
  invalid (e.g., the source disappears, the URL changes, the manual intake
  backlog exceeds 2× cadence).

### 2. `blocked_provisional` — temporarily blocked, awaiting triage

Use this when a source was reachable before but is now failing with an
anti-bot, login, or paywall response that has not yet been classified. The
runner emits one `change_request` per week at most (not per run) while the
source stays in this state; repeated failures within the cooldown window are
collapsed into that single CR.

Transitions out of this state:

- codex_triage promotes to `manual_only_permanent` (the preferred path for
  IR/regulatory content), or
- codex_triage fixes the adapter/config and returns the source to its normal
  strategy, or
- codex_triage declares the source dead and removes it from the group.

## Rules

- do not keep retrying automated fetches once the block is confirmed —
  retry loops cause IP-reputation damage without producing content;
- mark the source as requiring manual user-side access or an out-of-band check
  in the run manifest;
- preserve the landing URL and source identity so missing coverage is visible
  in run artifacts;
- never silently drop a blocked source from a group — the absence must be
  explicit so audit trails can confirm the gap is known, not a regression.

## Notes

- this adapter records an operational limitation, not a content pattern;
- it exists so blocked sources are handled explicitly instead of failing
  silently or flooding the change_request log;
- the `manual_only_permanent` designation is not a license to ignore the
  source — it is a contract that coverage will be filled by a human on the
  declared cadence. If the cadence is missed, the runner must emit a
  `change_request` with `failure_type=persistent_workaround_required`.
