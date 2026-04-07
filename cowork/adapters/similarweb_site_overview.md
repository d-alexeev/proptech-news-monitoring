# Adapter: Similarweb Site Overview

Applies to:

- `similarweb_global_real_estate`
- `similarweb_country_real_estate`

Use this adapter for Similarweb traffic context sources.

Rules:

- do not use category ranking URLs that require login and return gated or empty states;
- use the configured individual site overview pages as the working surface;
- extract traffic trend, rank context, and competitor references from those public overview pages;
- treat these items as behavioral context, not company-authored announcements.

Notes:

- this adapter is for public site overview pages only;
- it does not authorize broad category scraping or login-dependent flows.
