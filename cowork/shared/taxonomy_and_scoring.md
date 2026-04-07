# Shared Taxonomy And Scoring

Use the following default scoring lens for relevance:

- `marketplace_relevance`: `35%`
- `event_scale`: `25%`
- `portability_to_avito`: `20%`
- `urgency`: `10%`
- `novelty`: `10%`

Default thresholds:

- main digest candidate: `priority_score >= 55`
- breaking alert candidate: `priority_score >= 85`
- weak signal band: below main digest threshold but still decision-useful

Default topic groups:

- `product`: launches, updates, AI search, recommendations, listing quality, pre-market, mobile
- `commercial`: monetization, paid visibility, subscriptions, agent relations, lead qualification
- `strategic`: M&A, competition, market dynamics, regulation, funding
- `tech`: AI/ML, data infrastructure, trust and safety, transaction tech
- `macro`: consumer behaviour, macro housing signals

Always prefer a compact, controlled taxonomy over free-form tags.
Detailed schemas and exact artifact fields belong in contract files, not in mode prompts.
