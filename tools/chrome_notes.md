# Browser fallback contract

Browser access is a narrow runner fallback for public pages that need a
rendered UI surface. It is not the default fetch path and must not replace
`rss`, `html_scrape`, or `itunes_api` when static fetch is sufficient.

## Operational interface

For local Codex/Cowork runs, the operational browser interface may be either:

- the Codex in-app browser, when the operator is reviewing or manually
  exercising a public page; or
- Claude in Chrome / an equivalent browser connector, when it is available in
  the active Cowork session.

These interactive interfaces are for local operator-assisted runs only. A
cron/server runner must not depend on a logged-in desktop Chrome session. A
future headless runner may use Playwright, Puppeteer, or another server-safe
browser implementation, but it must emit the same JSON-shaped result described
below and preserve the same eligibility rules.

No RT-M3 implementation adds browser automation scripts. This document defines
the contract and review boundary for later runner implementations.

## Eligibility

Browser fallback is allowed only when one of these is true:

- the source config has `fetch_strategy: chrome_scrape`; or
- the source has an explicit adapter fallback case saying static HTTP was tried
  or is known to be insufficient for that specific source surface.

Browser fallback is not allowed for:

- `fetch_strategy: rss`, `html_scrape`, or `itunes_api` sources while their
  static/API path is sufficient;
- sources with `fetch_strategy: blocked` and
  `blocked_mode: manual_only_permanent`;
- login, CAPTCHA, paywall bypass, proxy rotation, or gated/manual-only flows;
- broad crawling beyond configured landing URLs or adapter-approved links.

For `manual_only_permanent`, the runner skips fetch entirely and follows
`cowork/adapters/blocked_manual_access.md`: no browser attempt, no automated
workaround, and only the configured manual-intake reminder behavior.

## Output shape

The browser runner emits one JSON document. It does not write `.state/` and does
not decide shortlist, digest, full-text, or change-request outcomes.

```json
{
  "fetched_at": "2026-05-04T09:30:00Z",
  "results": [
    {
      "source_id": "similarweb_global_real_estate",
      "url": "https://www.similarweb.com/website/zillow.com/#overview",
      "kind": "browser",
      "http": {
        "status_like": 200,
        "content_type": "text/html",
        "source": "browser_observation"
      },
      "final_url": "https://www.similarweb.com/website/zillow.com/#overview",
      "elapsed_ms": 1840,
      "text": "Visible page text or compact listing snippets...",
      "html": null,
      "items": [],
      "error": null,
      "soft_fail": null,
      "soft_fail_detail": null,
      "browser": {
        "interface": "codex_in_app_browser",
        "mode": "interactive",
        "headless": false,
        "user_agent_family": "chrome",
        "network_events_available": false
      }
    }
  ]
}
```

Field notes:

- `url` is the configured or adapter-approved URL requested.
- `final_url` records redirect/canonical location when the interface exposes it.
- `http.status_like` is best-effort browser metadata. Use `null` when the
  browser cannot observe an HTTP-like status.
- `text` should be visible listing text, snippets, titles, release metadata, or
  other discovery-mode content. Keep it compact.
- `html` is optional and should be included only when visible text is
  insufficient for adapter review. Prefer relevant HTML fragments over full page
  dumps.
- `items` defaults to `[]`; source-specific normalization belongs in the
  runner/adapter layer, not the browser interface.
- `soft_fail` uses the same stable labels as `tools/rss_fetch.py` where
  practical: `blocked_or_paywall`, `rate_limited`, `origin_blocked`, `anti_bot`,
  or `timeout`.
- `soft_fail_detail` records the observed reason, for example
  `captcha_or_human_check_visible`, `login_required`, or `http_429_observed`.

Manual-only sources are not browser results. Record them in the run manifest or
manual intake reminder flow described by `cowork/adapters/blocked_manual_access.md`.

