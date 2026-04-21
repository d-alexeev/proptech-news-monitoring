# Adapter: Rightmove PLC

Applies to:

- `rightmove_plc`

Use this adapter for Rightmove investor and regulatory news discovery.

## Fetch strategy

Use static HTML on the PLC homepage as the discovery surface:

- landing URL: `https://plc.rightmove.co.uk/`
- fetch_strategy: `html_scrape`
- tool: `tools/rss_fetch.py --kind http` or any static fetcher; the page returns
  a fully rendered 200 with a standard Mozilla UA — no JS required for discovery.

The page is a WordPress SPA (Redwire theme) that renders all investor content
under hash anchors (`#regulatory_news`, `#results`, `#market_data`), but the
underlying HTML already contains the regulatory-news anchor list and dated PDF
links inline, so we do not need to execute JS.

## Rules

- do not rely on `plc.rightmove.co.uk/feed/` as a content source — the WordPress
  RSS exists and returns a valid XML document, but with zero items (the PLC site
  does not syndicate RNS announcements through it);
- do not rely on the chrome_scrape path as a primary strategy — a browser visit
  to `/` sometimes resolves as an error frame ("Frame with ID 0 is showing
  error page") when the Chrome profile is flagged, but static HTTP works fine;
- discovery must parse the homepage HTML for:
  - anchor hrefs matching
    `plc.rightmove.co.uk/content/uploads/<YYYY>/<MM>/*RNS*.pdf` (case-insensitive)
    — these are the dated RNS PDFs;
  - a single `polaris.brighterir.com/public/rightmove_plc/news/html_rns_announcements/story/<id>`
    link — this is the latest announcement in the third-party IR platform;
- treat the PDF filename stem as the initial title (e.g.
  `251106-RNS-Trading-Update` → "RNS Trading Update"); use `scrape_and_enrich`
  to download the PDF and extract a cleaner title + date if needed;
- cadence is quarterly/half-year + ad-hoc — expect 4–8 items per year, so an
  empty run is normal and must not emit a change_request;
- treat the source as lower-yield because overlapping coverage often appears in
  industry sources first.

## Soft-fail detection

- if `html_scrape` returns a Chrome "error frame" marker in the body (the
  runner's chrome-bridge variant), emit `soft_fail=chrome_nav_error` and retry
  once as `http_scrape` with a plain Mozilla UA before giving up;
- if the static HTTP response is 200 but contains zero `*RNS*.pdf` hrefs, emit
  `soft_fail=selector_miss` with the current timestamp so a site re-theme can
  be caught quickly.

## Notes

- config currently declares `fetch_strategy: chrome_scrape`; recommend changing
  to `html_scrape` (static HTTP is sufficient and faster);
- the Brighter IR "story" link is an option for richer historical discovery,
  but the Polaris page is client-rendered (5.6KB shell HTML, content loaded via
  JS) — parsing it would require chrome_scrape, which is why we prefer the
  inline PDFs on the PLC homepage;
- there is no declared public JSON API on the site; WP-JSON endpoints for the
  PLC domain require auth (`/wp-json/wp/v2/pages/132` → 401).
