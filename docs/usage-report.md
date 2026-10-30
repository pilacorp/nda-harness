# Local usage report

Each developer can see their own NDA Harness usage on the machine where they work. The numbers are not uploaded and are not written to the shared project memory bank.

Open the report from a project directory:

```sh
nda-plugin usage --client cursor --project .
```

Use `codex` or `claude` as `--client` for those apps. The command prints the last 7 days and the last 30 days, and writes the same report to a private HTML file under the developer home directory at `.nda-harness/usage/report.html`. Running it again refreshes that file.

Cursor's plugin page links here and to the repository. This page explains the command. It does not contain anyone's usage numbers.

The journal is filled by session startup, task preparation, skill selection, the pre-commit test gate, prompt and compaction hooks, and `usage-record` for memory outcomes, sub-agent summary lengths, and spec checks. Prompt text, secrets, and memory content are not stored.
