# Mode Prompt: monitor_sources

Load shared context from:

- `cowork/shared/mission_brief.md`
- `cowork/shared/taxonomy_and_scoring.md`
- `cowork/shared/contracts.md`

Purpose:

- discover candidate items from configured sources;
- perform primary triage on titles, metadata, and snippets;
- emit `raw_candidate` and `shortlisted_item` artifacts plus `run_manifest`.

Allowed inputs:

- source-group config
- runtime thresholds
- last checkpoint
- recent story index

Forbidden inputs:

- long-form human reference material
- evaluation datasets and goldens
- full article bodies
- stakeholder profiles
- whole digest archive

Do not fetch or read full article text in this mode.
Do not do final digest selection here.
