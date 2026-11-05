# Desktop custom marketplace from the nda-harness Git URL

Feature issue: [pilacorp/nda-harness#44](https://github.com/pilacorp/nda-harness/issues/44)
Issue updated at: 2026-11-04T03:46:28Z
Issue body SHA-256: 673343e68e4b65e929e66a97ce9bd486681decf94390c692909e47e4d99da198
Consulted source revisions: NDA Harness `main` at `1c7a9d9b616b34886878cca1dd08434112268cf5`.
Consulted docs: Claude Code plugin docs (code.claude.com/docs/en/plugins/install, host-marketplace, cli-reference), fetched 2026-11-05.
Repository visibility: **public** (confirmed via GitHub API; default branch `main`).
Spec branch: `nda/44-desktop-git-marketplace`

## Summary

Claude Code Desktop cannot add `https://github.com/pilacorp/nda-harness` as a
custom marketplace, while `claude plugin marketplace add` from a terminal
succeeds. The repository is **public**, so no git credentials are required to
clone it — this rules out an authentication cause. The manifest at
`.claude-plugin/marketplace.json` is valid and works from the CLI, so it is not a
manifest bug either. Because the CLI and Desktop share the same plugin engine,
the failure is in what differs between them: the environment Desktop runs `git`
in (PATH/network), or how the Desktop "add marketplace" UI parses the URL string.
Root cause is **not yet established** — this spec defines the evidence to
capture, ranked hypotheses to test, and the fix or documented-blocker outcome.

## Problem

- Desktop "add custom marketplace" UI fails for the nda-harness Git URL.
- The same URL on the same machine succeeds via the CLI.
- The initial report did not include the Desktop version, the exact URL string
  entered, the error message, or logs. Without these the failure mode is a guess.

## Facts the fix must respect

From the Claude Code plugin docs (the same engine backs the CLI and the Desktop
Code tab, per INSTALLATION.md):

1. Claude Code clones a marketplace repo by running `git` on the user's machine
   with **interactive prompts turned off**. `git` must be present and reachable
   in the environment that invokes it.
2. The repo is **public**, so the clone needs no credential, no ssh key, and no
   credential helper. Authentication is therefore **not** a candidate cause.
3. Accepted URL forms include `https://github.com/owner/repo` (Claude appends
   `.git`), `https://…/repo.git[#ref]`, and `git@host:path[.git][#ref]`. A bare
   host or `owner/repo` shorthand resolves to github.com shorthand and can be
   rejected with `Invalid marketplace source format`.
4. Desktop apps commonly launch with a **login environment different from the
   user's interactive shell**: PATH may omit the `git` the terminal uses, or
   network/proxy/TLS settings may differ. This is the most likely reason
   CLI-works-but-Desktop-fails for a public repo.

## Root-cause hypotheses (ranked, each with a discriminating test)

- **H1 — Desktop invokes `git` in an environment without it (or a broken one).**
  Desktop's PATH omits the `git` the terminal uses, or git is too old, so the
  clone fails before it starts. *Test:* capture Desktop's effective PATH /
  `which git` / `git --version` and compare to the terminal. (H1 is the top
  suspect now that auth is excluded.)
- **H2 — URL-form mismatch in the UI field.** The string entered may be a form
  the UI rejects (bare host, shorthand, or a `/tree/<branch>` web URL). *Test:*
  in Desktop, try `https://github.com/pilacorp/nda-harness`,
  `https://github.com/pilacorp/nda-harness.git`, and
  `https://github.com/pilacorp/nda-harness.git#main`; record which parse.
- **H3 — Network/proxy/TLS difference in Desktop vs terminal.** Desktop's clone
  cannot reach github.com (corporate proxy, different trust store) though the
  terminal can. *Test:* from Desktop's environment, attempt a plain
  `git clone https://github.com/pilacorp/nda-harness` and read the error.
- **H4 — Upstream Desktop limitation.** The Code-tab UI add path differs from the
  CLI and genuinely cannot add this (kind of) marketplace. *Test:* only after
  H1–H3 are ruled out; reproduce in Desktop with a **known-good public**
  marketplace and a clean profile.

## Investigation plan (do first — the acceptance criteria require this evidence)

1. Record Desktop version/build, OS, and the **exact URL string** pasted.
2. Reproduce and capture the verbatim error message and any Desktop/Code-tab
   logs around the failure.
3. In the same OS account, capture Desktop's PATH, `which git`, `git --version`,
   and proxy/`http.*` git config; compare to the terminal where the CLI add
   succeeds.
4. Run H1→H2→H3→H4 tests in that order; stop at the first confirmed hypothesis.

## Fix / outcome (branches by confirmed hypothesis)

This repo cannot change Claude Code Desktop itself. The deliverable is the
smallest change that makes Desktop work or documents a tested blocker:

- **If H1 (git/PATH):** document in `INSTALLATION.md` that Desktop needs `git` on
  the PATH it launches with (and how to verify), and keep the terminal
  `claude plugin marketplace add 'https://github.com/pilacorp/nda-harness.git#main'`
  as the supported path and sanctioned workaround.
- **If H2 (URL form):** correct the documented URL to an accepted form and note
  which forms the Desktop UI rejects.
- **If H3 (network):** document the proxy/trust-store requirement; CLI workaround
  stands.
- **If H4 (upstream):** record the Desktop version, the reproduction with a
  known-good public marketplace, and file/link an upstream report; keep the CLI
  add documented as the workaround.

No change to `.claude-plugin/marketplace.json`, package routing, or hooks is
expected; if investigation shows the manifest is at fault, revise this spec.

## Acceptance mapping

| Issue acceptance criterion | Addressed by |
| :- | :- |
| Capture Desktop version, exact URL, error message, logs | Investigation plan steps 1–2 |
| Compare Desktop vs CLI with same URL and GitHub access | Investigation plan step 3; H1–H3 tests |
| Identify metadata vs auth vs Desktop behavior as cause | Auth excluded (public repo); remaining split across H1 (env), H2 (URL/metadata), H3–H4 (Desktop behavior) |
| Verify Desktop add + plugin discovery, or document blocker + tested CLI workaround | Fix/outcome section (all branches) |
| Confirm CLI marketplace-add still works | Concrete test case T4 |

## Concrete test cases

- **T1 (repro):** In Desktop, add `https://github.com/pilacorp/nda-harness` →
  record exact error. *Baseline of the bug.*
- **T2 (H4 control):** In Desktop, add a **known-good public** marketplace (a
  public example repo) → if it also fails, the Desktop UI add path is broken for
  any URL (H4); if it succeeds, the problem is specific to this repo/URL/env.
- **T3 (H2 URL forms):** In Desktop, try the three URL forms in H2 → record which
  parse/clone.
- **T4 (CLI regression):** `claude plugin marketplace add 'https://github.com/pilacorp/nda-harness.git#main'`
  then `claude plugin install nda-harness@nda-harness-internal` and
  `claude plugin list --json` → still succeeds.
- **T5 (fix verification):** After applying the H1/H2/H3 fix, repeat T1 in Desktop
  → marketplace adds and `nda-harness` appears in plugin discovery; **or** T4
  remains the documented workaround with an upstream link.

## Boundaries

- Does not modify Claude Code Desktop; at most documents its behavior and a
  tested workaround.
- Does not change the marketplace manifest, package routing, hooks, or the
  distribution branch unless investigation proves one is the cause.
- No credential work: the repo is public and the clone needs none.

## Documentation and review handoff

Update `INSTALLATION.md` (Claude Code / Desktop Code tab section) with the
confirmed prerequisite and URL form. Attach captured evidence (version, URL,
error, env comparison) to issue #44. Human review required before merge; any
conflict between retrieved docs and this approved spec is reported to the owner.
