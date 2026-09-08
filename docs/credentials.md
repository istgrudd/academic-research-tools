# Credential setup

Credentials are supplied by the user and stay in the local process environment. Academic Research Tools does not provide shared keys, hosted secret storage, or telemetry.

## Provider matrix

| Provider | Environment variable | Requirement |
|---|---|---|
| arXiv | none | no key required |
| Semantic Scholar | `SEMANTIC_SCHOLAR_API_KEY` | optional; recommended for dedicated quota |
| Scopus | `ELSEVIER_API_KEY` | required for Scopus features |
| Scopus institutional access | `ELSEVIER_INST_TOKEN` | optional; only when provided by an eligible institution |
| Google Scholar through SerpAPI | `SERPAPI_API_KEY` | required for the experimental adapter |

Not every provider needs to be configured. `academic-research status` reports availability without displaying values.

## Shell environment

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

`.env.example` is a reference and contains empty values. The package intentionally does **not** auto-load `.env`, because MCP hosts and deployment environments have different secret-management rules.

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

Do not upload `.env` to GitHub, paste keys into issues, include them in fixtures, or pass them as CLI arguments. CLI arguments may be retained in shell history and process listings.

## MCP hosts

Most MCP hosts accept an `env` object in server configuration. Prefer variable interpolation or the host's secret manager. Avoid checking a JSON config containing plaintext keys into a dotfiles repository.

Restart the MCP host after changing its environment, then call `research_provider_status`.

## Rotation

If a key may have leaked, revoke or rotate it with the provider first. Removing it from the current file does not remove it from Git history, CI logs, backups, or copied configuration.

## Provider-specific instructions

- [arXiv](providers/arxiv.md)
- [Semantic Scholar](providers/semantic-scholar.md)
- [Scopus](providers/scopus.md)
- [Google Scholar through SerpAPI](providers/google-scholar-serpapi.md)
