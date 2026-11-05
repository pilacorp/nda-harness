# <Explicitly selected issue/task>

Issue: <published issue URL>
Type: feature
Spec: <repository-relative spec path; may be absent during drafting or initially for bugfix>
Revision: <current Git HEAD>
Input fingerprint: <prepare/refresh result>
Stage: <actual recorded stage; never inferred approval>
Evidence: <test/review links or explicitly no executed tests yet>
Next action: <next permitted action>

## Context and prerequisites

<Role, checkout identity, policy/profile/release references, live issue fingerprint,
spec PR review/merge references, merged revision and independently verified checks>

## Completed work and tests

<Completed steps, source revisions, red patch/base, passing-test summaries/links>

## Documentation and unresolved decisions

<Doc impact, selected skills and reasons, blockers, risks and remaining work>

For a bug fix, set `Type: bugfix` only when restoring established intended behavior.
Verify and record the live issue's `bug` label or `Type: bugfix` body field at
start/resume; this local record mirrors that shared classification.
Record reproduction, root cause, expected-behavior sources and regression-test
evidence. Update the related spec and its regression case in the same change
before completion; add a concise behavior/regression spec if none exists. Record
its path above and include code and spec in human review. New requirements or
unresolved conflicts with approved intent use the feature path.

Keep this record current for checkpoint/resume across agents. No transcripts,
credentials or fabricated approvals/test results. Native hooks never write it.
Keep this file local under Git-ignored `.nda-harness/tasks/`; never stage or force-add it.
