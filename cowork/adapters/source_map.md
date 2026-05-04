# Source Adapter Resolution

Use this file to resolve `source_id -> adapter file` for the current run.

Resolution rules:

- resolve adapters only for source IDs present in the current source group or shortlist;
- load the unique adapter files referenced by those source IDs;
- do not load the whole adapter directory by default;
- `none` means the source follows baseline runtime behavior and needs no adapter layer.

| source_id | adapter | note |
| --- | --- | --- |
| `aim_group_real_estate_intelligence` | `none` | baseline RSS |
| `onlinemarketplaces` | `cowork/adapters/onlinemarketplaces_family.md` | HTML listing page; RSS endpoints redirect to subscription page |
| `mike_delprete` | `cowork/adapters/mike_delprete_library.md` | dated library listing; public content backend has source-specific caveats |
| `zillow_newsroom` | `cowork/adapters/zillow_newsroom_html.md` | HTML scrape with non-browser user agent rules |
| `costar_homes` | `none` | baseline RSS |
| `redfin_news` | `none` | baseline RSS |
| `rea_group_media_releases` | `none` | baseline static HTML media releases page |
| `rightmove_plc` | `cowork/adapters/rightmove_plc.md` | empty RSS; scrape investor page instead |
| `similarweb_global_real_estate` | `cowork/adapters/similarweb_site_overview.md` | use site overview pages, not gated category rankings |
| `property_portal_watch` | `cowork/adapters/onlinemarketplaces_family.md` | same publisher family and listing-style discovery |
| `inman_tech_innovation` | `none` | baseline RSS with analysis-stage filtering |
| `similarweb_country_real_estate` | `cowork/adapters/similarweb_site_overview.md` | use site overview pages, not gated category rankings |
| `zillow_ios` | `cowork/adapters/itunes_lookup_api.md` | Apple lookup API; customer review feed is unusable |
| `zillow_android` | `cowork/adapters/google_play_app_page.md` | Google Play page scrape only |
| `rightmove_ios` | `cowork/adapters/itunes_lookup_api.md` | Apple lookup API; storefront-specific lookup URL |
| `rightmove_android` | `cowork/adapters/google_play_app_page.md` | Google Play page scrape only |
