# Add the marketplace and install NDA Harness

Add the private GitHub repository as a marketplace in your client, then install
**NDA Harness**. The client downloads the plugin for you.

| Setting | Value |
| --- | --- |
| Repository URL | `https://github.com/pilacorp/nda-harness` |
| Marketplace name | `nda-harness-internal` |
| Plugin name | `nda-harness` |
| Distribution branch | `main` |

These instructions target `main`. Updating a marketplace keeps its selected
branch; it does not switch branches automatically. A marketplace already
registered on `dev` stays there until you remove it and add it again with
`main`.

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
   codex plugin marketplace add https://github.com/pilacorp/nda-harness.git --ref main
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

## Claude Code (CLI, terminal)

1. **Add the marketplace:**

   ```sh
   claude plugin marketplace add 'https://github.com/pilacorp/nda-harness.git#main'
   ```

   The quoted `#main` selects the distribution branch.

2. **Install the plugin:**

   ```sh
   claude plugin install nda-harness@nda-harness-internal
   ```

3. **Check installation,** then restart the session and trust the reviewed plugin
   hooks if prompted:

   ```sh
   claude plugin list --json
   ```

**Authenticate the MCP servers.** Installing only *registers* the servers; it
does not sign in. OAuth runs only when a client connects, so you sign in after
install. From the terminal, no session needed:

```sh
claude mcp login nda-harness-hindsight
claude mcp login nda-harness-nda-rag
```

Credentials are stored once and reused by later sessions. `nda-harness-context7`
is open and needs no login.

**For later updates:**

```sh
claude plugin marketplace update nda-harness-internal
claude plugin update nda-harness@nda-harness-internal
```

Restart the session to apply the update, or use `/reload-plugins` when supported.

## Claude Desktop (Code tab, in-app UI)

Do everything from the Desktop app's **Code** tab — no terminal. Type the
slash commands into the prompt box.

1. **Add the marketplace.** Type `/plugin marketplace add` with no source and
   press Enter; the **Add marketplace** input opens. Enter:

   ```text
   https://github.com/pilacorp/nda-harness.git#main
   ```

   (Or type it in one line: `/plugin marketplace add https://github.com/pilacorp/nda-harness.git#main`.)

2. **Install the plugin.** Click the **+** button next to the prompt box and
   select **Add plugins** (if the menu shows **Plugins**, pick **Plugins →
   Browse plugins**). The plugin browser opens with plugins from your
   marketplaces — find **nda-harness** and select it.

3. **Choose a scope** (your user account, this project, or local-only) to finish
   installing. Manage it later from the **Installed** tab (enable, disable,
   update, uninstall). Restart the Code tab and trust the plugin hooks if
   prompted.

**Authenticate the MCP servers (in the UI).** The Customize Plugins / install
panel does **not** have an authenticate button — OAuth only runs once a session
connects to the server. This is Claude Code's designed behavior, not a bug. To
sign in from the UI:

1. In a Code session, type `/mcp` in the prompt box and press Enter. The MCP
   panel lists the plugin's servers.
2. Select **nda-harness-hindsight** (and **nda-harness-nda-rag** if it needs
   auth), choose **Authenticate**, and complete sign-in in the browser window
   that opens.
3. Return to Desktop; the server status flips to connected. The credential is
   stored and reused by later sessions. `nda-harness-context7` is open and needs
   no login.

**Reference (official Claude Code docs):**
[Install a plugin — Desktop app](https://code.claude.com/docs/en/plugins/install),
[Authenticate with remote MCP servers](https://code.claude.com/docs/en/mcp#authenticate-with-remote-mcp-servers),
and [`claude mcp login`](https://code.claude.com/docs/en/cli-reference).

## Cursor IDE

Private team marketplaces require **Teams or Enterprise**. A team administrator
adds the marketplace; team members then install the plugin in Cursor.

1. **Add the marketplace:** open **Cursor Dashboard → Plugins & MCPs → Team
   Marketplaces → Add Marketplace → Import from Repo**.
2. Paste `https://github.com/pilacorp/nda-harness`. Connect the GitHub provider
   and grant access to the private repository when prompted.
3. Select/confirm `main` as the tracked branch where supported. If your account
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
