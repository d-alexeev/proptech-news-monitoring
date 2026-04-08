# Mode Prompt: build_daily_digest

Load shared context from:

- `cowork/shared/mission_brief.md`
- `cowork/shared/taxonomy_and_scoring.md`
- `cowork/shared/contracts.md`

Purpose:

- select daily top items and weak signals from compact artifacts;
- suppress redundant repeats using recent compact digest memory;
- add contextual continuation where justified from `story_brief`, not from article bodies;
- render the human-readable daily digest;
- emit a structured `daily_brief` for weekly synthesis and stakeholder fanout.

Allowed inputs:

- enriched items for the daily window
- recent `story_brief`
- recent `daily_brief`
- current-run selection outputs
- delivery profile metadata from schedule bindings

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
Render markdown and `daily_brief` from selected compact records only.
Do not read past markdown digests or `./.state/articles/` in this mode.
Do not perform downstream personalization here.
