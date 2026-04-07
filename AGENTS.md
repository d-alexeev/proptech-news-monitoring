# AGENTS.md

## Purpose
This repository contains an LLM-driven monitoring agent operated by `Claude Cowork`.
Most changes here are not traditional code changes: they affect prompts, runtime instructions, config, state contracts, source adapters, and output behavior.

Changes must be made safely, incrementally, and in a way that is reviewable from artifacts, not just implementation intent.

For substantial tasks, completeness, traceability, and verifiability matter more than speed.

## What Counts As a Change
In this repo, the following all count as behavior changes:
- prompt changes
- `Claude Cowork` mode or job changes
- source config changes
- state schema changes
- digest format changes
- selection/scoring/context rules changes
- migration/backfill/compatibility changes

Do not treat prompt-only or config-only edits as “just docs” if they change agent behavior.

## Task Size Rules
Use the lightweight path for trivial tasks.
Use the full planning path for substantial tasks.

### Trivial tasks
Examples:
- typo fixes
- wording-only docs edits
- formatting cleanup
- isolated non-behavioral file organization
- narrow fixes that do not change runtime behavior, state shape, prompt behavior, or output contracts

For trivial tasks:
- `PLANS.md` is not required
- keep the diff narrow
- report clearly what changed and what did not

### Substantial tasks
A task is substantial if it changes any of:
- architecture
- runtime mode behavior
- prompt behavior
- source handling
- output shape
- state layout or schema
- migration/backfill expectations
- compatibility guarantees
- user-visible digest behavior

For substantial tasks:
- create or update `PLANS.md` before implementation
- do not start coding or editing runtime artifacts until requirements are mapped

## General Working Rules
- Do not implement a substantial feature in one pass unless explicitly instructed.
- Prefer small, reviewable, shippable increments over large diffs.
- Keep changes focused. Do not refactor unrelated parts of the repo.
- Preserve backward compatibility unless the task explicitly allows breaking changes.
- Never silently skip requirements.
- If something is unclear, blocked, risky, deferred, or only partially complete, state it explicitly.
- Do not claim completion if acceptance criteria are not met.
- If code, prompts, config, and docs disagree, either align them or explicitly call out the mismatch.

## Repo-Specific Rules
- Treat `Claude Cowork` jobs/modes as first-class runtime interfaces.
- Treat prompt files, config files, adapter files, and `.state` schemas as production behavior.
- Do not let large human docs become runtime dependencies.
- Prefer compact runtime briefs and explicit contracts over long narrative instructions.
- Keep source-specific operational knowledge in small adapter files rather than in large general docs.
- Avoid duplicating the same runtime rule across multiple files unless one is explicitly an export or human-facing summary.
- If a change affects selection, scoring, contextualization, weekly synthesis, personalization, or alerting, treat it as behaviorally significant.

## Planning Rules
For any substantial task:

1. Break the work into milestones.
2. Each milestone should be small enough to review independently.
3. For each milestone, define:
   - goal
   - scope
   - likely files/artifacts to change
   - dependencies
   - risks
   - acceptance criteria
   - tests or verification steps
   - explicit non-goals
4. Add a coverage matrix mapping every original requirement to at least one milestone.
5. Do not start implementation until all requirements are either:
   - mapped to milestones
   - explicitly blocked
   - explicitly unclear and requiring decision

## Milestone Discipline
- Implement one milestone at a time unless explicitly instructed otherwise.
- Before editing, restate the current milestone acceptance criteria.
- Limit the diff to the current milestone.
- If hidden work appears and materially changes scope, update `PLANS.md` before continuing.
- Do not drift into future milestones.
- If implementation diverges from the plan, explain why and update the plan.

## Validation Rules
This repo is not code-heavy, so validation must match the actual artifact type.

For each milestone, run the relevant checks for touched areas when applicable:

### For prompt or instruction changes
- fixture-based input/output review
- sample run or dry-run review
- contract validation against expected inputs and outputs
- regression comparison against prior expected behavior when practical

### For config or state changes
- schema validation
- sample artifact generation
- compatibility review
- migration/backfill impact review

### For output-format changes
- sample digest rendering review
- downstream consumer compatibility review
- parity check against expected structure

### For code changes, if any exist
- tests
- lint
- type checks
- build checks
- only for touched and relevant areas

If a check is not run, explain why.
If a test or fixture should exist but does not, add it when practical.
If adding it is not practical, explain why.

## Runtime Safety Rules
- Do not overwrite or revert unrelated user changes.
- Do not make destructive changes without explicit approval.
- If the worktree is dirty, work around existing changes rather than resetting them.
- Do not break existing run artifacts or state readers unless the task explicitly allows it.
- If changing state shape, define migration notes and compatibility expectations.
- If changing a runtime contract, update every producer/consumer relationship in the plan.

## Full-Text and Context Rules
For this project specifically:
- full article text is a special artifact, not a default input
- do not expand full-text usage into unrelated modes unless explicitly required
- if a change causes more runtime context to be loaded, call that out explicitly
- if a change alters which files a `Claude Cowork` mode loads, document the new runtime footprint

## Documentation Rules
When relevant, update:
- runtime docs
- config docs
- state schema notes
- migration notes
- operator notes or runbook
- prompt documentation
- compatibility notes

If a schema, prompt contract, mode behavior, config field, env var, or output behavior changes, document it.

## End-of-Milestone Report
At the end of each milestone, provide:

1. Summary of what was implemented
2. List of changed files
3. Acceptance criteria status
   - pass/fail per criterion
4. Validation results
   - fixtures
   - dry-runs
   - schema checks
   - tests/lint/typecheck/build if applicable
5. Incomplete items
6. Risks and follow-up work
7. Whether the milestone is actually complete

## Completion Audit
When a substantial multi-milestone feature is finished, produce a completion audit.
It may be a file such as `COMPLETION_AUDIT.md` or an equivalent structured final report if a file is unnecessary.

The audit must compare:
- original requirements
- implemented requirements
- partially implemented requirements
- missing requirements
- known follow-ups
- migration or compatibility caveats

For small tasks, a file is not required; a structured final report is enough.

## Preferred Behavior Under Ambiguity
If a choice affects:
- architecture
- runtime contracts
- mode boundaries
- migration
- compatibility
- user-visible digest behavior

then:
- make the smallest safe assumption
- record it in `PLANS.md`
- call it out in the implementation report

Do not hide uncertainty.

## Preferred Output Style
Be concise but explicit.
Use clear status language.
Do not say something is done if it is only partially done.
Do not present planned work as implemented work.
