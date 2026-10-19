Issue: https://github.com/pilacorp/nda-harness/issues/10
Spec: specs/harness-plugins.md
Revision: f035ccf1dbbb74131834f6673647474299447937
Stage: implementation
Evidence: approved specification merged in PR https://github.com/pilacorp/nda-harness/pull/14; explicit owner instruction to implement on implementation/hindsight-supabase-auth
Next action: finish runtime validation and implementation review; record remaining native UI/trust/expiry checks honestly

The live feature issue was checked on 2026-10-18. It still describes the previous
CLI/provider-token approach. The owner's later clarification and approved merged
plugin spec govern this work. Do not add provider credentials, token conversion,
or released-installation migration. Claude Code Desktop is an initial package by
owner instruction on 2026-10-19; it uses the shared engine and native Claude plugin files.

Implemented: reproducible Codex, Cursor, and Claude Code packages, bundled dependencies/assets, native
MCP declarations and deferred Codex authentication, fixed-client setup/verify,
locked automatic bootstrap, committed project profile, composed local Git test
checks, transactional recovery, shared project bank identity, five context skills,
optional memory instructions and fallback guidance, plugin installation docs.

Automated evidence and exact native runtime observations are recorded in
`docs/compatibility/harness-plugin-implementation.md`. Native Desktop/IDE trust
execution, complete OAuth lifecycle and production endpoint remain independent
validation requirements. No local metadata, hook or this record grants approval.

This development task has not adopted the harness repository as a configured
plugin project; no test command or Git hook activation was silently inferred.
