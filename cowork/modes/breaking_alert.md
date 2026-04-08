# Mode Prompt: breaking_alert

Load shared context from:

- `cowork/shared/mission_brief.md`
- `cowork/shared/taxonomy_and_scoring.md`
- `cowork/shared/contracts.md`

Purpose:

- evaluate recent enriched items for immediate high-priority delivery;
- allow high-signal `weekly_context` items to alert immediately;
- suppress obvious same-story follow-up noise;
- emit alert payload and `run_manifest`.

Allowed inputs:

- recent enriched items
- recent `story_brief`
- alert thresholds
- schedule bindings for `breaking_alert`

Forbidden inputs:

- raw candidates
- `./.state/briefs/`
- full article bodies
- `./.state/articles/`
- whole daily or weekly archive
- long-form human reference material
- evaluation datasets and goldens
- stakeholder profiles

This mode is alert-only.
Do not depend on daily or weekly digest generation.
Do not build a daily or weekly digest here.
