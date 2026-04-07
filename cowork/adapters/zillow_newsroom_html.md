# Adapter: Zillow Newsroom HTML

Applies to:

- `zillow_newsroom`

Use this adapter for the Zillow product-innovation newsroom category.

Rules:

- use the configured category URL as the discovery surface and keep scope limited to product innovation;
- do not try RSS discovery because `/news/feed/` redirects to HTML and the site exposes no usable feed;
- treat browser-style Chrome access as unreliable because PerimeterX can return `px-captcha` blocks;
- prefer neutral HTML fetching with a non-browser `RSS reader` style user agent;
- do not require `Accept-Encoding: gzip` handling assumptions from the caller;
- use article pages only after shortlist selection, not for broad discovery.

Notes:

- this adapter exists because the source is server-rendered but hostile to normal browser-style automation;
- keep press releases and non-product newsroom sections out of scope unless the source config changes.
