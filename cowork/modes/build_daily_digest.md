# Mode Prompt: build_daily_digest

Load shared context from:

- `cowork/shared/mission_brief.md`
- `cowork/shared/taxonomy_and_scoring.md`
- `cowork/shared/contracts.md`

Purpose:

- select daily top items and weak signals from compact artifacts;
- add contextual continuation where justified;
- emit daily markdown digest, `daily_brief`, and `run_manifest`.

Allowed inputs:

- enriched items for the daily window
- recent `story_brief`
- recent `daily_brief`

Forbidden inputs:

- raw candidates
- full article bodies
- long-form human reference material
- evaluation datasets and goldens
- stakeholder profiles

This mode should work from compact artifacts only.
Do not perform downstream personalization here.
