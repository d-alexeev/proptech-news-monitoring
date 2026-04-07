# Adapter: Mike DelPrete Library

Applies to:

- `mike_delprete`

Use this adapter when working with `library.mikedp.com`.

Rules:

- use the library landing page as the default discovery surface because it exposes dated items in a stable list;
- do not rely on legacy `mikedp.com` RSS or `/feed/` endpoints;
- when a mode explicitly supports deeper retrieval, prefer the known public content backend over brittle DOM-only extraction;
- for podcasts, prefer full content over short summaries when full content is available;
- if a retrieved body is only a stub, mark it as low-confidence rather than pretending full content exists.

Notes:

- this adapter records safe source-specific handling but does not override the current project config by itself;
- keep article and podcast handling within the current shortlist scope only.
