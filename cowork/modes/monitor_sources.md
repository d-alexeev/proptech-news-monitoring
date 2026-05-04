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

Source runner failure handling:

- If the scheduled wrapper provides runner source discovery prefetch artifacts,
  read the prefetch summary and fetch result as the static source runner output.
  Do not re-run static network fetches for those sources from inside the inner
  `codex exec` sandbox.
- Treat prefetch artifacts as evidence references, not prompt context dumps.
  For large `kind=http` bodies, summarize only adapter-relevant listing markers,
  titles, links, dates, and compact snippets. Do not copy full listing HTML into
  raw candidate reasoning notes.
- Use configured `chrome_scrape` source output only when the wrapper provides a
  browser artifact path from prefetch summary field `browser_result_path`. The
  browser artifact must follow `tools/chrome_notes.md` and may contribute only
  visible listing/snippet/metadata evidence, not full article bodies.
- If the browser artifact is absent or reports
  `failure_class=browser_runtime_unavailable`, keep configured `chrome_scrape`
  sources as `not_attempted` and record the missing runner capability.
- Treat `tools/rss_fetch.py` output `batch_status=environment_failure` with
  `failure_class=global_dns_resolution_failure` as a runner/network failure,
  not as a canonical empty source result.
- When the source runner reports global DNS failure across all fetchable sources,
  or across all fetchable sources except a known `costar_homes` timeout, emit a
  run manifest with failure status and enough diagnostic detail for operator
  follow-up; do not emit clean empty raw/shortlist shards as if source discovery
  succeeded.
- Preserve source-level outcomes in each result. A single source `soft_fail`,
  including `costar_homes` `soft_fail=timeout`, remains a source-level soft
  failure unless the batch also reports a global resolver failure.
- Do not use web search or ad hoc web fallback as a canonical replacement for
  configured source discovery. If fallback evidence is operator-supplied, mark
  it non-canonical or partial in the run manifest.
