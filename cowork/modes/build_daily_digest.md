# Mode Prompt: build_daily_digest

Load shared context from:

- `cowork/shared/mission_brief.md`
- `cowork/shared/taxonomy_and_scoring.md`
- `cowork/shared/contracts.md`

Purpose:

- select daily top items and weak signals from compact artifacts;
- suppress redundant repeats using recent compact digest memory;
- add contextual continuation where justified from `story_brief`, not from article bodies;
- prepare selection outputs for later digest rendering.

Allowed inputs:

- enriched items for the daily window
- recent `story_brief`
- recent `daily_brief`

Forbidden inputs:

- raw candidates
- shortlist shards
- full article bodies
- `./.state/articles/`
- digest markdown archive
- long-form human reference material
- evaluation datasets and goldens
- stakeholder profiles

This mode should work from compact artifacts only.
Use `recent daily_brief` for anti-repeat decisions and `story_brief.last_digest_refs` plus `story_brief.summary_line` for context.
Do not read past markdown digests or `./.state/articles/` in this mode.
Do not perform downstream personalization here.
