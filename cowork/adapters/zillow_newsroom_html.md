# Adapter: Zillow Newsroom

Applies to:

- `zillow_newsroom`

## Fetch strategy

Use the Zillow Mediaroom RSS feed as the primary discovery surface:

- feed URL: `https://zillow.mediaroom.com/press-releases?pagetemplate=rss`
- fetch_strategy: `rss`
- tool: `tools/rss_fetch.py` with the default user agent (no special headers required)

The former path (`https://www.zillow.com/news/category/product-innovation/` as
an `html_scrape` target) is blocked by PerimeterX and returns a 403 `px-captcha`
body to both browser-style Chrome access and neutral RSS-reader user agents as
of 2026-04-21. That path must not be retried.

## Rules

- use the Mediaroom RSS feed for broad discovery, no full HTML scraping;
- article bodies may be fetched from `zillow.mediaroom.com/<slug>` in
  `scrape_and_enrich` only, not during discovery;
- keep scope to product, market, and company-policy items; exclude agent-hires
  and investor-relations routine filings unless they surface product signals;
- if the Mediaroom feed returns `soft_fail=blocked_or_paywall` or `timeout`, do
  not fall back to the `www.zillow.com/news/...` path — emit a `change_request`
  and continue the run without this source.

## Notes

- Mediaroom is Zillow's canonical press-release surface and is not behind
  PerimeterX;
- the old product-innovation category page was a useful topical filter but is
  no longer reachable by automation — topical filtering is now the enrich-stage
  classifier's job;
- if we ever need per-category filtering again, the Mediaroom site exposes
  `?pagetemplate=rss` on category pages as well, e.g. `...category/products`.
