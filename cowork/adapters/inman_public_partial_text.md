# Inman Public Partial Text Adapter

Use RSS/feed discovery as the primary discovery path for `inman_tech_innovation`.

Stage B article prefetch rules:

- do not automate login, subscription, CAPTCHA, paywall bypass, cookies, or proxy rotation;
- if static HTTP returns a source-level block but a public headless page observation returns normal HTTP success and visible article text, retain only that visible article text as `snippet_fallback`;
- if an Inman article page returns normal HTTP success and contains visible article text plus subscription/login UI, retain only the visible article text as `snippet_fallback`;
- write the retained partial text as a local article artifact only when the fetch result marks `soft_fail_detail = public_partial_text_extracted`;
- keep `body_status_hint = snippet_fallback` for this case, even when the visible text is long enough to summarize;
- if the page has no reliable visible article text, keep `body_status_hint = paywall_stub` and do not emit evidence points from the article body.

This adapter preserves public evidence without claiming credentialed or full
article access.
