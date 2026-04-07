# Adapter: Google Play App Page

Applies to:

- `zillow_android`
- `rightmove_android`

Use this adapter for Google Play product-release signals.

Rules:

- use the configured Google Play app page as the discovery and extraction surface;
- do not assume a public API exists for version or release notes;
- extract visible app metadata such as version, updated date, release-note text, and product description when available;
- treat page structure as UI-driven and prefer resilient text extraction over brittle selectors.

Notes:

- this adapter is intentionally narrow and does not introduce unofficial APIs;
- keep extraction focused on product-change signals rather than ratings or review mining.
