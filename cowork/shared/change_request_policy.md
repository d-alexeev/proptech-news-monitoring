# Shared Policy: External Change Requests

## Purpose

This policy defines what an externally running agent may do when it encounters
source, scrape, or adapter problems, and what must be escalated back into the
Codex-managed repository as a `change_request`.

## Ownership Boundary

The repository under git is the only master source of truth for:

- prompts
- mode instructions
- runtime config
- source adapters
- contracts and schemas
- planning and policy files

The external runner may observe runtime failures, collect evidence, and emit a
`change_request`, but it must not persist changes to the files above.

## Mandatory `change_request` Triggers

The external runner must create a `change_request` when any of the following
occur:

1. `scrape_failure`
   The source cannot be fetched or normalized using the currently declared
   adapter and allowed fallback behavior.

2. `blocked_or_manual_source`
   The source requires manual access, anti-bot handling, login, or another step
   outside the current declared runtime path.

3. `adapter_gap`
   The source is reachable, but the current adapter/config/prompt layer is
   insufficient to parse or classify it correctly.

4. `persistent_workaround_required`
   The agent found a workaround that could help future runs, but using it again
   would require a persistent repo change.

## Allowed Temporary In-Run Workarounds

The external runner may use a temporary workaround only when all of the
following are true:

- the workaround is limited to the current run;
- it does not modify prompts, config, adapters, contracts, or docs on disk;
- it stays within behavior already allowed by the current mode contract;
- it is reported in the resulting `change_request` if the issue is not fully
  resolved by the declared runtime path.

Examples of allowed temporary in-run behavior:

- retrying the same declared fetch strategy;
- falling back to a contract-allowed snippet or stub outcome;
- skipping a source for the current run when the contract already permits it.

## Forbidden Workarounds

The external runner must not:

- edit prompt, config, adapter, contract, or policy files;
- create hidden local overrides that change future runtime behavior;
- change thresholds, source lists, taxonomy, or schedules on the fly;
- treat a discovered workaround as canonical without a reviewed repo change;
- silently suppress a recurring failure without emitting a `change_request`.

## Required Escalation Outcome

When a problem cannot be resolved inside the declared runtime path, the external
runner must:

1. stop short of persistent self-modification;
2. capture the failure context and evidence;
3. emit a `change_request` for Codex-side triage and planning.

The detailed `change_request` schema, state path, and lifecycle are defined in
later follow-up milestones. This policy only fixes the behavior boundary and the
minimum trigger classes.

## Responsibilities

External runner responsibilities:

- detect the failure;
- capture evidence;
- record any temporary workaround used in the current run;
- emit a `change_request`;
- leave source-of-truth files unchanged.

Codex-side responsibilities:

- triage the `change_request`;
- decide whether prompts, adapters, config, contracts, or docs must change;
- plan the fix as a reviewable change;
- validate and commit the approved change in this repository.
