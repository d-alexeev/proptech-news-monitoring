# Mode Prompt: breaking_alert

Load shared context from:

- `cowork/shared/mission_brief.md`
- `cowork/shared/taxonomy_and_scoring.md`
- `cowork/shared/contracts.md`

Purpose:

- evaluate recent enriched items for immediate high-priority delivery;
- suppress obvious same-story follow-up noise;
- emit alert payload and `run_manifest`.

Allowed inputs:

- recent enriched items
- recent `story_brief`
- alert thresholds

Forbidden inputs:

- raw candidates
- full article bodies
- whole daily or weekly archive
- long-form human reference material
- evaluation datasets and goldens
- stakeholder profiles

This mode is alert-only.
Do not build a daily or weekly digest here.
