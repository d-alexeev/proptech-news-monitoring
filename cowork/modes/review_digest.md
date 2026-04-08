# Mode Prompt: review_digest

Load shared context from:

- `cowork/shared/mission_brief.md`
- `cowork/shared/contracts.md`

Purpose:

- review a produced digest as a QA step;
- identify missed signals, duplication risk, weak reasoning, and source gaps;
- emit a grouped QA review report with next-run recommendations.

Allowed inputs:

- digest markdown
- kept and dropped compact artifacts
- `daily_brief` or `weekly_brief`
- `run_manifest`

Forbidden inputs:

- raw candidates
- full article bodies
- `./.state/articles/`
- source adapters
- stakeholder profiles
- long-form human reference material
- evaluation datasets and goldens

Do not rewrite the digest in this mode.
Group findings under actionable categories rather than editorial prose.
Do not deliver anything to Telegram from this mode.
The output is a QA assessment, not a replacement digest.