If a browser-eligible public page is blocked, the runner returns a soft-fail
result with available provenance. It must not continue into login, CAPTCHA,
paywall, or proxy workarounds.

## Full-text boundary

`monitor_sources` and other discovery flows use browser output only for listing
text, snippets, visible metadata, and adapter-specific discovery evidence.

Full article body text remains a special artifact. It is allowed only in
`scrape_and_enrich`, only for shortlisted items from the current run, and only
under that mode's body-status policy (`full`, `snippet_fallback`, or
`paywall_stub`).

## Source strategy table

Static review target: `config/runtime/source-groups/daily_core.yaml` and
`config/runtime/source-groups/weekly_context.yaml`.

| source_id | group | fetch_strategy | Primary runner path | Browser use |
|---|---|---|---|---|
| `aim_group_real_estate_intelligence` | daily_core | `rss` | `tools/rss_fetch.py --kind rss` | Not allowed while RSS works. |
| `onlinemarketplaces` | daily_core | `chrome_scrape` | Browser fallback contract | Allowed for configured public listing page. |
| `mike_delprete` | daily_core | `html_scrape` | `tools/rss_fetch.py --kind http` | Adapter fallback only if static page becomes insufficient. |
| `zillow_newsroom` | daily_core | `rss` | `tools/rss_fetch.py --kind rss` | Not allowed for blocked PerimeterX page; use RSS config. |
| `costar_homes` | daily_core | `rss` | `tools/rss_fetch.py --kind rss` | Not allowed while RSS works. |
| `redfin_news` | daily_core | `rss` | `tools/rss_fetch.py --kind rss` | Not allowed while RSS works. |
| `rea_group_media_releases` | daily_core | `html_scrape` | `tools/rss_fetch.py --kind http` | Adapter fallback only; static HTTP is primary. |
| `rightmove_plc` | daily_core | `html_scrape` | `tools/rss_fetch.py --kind http` | Adapter fallback only; static HTTP is primary. |
| `similarweb_global_real_estate` | daily_core | `chrome_scrape` | Browser fallback contract | Allowed for configured public overview pages. |
| `property_portal_watch` | weekly_context | `chrome_scrape` | Browser fallback contract | Allowed for configured public listing page. |
| `inman_tech_innovation` | daily_core | `rss` | `tools/rss_fetch.py --kind rss`; Stage B uses `tools/article_fetch.py` | Discovery browser use is not allowed while RSS works; Stage B may use public browser fallback only to retain visible article text after static article fetch is blocked. |
| `similarweb_country_real_estate` | weekly_context | `chrome_scrape` | Browser fallback contract | Allowed for configured public overview pages. |
| `zillow_ios` | weekly_context | `itunes_api` | `tools/rss_fetch.py --kind http` | Not allowed; use iTunes lookup JSON. |
| `zillow_android` | weekly_context | `chrome_scrape` | Browser fallback contract | Allowed for configured public Google Play page. |
| `rightmove_ios` | weekly_context | `itunes_api` | `tools/rss_fetch.py --kind http` | Not allowed; use iTunes lookup JSON. |
| `rightmove_android` | weekly_context | `chrome_scrape` | Browser fallback contract | Allowed for configured public Google Play page. |

## Runner protocol

For `monitor_sources`:

1. Resolve `source_id` and `fetch_strategy` from the source-group config.
2. Use `tools/rss_fetch.py` for `rss`, `html_scrape`, and `itunes_api`.
3. Use browser fallback only for `chrome_scrape` or explicit adapter-approved
   fallback cases.
4. For `blocked` + `manual_only_permanent`, skip fetch entirely and follow the
   manual intake policy.
5. On browser soft-fail, return the JSON result with `soft_fail` and
   `soft_fail_detail`; the runtime layer decides whether adapter policy requires
   a `change_request`, manual reminder, retry, or snippet fallback.

No browser test or runner path may automate login, CAPTCHA, paywall, proxy, or
manual-only source flows.
