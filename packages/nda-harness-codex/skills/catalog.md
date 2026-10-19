# Skills hub

This folder is the source Skills hub for NDA Harness. Native plugins bundle it once alongside the shared engine; do not copy shared skills into each project's `.nda-harness/`. The catalog is discovery metadata; load a skill body only for the assigned task. These skills are instructions, not installed tools or enforced gates.

| Skill | Select when | Required context | Output |
| --- | --- | --- | --- |
| [UI/UX Pro Max](ui-ux-pro-max/SKILL.md) | Designing, implementing, or reviewing interfaces | Approved UI scope/spec, existing design system, detected stack, relevant local files | UI/UX recommendations or scoped changes, using bundled search data |
| [Official Vietnamese document wording](vietnamese-official-wording/SKILL.md) | Drafting or revising formal Vietnamese organizational documents | Document purpose/audience, approved template/glossary, source facts | Vietnamese draft/revision and unresolved factual fields; human approves issuance |
| [Diagram Design](diagram-design/SKILL.md) | Creating or updating architecture, workflow, sequence, or other explanatory diagrams | Verified source relationships, audience, output requirements, approved project style | Self-contained HTML/SVG diagrams; PNG/SVG exports when requested |

The coordinating agent reads this catalog and selects the smallest set per assignment. Default to one skill for a specialist sub-agent. A UI assignment selects UI/UX Pro Max; a Vietnamese formal-document assignment selects the wording skill; an explanatory diagram assignment selects Diagram Design. Select multiple only when the assignment needs them, such as Vietnamese wording within a diagram. Ordinary backend or test-review work may need none. Do not preload the whole hub into the coordinator or every child.

Agent capability checks, context preparation, and test-quality review are harness workflow improvements, not hub skills. They apply independently of specialist skill selection; see the [architecture](https://github.com/pilacorp/nda-harness/blob/dev/docs/architecture.md#harness-quality-improvements).

Context7 is a mandatory documentation tool outside the specialist hub. Make it available when library/framework documentation is needed; selection of no specialist skill does not remove that requirement. Query only relevant public documentation, with no private code/context or full documentation preload.

UI/UX Pro Max is vendored from NextLevelBuilder with its license and [pinned provenance](ui-ux-pro-max/SOURCE.md). The Vietnamese wording skill is locally authored and follows supplied organizational templates; it does not claim official certification or legal compliance.

Diagram Design is vendored from Cathryn Lavery with its license, third-party notices, and [pinned provenance](diagram-design/SOURCE.md). It includes type references, templates, and local verification helpers. Load the selected type's references rather than the entire collection; retain the project's approved style choice.

Before spawning, provide a bounded assignment with: task/issue, allowed scope and side effects, repository revision, shared policy/profile paths, exact selected skill paths and pinned release revision, relevant input references, expected output, and stop conditions. Start with fresh/minimal context where the client supports it. A child loads the shared policy/profile and selected bodies, not the entire hub or unrelated parent history. Never pass credentials or personal-memory content to another agent.

Use the folder names `ui-ux-pro-max`, `vietnamese-official-wording`, and `diagram-design` as stable selection IDs; an empty selection is valid. Read this catalog for discovery, not the linked bodies. Validate IDs and resolved paths against the pinned hub before delegation. Record the IDs, catalog revision, short reason, and requested tools inline in task state. Load selected references progressively. Native startup/delegation hooks may automate this contract after client verification; tool-schema exposure must be verified separately from skill loading. Mandatory Superpowers/RTK requirements remain outside specialist selection.

Use the existing client's native delegation mechanism. If the client cannot isolate instructions or supports no sub-agents, use a separate fresh session with the same bounded assignment; document that limitation rather than claiming isolation. Skills do not grant new tools, permissions, human approvals, or authority to skip workflow gates. Returned findings are evidence for the coordinator and human reviewer, not approval.

Record selected skill paths/revision and assignment scope in the task record. On handoff, select again for the new assignment; do not accumulate every previously used skill. Maintainers review skill changes with the policy and pin them to the same release.
