# Credential setup

Credentials are optional capability upgrades. Academic Research Tools works immediately with arXiv and unauthenticated Semantic Scholar, so configuration is not required for a first search.

## Recommended interactive setup

Run the local wizard only when you want an additional provider or dedicated quota:

```bash
academic-research configure
```

Or choose one provider directly:

```bash
academic-research configure --provider scopus
academic-research configure --provider semantic-scholar
academic-research configure --provider google-scholar
academic-research configure --provider scopus-institutional
```

Secret input uses the operating system's hidden terminal prompt. There is intentionally no `--api-key` option because command arguments can leak through shell history, process listings, logs, and agent tool calls.

Never paste a provider key into an AI chat. Enter it yourself in a trusted local terminal.

Inspect or remove configuration without displaying values:

```bash
academic-research configure --list
academic-research configure --remove scopus
academic-research doctor
```

## Provider matrix

| Provider | Credential | Requirement |
|---|---|---|
| arXiv | none | no key required |
| Semantic Scholar | `SEMANTIC_SCHOLAR_API_KEY` | optional; recommended for dedicated quota |
| Scopus | `ELSEVIER_API_KEY` | required for Scopus features |
| Scopus institutional access | `ELSEVIER_INST_TOKEN` | optional; only when provided by an eligible institution |
| Google Scholar through SerpAPI | `SERPAPI_API_KEY` | required for the experimental adapter |

Not every provider needs to be configured. `academic-research status` reports availability and credential source without displaying credential values.

## Protected user configuration

The interactive wizard stores a small plaintext JSON file under the current operating-system user. It is protected by filesystem permissions, but it is not an encrypted vault or operating-system keyring.

Default locations:

- Linux: `~/.config/academic-research/credentials.json`
- macOS: `~/Library/Application Support/academic-research/credentials.json`
- Windows: `%APPDATA%\academic-research\credentials.json`

On Unix systems, the directory is written with mode `0700` and the file with mode `0600`. The resolver refuses to read credentials when either the file or its containing configuration directory is accessible by group or other users. On Windows, access is governed by the user's filesystem ACL.

Set `ACADEMIC_RESEARCH_CONFIG_DIR` to override the containing directory for an isolated deployment or test environment.

The resolver reads the file on each MCP tool call. A credential configured while the MCP server is running therefore becomes available without restarting that server. A host may still need to reconnect after the MCP server is registered for the first time.

## Resolution precedence

Credentials are resolved in this order:

1. current process environment
2. protected user configuration
3. not configured

Environment variables remain useful for CI, containers, and managed secret injection. They always override a value saved by the wizard.

For the current Unix shell:

```bash
export SEMANTIC_SCHOLAR_API_KEY="your-key"
export ELSEVIER_API_KEY="your-key"
export ELSEVIER_INST_TOKEN="your-token"
export SERPAPI_API_KEY="your-key"
```

For PowerShell:

```powershell
$env:SEMANTIC_SCHOLAR_API_KEY = "your-key"
$env:ELSEVIER_API_KEY = "your-key"
$env:ELSEVIER_INST_TOKEN = "your-token"
$env:SERPAPI_API_KEY = "your-key"
```

Use only the lines relevant to you.

## Local `.env` files

`.env.example` is a reference and contains empty values. The package intentionally does not auto-load `.env`, because MCP hosts and deployment environments have different secret-management rules.

If you create a local `.env`, keep it untracked and restrict permissions:

```bash
cp .env.example .env
chmod 600 .env
```

Load it explicitly in a trusted Unix shell:

```bash
set -a
. ./.env
set +a
```

Do not upload `.env` to GitHub, paste keys into issues or chats, include them in fixtures, or pass them as CLI arguments.

## Agent-driven installation

An agent may install the package, register its MCP server, call provider status, and run a keyless search. It must not ask for a key in chat or automatically launch the credential wizard.

After first setup, the agent should mention `academic-research configure` once as an optional next step. Configuration becomes a prerequisite only when the user explicitly requests a provider whose required credential is missing. If another provider is available, the agent should offer or perform that search as an immediate fallback.

## MCP hosts

MCP hosts may also provide credentials through an `env` object or secret manager. Avoid checking a JSON configuration containing plaintext keys into a dotfiles repository. The protected user configuration is usually simpler for local stdio MCP hosts because every adapter uses the same resolver.

## Rotation

If a key may have leaked, revoke or rotate it with the provider first. Removing it from the user configuration does not remove it from shell history, chat history, Git history, CI logs, backups, or copied files.

## Provider-specific instructions

- [arXiv](providers/arxiv.md)
- [Semantic Scholar](providers/semantic-scholar.md)
- [Scopus](providers/scopus.md)
- [Google Scholar through SerpAPI](providers/google-scholar-serpapi.md)
