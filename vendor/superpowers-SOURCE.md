# Superpowers bundled source

- Upstream: https://github.com/obra/superpowers
- Revision: `bb92a77741419a4ab5f06e711a283343f1ada0c3` (manifest 7.0.0)
- Archive: `superpowers-bb92a777.tar.gz`
- Source URL: https://codeload.github.com/obra/superpowers/tar.gz/bb92a77741419a4ab5f06e711a283343f1ada0c3
- SHA-256: `496b576d4a4a62c0d72cce4a9e99ff46c57026c07fe503931cbb8afd33006cf2`
- License: MIT, complete LICENSE inside the source archive and generated package.

The builder checks this archive before reading it and preserves the original
source under `vendor/superpowers/` in each package. Active skills and agent assets
are generated from that same source. Only Markdown namespace references change
from `superpowers:` to `nda-harness:` so native skill
discovery resolves them in the containing plugin. There are no independently
maintained client copies. The generated SOURCE.json records this adaptation.

NDA's trusted bootstrap instructs the agent to load using-superpowers. It does not
register a duplicate upstream startup handler or modify existing Superpowers
plugins/hooks. Original handlers remain bundled for provenance, without alteration.
