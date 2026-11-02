# Standards reviewer

Review the diff for coding standards only. Do this review yourself, without invoking code-review or spawning agents. Read-only on this checkout. Do not look for a spec, an issue, or a merge verdict.

Diff:

```bash
git diff [BASE_SHA]..[HEAD_SHA]
```

Standards files: [STANDARDS_FILES]

Rules:

- A documented standard in the listed files is a hard violation when the diff breaks it. Cite the file and the rule.
- The smell baseline below is always a judgement call. Name the smell and quote the hunk.
- A documented repo standard wins. Where the repo endorses something the baseline would flag, suppress the smell.
- Skip anything tooling already enforces.
- Stay under 400 words.

Smell baseline (what it is, then how to fix):

- **Mysterious Name**: a name that hides what the thing does or holds. Rename it.
- **Duplicated Code**: the same logic shape in more than one hunk. Extract the shared shape.
- **Feature Envy**: a method that uses another object's data more than its own. Move it onto that data.
- **Data Clumps**: the same fields or parameters travel together. Bundle them into one type.
- **Primitive Obsession**: a primitive standing in for a domain concept. Give it a small type.
- **Repeated Switches**: the same switch or if-cascade on the same type. Use one polymorphism or one shared map.
- **Shotgun Surgery**: one logical change scattered across many files. Gather it into one module.
- **Divergent Change**: one module edited for unrelated reasons. Split it.
- **Speculative Generality**: abstraction for a need the change does not have. Delete it.
- **Message Chains**: a long `a.b().c().d()` walk. Hide it behind one method.
- **Middle Man**: a function that mostly delegates. Call the real target.
- **Refused Bequest**: an implementer that ignores most of what it inherits. Use composition.

Report only documented-standard breaches and baseline smells.

The smell baseline is adapted from mattpocock/skills `skills/engineering/code-review/SKILL.md`.

MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
