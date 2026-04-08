# Change Request Intake Workflow

## Purpose

This document defines the Codex-side workflow for turning an incoming
`change_request` into a reviewable repo commit in the git-managed master
source of truth.

## Inputs

- `change_request` artifact defined in `config/runtime/change_request_schema.yaml`
- external-runner policy in `cowork/shared/change_request_policy.md`
- relevant runtime contracts and fixtures

## Role Boundary

- The external runner may emit `change_request` artifacts and continue only with
  policy-allowed temporary in-run workarounds.
- The external runner must not edit prompts, config, adapters, contracts, or
  other source-of-truth files in this repo.
- Codex owns intake, triage, planning, implementation, validation, and commit.

## Workflow Stages

### 1. Intake

- Load the incoming `change_request`.
- Validate required fields, status, owner, and run-context references.
- Confirm that the request belongs to this repo and points to a real runtime
  contract, adapter, prompt, config file, or documentation surface.

### 2. Triage

- Classify the request by failure type and affected runtime area.
- Decide whether the request is actionable, needs clarification, or should be
  rejected with rationale.
- Determine whether the likely fix belongs in prompts, config, adapters,
  fixtures, contracts, or docs.

### 3. Plan Update

- Convert the accepted request into a reviewable implementation step in the
  active plan document.
- `suggested_target_files` are hints only; Codex planning owns the final target
  file decision.
- If hidden work expands scope, update the plan before implementation.

### 4. Implementation

- Apply only the planned changes in this repo.
- Keep the diff limited to the accepted fix scope.
- Do not mix the request fix with unrelated cleanup.

### 5. Validation

- Convert `tests_to_add` into the verification scope for the fix.
- Map each requested test into the smallest relevant verification type:
  - fixture update or new fixture
  - contract/schema review
  - docs consistency check
  - targeted runtime artifact validation
- Run the relevant checks for the touched surfaces, or explicitly record why a
  check was not run.

### 6. Commit

- Produce a reviewable commit in this repository.
- The final report must list changed files, acceptance status, validation
  results, remaining risks, and whether the request is fully resolved.

## File Decision Rules

- The external runner may propose file targets, but it does not decide them.
- Codex triage narrows the affected runtime layer.
- Codex planning decides the final file set to edit.
- Codex implementation stays within that planned file set unless the plan is
  explicitly updated first.

## Verification Scope Rules

- `tests_to_add` must be interpreted as required verification intent, not as
  optional suggestions.
- If a requested test already exists, validation should reference the existing
  check instead of creating a duplicate.
- If a requested test is not practical in the current repo state, the final
  report must explain the gap and the remaining risk.

## End State

An accepted `change_request` is complete only when it has produced:

- a reviewed plan update,
- a minimal implementation diff,
- validation evidence,
- and a reviewable git commit in this repo.
