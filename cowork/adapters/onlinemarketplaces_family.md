# Adapter: OnlineMarketplaces Family

Applies to:

- `onlinemarketplaces`
- `property_portal_watch`

Use this adapter for listing-style discovery on OnlineMarketplaces-owned pages.

Rules:

- treat the configured landing page as the discovery surface;
- do not attempt RSS endpoints such as `/feed/`, `/?feed=rss2`, or `/articles/feed/`;
- ignore subscription or marketing pages such as `/rss-feed/`;
- extract article or interview URLs, titles, and visible dates from listing cards or anchors;
- keep the item URL canonical and strip tracking parameters when present.

Notes:

- `property_portal_watch` is handled through OnlineMarketplaces topic pages rather than a separate feed;
- this adapter provides discovery guidance only and does not change the configured fetch strategy.
