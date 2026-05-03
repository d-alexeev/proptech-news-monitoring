# RT-M7 Live Scrape Test Report

Run date: 2026-05-04 Europe/Moscow

Scope: bounded live discovery/metadata checks for all configured `daily_core`
and `weekly_context` sources after RT-M2 through RT-M6 passed offline validation.

Non-goals observed:

- no Telegram delivery;
- no login, CAPTCHA, paywall bypass, proxy rotation, or browser-safety bypass;
- no source config, adapter, prompt, or runtime contract fixes during the live test;
- no full article body fetch during discovery checks.

## Procedure

1. Ran the RT-M6 offline validator suite before the live test.
2. Ran the static/RSS/API sources through `tools/rss_fetch.py`.
3. Ran configured `chrome_scrape` sources through the Codex in-app browser
   surface using the RT-M3 browser contract.
4. Kept `rea_group_investor_centre` as blocked/manual and did not fetch it.
5. Did not run enrichment/full-text checks. No PDF or article body extraction
   was performed in RT-M7.

The first static fetch batch failed inside the default sandbox because DNS
resolution was blocked. The same bounded batch was rerun with approved network
access. That first failure is excluded from source health classification because
it was an environment constraint, not a source response.

## Source Results

| Source | Group | Primary Tool Path | URL Used | Status | Soft Fail | Discovery Sufficient | Outcome |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `aim_group_real_estate_intelligence` | `daily_core` | HTTP/RSS fetcher | `https://aimgroup.com/feed/` | `pass` | null | yes | RSS 200, 30 items. First item was a non-real-estate marketplace story, so downstream scoring still needs normal relevance filtering. |
| `onlinemarketplaces` | `daily_core` | Browser fallback | `https://www.onlinemarketplaces.com/property-portal-insights/` | `pass` | null | yes | Browser page loaded with title `Property Portal Insights | Online Marketplaces`; visible listing text contained configured markers. |
| `mike_delprete` | `daily_core` | HTTP/RSS fetcher | `https://www.mikedp.com/articles` | `pass` | null | yes | Static HTTP 200. Listing HTML was available, but body was large at about 656k chars. |
| `zillow_newsroom` | `daily_core` | HTTP/RSS fetcher | `https://zillow.mediaroom.com/press-releases?pagetemplate=rss` | `pass` | null | yes | RSS 200, 5 items. |
| `costar_homes` | `daily_core` | HTTP/RSS fetcher | `https://investors.costargroup.com/rss/news-releases.xml` | `soft_fail` | `timeout` | no | Fetcher returned timeout after configured retry budget. Treat as transient unless repeated. |
| `redfin_news` | `daily_core` | HTTP/RSS fetcher | `https://www.redfin.com/news/feed/` | `pass` | null | yes | RSS 200, 6 items. |
| `rea_group_investor_centre` | `daily_core` | No fetch / manual intake policy | `https://www.rea-group.com/investor-centre/` | `blocked_manual` | null | n/a | Correctly not fetched because source is `manual_only_permanent`. |
| `rightmove_plc` | `daily_core` | HTTP/RSS fetcher | `https://plc.rightmove.co.uk/` | `pass` | null | yes | Static HTTP 200, about 286k chars, with RNS/PDF markers present for discovery. |
| `similarweb_global_real_estate` | `daily_core` | Browser fallback | `https://www.similarweb.com/website/zillow.com/#overview` | `pass` | null | yes | Browser page loaded and visible text contained `zillow.com`, `Similarweb`, and traffic markers. |
| `property_portal_watch` | `weekly_context` | Browser fallback | `https://www.onlinemarketplaces.com/topic/videos-vodcasts-interviews/conference/` | `pass` | null | yes | Browser page loaded with title `Conference Archives | Online Marketplaces`; visible listing text contained configured markers. |
| `inman_tech_innovation` | `weekly_context` | HTTP/RSS fetcher | `https://feeds.feedburner.com/inmannews` | `pass` | null | yes | RSS 200, 18 items. Inman is confirmed as a regular recurring scraping-analysis source. |
| `similarweb_country_real_estate` | `weekly_context` | Browser fallback | `https://www.similarweb.com/website/propertyguru.com.sg/#overview` | `pass` | null | yes | Browser page loaded with Similarweb overview text for `propertyguru.com.sg`. |
| `zillow_ios` | `weekly_context` | HTTP/RSS fetcher | `https://itunes.apple.com/lookup?id=310738695&country=us` | `pass` | null | yes | iTunes lookup HTTP 200 with `resultCount: 1`; app metadata and release notes available. |
| `zillow_android` | `weekly_context` | Browser fallback | `https://play.google.com/store/apps/details?id=com.zillow.android.zillowmap` | `pass` | null | yes | Google Play browser page loaded. Visible text contained Zillow app markers. |
| `rightmove_ios` | `weekly_context` | HTTP/RSS fetcher | `https://itunes.apple.com/lookup?id=323822803&country=gb` | `pass` | null | yes | iTunes lookup HTTP 200 with `resultCount: 1`; app metadata and release notes available. |
| `rightmove_android` | `weekly_context` | Browser fallback | `https://play.google.com/store/apps/details?id=com.rightmove.android` | `pass` | null | yes | Google Play browser page loaded. Visible text contained Rightmove/property markers. |

## Boundary Review

- `monitor_sources` boundary held: no article page body, PDF extraction, or
  full article text was fetched during the live test.
- Browser checks used public page navigation only. No clicks, forms, login,
  CAPTCHA solving, paywall interaction, or proxy behavior were attempted.
- `rea_group_investor_centre` was not fetched and remains covered by manual
  intake policy.
- No `.state/` artifacts were written in this milestone.

## Transient vs Persistent Findings

Transient or source-health findings:

- `costar_homes` timed out. This matches the already documented flaky-source
  pattern and should be retried in isolation before creating a persistent
  adapter/tooling change request.

Persistent follow-up candidates:

- `mike_delprete` static listing fetch returned a very large HTML body
  (~656k chars). This is not a full article body, but it is too large to be
  comfortable as direct LLM context. Proposed follow-up: add an optional
  `max_body_chars` or `body_preview_chars` path to `tools/rss_fetch.py` for
  discovery-mode HTTP fetches, with tests proving iTunes JSON and listing HTML
  remain usable.
- `rightmove_plc` static homepage returned a large HTML body (~286k chars).
  Proposed follow-up: reuse the same HTTP body preview/cap change and ensure
  adapter-level RNS/PDF marker detection still has enough context.
- Browser source checks passed through the in-app browser, but there is still no
  repeatable headless server browser implementation. Proposed follow-up for
  production scheduling: add a headless browser runner only if cron/server
  execution needs non-interactive browser-backed checks.

No immediate persistent `change_request` artifact was written because no
source produced a confirmed adapter/config/tooling gap requiring repository
changes before the next milestone. The follow-up candidates above are concrete
plan candidates for a post-RT-M7 hardening pass.

## Validation After Live Test

Offline validation after the live test:

- `python3 tools/validate_runtime_artifacts.py --check all`
- `python3 tools/test_validate_runtime_artifacts.py`
- `PYTHONPYCACHEPREFIX=.pycache-local python3 -m py_compile tools/rss_fetch.py tools/pdf_extract.py tools/validate_runtime_artifacts.py`

These checks passed after the report was written.

## RT-M7 Status

RT-M7 is complete for bounded live discovery/metadata testing. It does not
claim future source availability, production browser scheduling readiness, or
full enrichment coverage.
