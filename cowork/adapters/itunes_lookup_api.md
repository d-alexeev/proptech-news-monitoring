# Adapter: iTunes Lookup API

Applies to:

- `zillow_ios`
- `rightmove_ios`

Use this adapter for Apple App Store release monitoring.

Rules:

- use the configured `itunes_api_url` lookup endpoint;
- do not use customer review RSS JSON endpoints because they return empty or unusable feeds for this workflow;
- parse the response defensively because control characters can appear in the payload;
- prefer text extraction or regex-style field capture for version, release date, and release notes.

Notes:

- storefront-specific lookup URLs matter and must come from source config;
- this adapter is about metadata extraction, not app review sentiment analysis.
