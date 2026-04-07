# Adapter: Rightmove PLC

Applies to:

- `rightmove_plc`

Use this adapter for Rightmove investor and regulatory news discovery.

Rules:

- do not rely on `plc.rightmove.co.uk/feed/` as a content source because it is valid XML with zero items;
- use the investor landing page as the discovery surface;
- prefer regulatory-news anchors and announcement links over generic navigation text;
- treat the source as lower-yield because overlapping coverage often appears in industry sources first.

Notes:

- this adapter captures the empty-feed caveat and the correct discovery surface;
- it does not change the existing priority or fetch strategy in config.
