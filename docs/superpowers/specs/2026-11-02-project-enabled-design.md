# Per-project enabled flag

## Intent

A pet project needs NDA Harness off without disabling the plugin for every other repo. The switch is `"enabled": false` in the committed project file `.nda-harness/config.json`.

## Behavior

- A missing `enabled` field means the project is on. `"enabled": true` means on. `"enabled": false` means off. Any other value is invalid configuration. Schema version stays 1.
- The field merges by key. A nested repo that omits `enabled` keeps the outer value. A nested repo that sets `enabled` wins.
- While the project is off, hook programs still start and return without workflow text. The git pre-commit test gate returns success without running the test command. The agent does not start harness skills and does not query NDA RAG or Hindsight. RTK and Context7 stay in force.
- The only command that wakes an off project is `nda-setup`. It writes `"enabled": true`. `select-bank` runs only as part of that setup when the profile has no bank id.
- Every other harness command, including `nda-verify` and `skill-selection`, replies with exactly `NDA Harness is disabled on the project` and does not run its job.
- Turning a project off is an edit to the file. There is no separate disable command.
