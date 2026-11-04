# <Bug title>

Type: bugfix

## Problem and reproduction

<Affected area/environment, reproduction steps and actual behavior.>

## Expected behavior and evidence

<Established intended behavior and its sources: existing requirements, acceptance
criteria, spec or other verified evidence. Identify unclear or conflicting intent.>

## Scope and related spec

<Affected scope and related repository spec paths/links, or explicitly none found.>

## Acceptance criteria

- The reported reproduction produces the expected behavior.
- A unit regression test fails before the fix and passes after it; relevant
  existing tests pass.
- The related spec's behavior/acceptance and regression case are updated in the
  same change. If none exists, add a concise behavior/regression spec with the fix.
- Code and spec receive human review together.

When publishing, keep `Type: bugfix` in the issue body and apply the repository's
`bug` label if available. The local task mirrors the live issue classification.
New requirements or unresolved conflicts with approved intent use the feature path.
