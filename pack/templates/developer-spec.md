# <Feature title>

Feature issue: <published issue URL>
Issue updated at: <UTC timestamp>
Issue body SHA-256: <fingerprint>
Consulted source revisions: <references>
Spec branch: <branch>

## Summary

<Explain the problem, proposed behavior, key decisions, and important limits in
clear upper-intermediate English. Keep this section easy to verify before reading
the detailed implementation contract below.>

## Setup and daily use

<When setup is needed, describe administrator and developer steps, prerequisites,
credential handling, verification, and normal use. Mark proposed commands clearly.
Omit this section when no setup or usage changes are needed.>

## Outcome and boundaries

Task classification: <behavior change or documentation/mechanical>
Describe outcome, scope, constraints, observed current/proposed behavior and callers.

## Implementation

Describe interfaces/configuration, data flow, compatibility and recovery.

## Acceptance mapping

| ID | Issue criterion | Expected behavior |
| --- | --- | --- |
| AC-01 | <source criterion> | <observable result> |

## Concrete test cases

| ID | Setup/input | Action | Expected result | Layer / acceptance IDs |
| --- | --- | --- | --- | --- |
| TC-01 | <fixture> | <action> | <assertion> | <unit/integration/manual; AC-01> |

Distinguish planned tests from executed evidence. Describe failure cases.

## Hook changes

<None, or guide links, affected surfaces/scopes, triggers, failure and fallback>

## Documentation and rollout/recovery

<Documentation impact, rollback, QA/manual scenarios>

## Decisions and risks

<Open decisions, constraints, unresolved risks and proposed exceptions>

## Review and implementation handoff

Spec PR: <URL>
Review reference: <unset until reviewed>
Merge reference/revision: <unset until merged>
Local spec matches merged reviewed version: <evidence>
Next action: <permitted workflow action>

The issue owns intent. This document does not grant approval; behavior-change
implementation requires verified review/merge and matching local content.
