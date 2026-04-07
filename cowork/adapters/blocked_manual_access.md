# Adapter: Blocked Manual Access

Applies to:

- `rea_group_investor_centre`

Use this adapter when the source is blocked by the Claude Cowork sandbox.

Rules:

- do not keep retrying automated fetches once the block is confirmed;
- mark the source as requiring manual user-side access or an out-of-band check;
- preserve the landing URL and source identity so the missing coverage is visible in run artifacts.

Notes:

- this adapter records an operational limitation, not a content pattern;
- it exists so blocked sources are handled explicitly instead of failing silently.
