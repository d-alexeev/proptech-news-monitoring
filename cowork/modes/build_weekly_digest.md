# Mode Prompt: build_weekly_digest

Load shared context from:

- `cowork/shared/mission_brief.md`
- `cowork/shared/taxonomy_and_scoring.md`
- `cowork/shared/contracts.md`

Purpose:

- aggregate the current week from compact daily artifacts;
- derive higher-level weekly themes and trends;
- emit weekly markdown digest, `weekly_brief`, and `run_manifest`.

Allowed inputs:

- current-week `daily_brief`
- prior `weekly_brief`

Forbidden inputs:

- raw candidates
- full article bodies
- full digest archive
- long-form human reference material
- evaluation datasets and goldens
- stakeholder profiles

This mode should not depend on the full historical digest corpus.
Use compact weekly memory, not raw archives.
