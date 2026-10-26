# Add the marketplace and install NDA Harness

Add the private GitHub repository as a marketplace in your client, then install
**NDA Harness**. The client downloads the plugin for you.

| Setting | Value |
| --- | --- |
| Repository URL | `https://github.com/pilacorp/nda-harness` |
| Marketplace name | `nda-harness-internal` |
| Plugin name | `nda-harness` |
| Distribution branch | `dev` |

These instructions target `dev` and become usable after the marketplace
implementation is merged there. Updating a marketplace keeps its selected
branch; it does not switch branches automatically.

You need access to the private repository and an installed client. Codex and
Claude use your existing GitHub/Git authentication; Cursor asks you to connect
its GitHub provider. Do not put credentials in the repository URL.

If an older uploaded or local copy is active, disable it before enabling the new
one. See [one-time migration](docs/plugin-operations.md#one-time-migration-from-an-upload-or-local-plugin)
to preserve project configuration and avoid duplicate hooks or MCP servers.

## Codex

Use the Codex executable supplied with your Desktop installation.

1. **Add the marketplace** in a terminal:

   ```sh
   codex plugin marketplace add https://github.com/pilacorp/nda-harness.git --ref dev
   ```

2. **Install the plugin**:

   ```sh
   codex plugin add nda-harness@nda-harness-internal
   ```

3. **Check installation**, then start a new Codex chat and trust the reviewed
   plugin hooks if prompted:

   ```sh
   codex plugin list --marketplace nda-harness-internal
   ```

For later updates:

```sh
codex plugin marketplace upgrade nda-harness-internal
```

If Codex reports the marketplace is already registered from another source,
inspect `codex plugin marketplace list`. To deliberately replace its URL or ref,
run `codex plugin marketplace remove nda-harness-internal`, then repeat add/install.
Removal can remove marketplace files; follow the
[recovery guidance](docs/plugin-operations.md#verification-and-recovery) for project
hooks bound to the previous installation.

## Claude Code and the Desktop Code tab

1. **Add the marketplace** in a terminal:

   ```sh
   claude plugin marketplace add 'https://github.com/pilacorp/nda-harness.git#dev'
   ```

2. **Install the plugin**:

   ```sh
   claude plugin install nda-harness@nda-harness-internal
   ```

3. **Check installation**, then restart the Claude Code session or Desktop Code
   tab and trust the reviewed plugin hooks if prompted:

   ```sh
   claude plugin list --json
   ```

The quoted `#dev` selects the distribution branch. Inside Claude Code,
equivalent commands begin with
`/plugin` instead of `claude plugin`. Desktop's Code tab shares that plugin store.

For later updates:

```sh
claude plugin marketplace update nda-harness-internal
claude plugin update nda-harness@nda-harness-internal
```

Restart the session to apply the update, or use `/reload-plugins` when supported.

## Cursor IDE

Private team marketplaces require **Teams or Enterprise**. A team administrator
adds the marketplace; team members then install the plugin in Cursor.

1. **Add the marketplace:** open **Cursor Dashboard → Plugins & MCPs → Team
   Marketplaces → Add Marketplace → Import from Repo**.
2. Paste `https://github.com/pilacorp/nda-harness`. Connect the GitHub provider
   and grant access to the private repository when prompted.
3. Select/confirm `dev` as the tracked branch where supported. If your account
   cannot select that branch, record the rollout as pending. Do not
   assume a GitHub `/tree/...` URL or a Claude-style `#ref` selects a Cursor branch.
4. Review **NDA Harness** and select **Add to Marketplace**. Confirm its source is
   `packages/nda-harness-cursor`. Under **Marketplace Settings**, set
   **Marketplace Access** for your team or group and save.
5. **Install the plugin:** in Cursor, open **Customize → Plugins**, find **NDA
   Harness** in the team marketplace and install/enable it.
6. Reload the window if prompted, then check the installed version and hook trust.

For later updates, the administrator clicks **Refresh** in the dashboard. GitHub
**Auto Refresh** additionally requires the Cursor GitHub App authorized for the
repository; indexing occurs at most once every ten minutes. Check the installed
version afterward; dashboard refresh alone does not prove open chats reloaded.

Private import, branch selection and installed refresh still require verification
with your team's Cursor account. Keep the repository private if a provider or
plan limitation blocks import.

## After installation

Follow the [setup guide](docs/setup-guide.md) for initial project setup,
Hindsight authentication, and skill selection.

Open your project in a new client session and ask the agent to set up NDA Harness.
It will ask for the project's test command or explicit Skip. Hindsight is optional;
authenticate it through the client's native MCP control only if you want memory.

For project setup, migration, optional memory and recovery, see
[plugin operations](docs/plugin-operations.md). Build, ZIP upload and local
development instructions are in that separate reference.

See [compatibility evidence](docs/compatibility/internal-client-marketplaces.md)
for executed checks and pending real-client validation.

Official references: [Codex plugins](https://developers.openai.com/plugins/),
[Cursor team marketplaces](https://cursor.com/docs/plugins), and
[Claude marketplace hosting](https://code.claude.com/docs/en/plugins/host-marketplace).
