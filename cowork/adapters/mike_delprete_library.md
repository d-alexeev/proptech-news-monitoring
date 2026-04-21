# Adapter: Mike DelPrete — Articles

Applies to:

- `mike_delprete`

Use this adapter for Mike DelPrete's independent proptech analysis.

## Fetch strategy

Use the chronological article index on the main Squarespace site as the primary
discovery surface:

- landing URL: `https://www.mikedp.com/articles`
- fetch_strategy: `html_scrape`
- tool: `tools/rss_fetch.py --kind http` or any static fetcher; a plain Mozilla
  UA is sufficient, no JS required.

The former surface `https://library.mikedp.com/` is now a thin SPA shell
(~4KB rendered HTML) that routes to playlists/collections instead of a linear
dated article list. It must not be used for discovery.

## Rules

- discovery must parse the articles page for anchor hrefs matching the pattern
  `/articles/<YYYY>/<M>/<D>/<slug>` (note: month and day have no leading zeros,
  e.g. `/articles/2026/1/8/compasss-new-product-address-upon-request`);
- the URL path is the canonical source of the publish date — do not rely on
  visible-date text, which may be rendered post-load;
- the article slug is the initial title hint; resolve the real title from the
  article page's `<meta property="og:title">` in `scrape_and_enrich`;
- the site is Squarespace; article pages include `<meta property="og:title">`
  and `<meta property="article:published_time">` tags suitable for enrichment;
- `www.mikedp.com` also publishes podcast episodes and chart-only posts — the
  scoring stage should down-weight chart-only posts unless the accompanying
  commentary clearly discusses a peer product or market move;
- there is no RSS feed — `/feed`, `/feed.xml`, `/rss` all return 404;
- `library.mikedp.com` may still be fetched in `scrape_and_enrich` for
  long-form retrievals (e.g. podcast transcripts) if a specific item is
  referenced, but never as a discovery surface.

## Soft-fail detection

- if `html_scrape` returns 200 but fewer than 5 `/articles/<YYYY>/<M>/<D>/...`
  hrefs are found, emit `soft_fail=selector_miss` — the index template has
  probably been reorganized;
- if the most recent dated item is older than 60 days, emit
  `soft_fail=stale_source` with the item date as the detail so the runner can
  decide whether to skip the source for this cycle rather than keep re-fetching
  a stale index;
- do not emit a `change_request` for a temporarily stale index (Mike posts
  irregularly — gaps of several weeks are normal).

## Notes

- cadence_hint in config should be `weekly_to_monthly`, not `twice_weekly` —
  2025 produced roughly one post every 2–4 weeks, not two per week;
- config currently declares `fetch_strategy: chrome_scrape`; recommend changing
  to `html_scrape` — chrome_scrape was the workaround for the library.mikedp.com
  SPA, which is no longer the primary surface.
