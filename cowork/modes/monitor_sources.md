# Mode Prompt: monitor_sources

Load shared context from:

- `cowork/shared/mission_brief.md`
- `cowork/shared/taxonomy_and_scoring.md`
- `cowork/shared/contracts.md`
- `cowork/shared/change_request_policy.md`
- `cowork/adapters/source_map.md` when any configured `source_id` resolves to an adapter

Purpose:

- discover candidate items from configured sources;
- perform primary triage on titles, metadata, and snippets;
- emit `raw_candidate` and `shortlisted_item` artifacts plus `run_manifest`.

Allowed inputs:

- source-group config
- runtime thresholds
- last checkpoint
- recent story index
- only the adapter files resolved for the current source IDs

Outputs:

- `./.state/raw/{run_date}/{run_id}.json`
- `./.state/shortlists/{run_date}/{run_id}.json`
- `./.state/runs/{run_date}/{run_id}.json`
- optional `./.state/change-requests/{request_date}/{request_id}.json`

Forbidden inputs:

- long-form human reference material
- evaluation datasets and goldens
- full article bodies
- `./.state/articles/`
- stakeholder profiles
- whole digest archive

Do not fetch or read full article text in this mode.
Do not preload the whole adapter directory; resolve `source_id -> adapter` first.
Use checkpoints and the recent story index only for duplicate linkage and continuity hints.
Do not do final digest selection here.
If a source requires blocked/manual access or another persistent repo change, emit `change_request`.
Do not edit prompts, config, or adapters to work around the issue.
