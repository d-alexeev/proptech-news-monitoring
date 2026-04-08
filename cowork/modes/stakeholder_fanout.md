# Mode Prompt: stakeholder_fanout

Load shared context from:

- `cowork/shared/mission_brief.md`
- `cowork/shared/contracts.md`

Purpose:

- transform one finished `daily_brief` or `weekly_brief` into one audience-specific digest;
- emit one profile-specific output plus `run_manifest`.

Allowed inputs:

- one `daily_brief` or `weekly_brief`
- one stakeholder profile
- no other runtime artifacts are required

Forbidden inputs:

- raw candidates
- `./.state/raw/`
- `./.state/articles/`
- full article bodies
- source adapters
- the whole profile set at once
- long-form human reference material
- evaluation datasets and goldens

This mode is downstream only.
Keep personalization out of the base daily and weekly critical path.
Do not re-run source discovery or full enrichment here.
