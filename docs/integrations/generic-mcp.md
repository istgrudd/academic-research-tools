# Generic MCP integration

Academic Research Tools uses local stdio transport. The MCP host starts the process and exchanges protocol messages over standard input/output.

## Installed command

After installing the package in an environment visible to the host:

```json
{
  "mcpServers": {
    "academic-research": {
      "command": "/absolute/path/to/academic-research",
      "args": ["serve"]
    }
  }
}
```

Find the command path with `command -v academic-research` on Unix or `Get-Command academic-research` in PowerShell.

## Ephemeral `uvx`

Run directly from PyPI without a prior installation:

```json
{
  "mcpServers": {
    "academic-research": {
      "command": "uvx",
      "args": [
        "--from",
        "academic-research-tools",
        "academic-research",
        "serve"
      ]
    }
  }
}
```

The explicit `--from` form is required because the distribution is named `academic-research-tools` while the executable is `academic-research`.

## Credentials

The recommended local setup is the protected shared user configuration:

```bash
academic-research configure
```

The MCP adapter re-resolves credentials for every tool call, so a newly saved provider key is visible without restarting the MCP process. Environment variables remain available for CI, containers, and host-managed secrets, and take precedence over the user configuration:

```json
{
  "env": {
    "SEMANTIC_SCHOLAR_API_KEY": "${SEMANTIC_SCHOLAR_API_KEY}",
    "ELSEVIER_API_KEY": "${ELSEVIER_API_KEY}",
    "ELSEVIER_INST_TOKEN": "${ELSEVIER_INST_TOKEN}",
    "SERPAPI_API_KEY": "${SERPAPI_API_KEY}"
  }
}
```

Not every MCP host expands `${...}` placeholders. If yours does not, use its secret manager, use the protected user configuration, or start the host from a shell where variables are already exported. Avoid committing plaintext MCP configuration.

Credential setup is optional for the first search. Never place API keys in agent chat, MCP arguments, or command-line flags.

## Verification

1. restart the MCP host
2. list tools and confirm `research_provider_status` exists
3. call `research_provider_status`
4. run `search_arxiv` with `query="agentic literature review"` and `limit=1`
5. optionally configure additional providers only after the keyless smoke test succeeds

If the process exits immediately, run the configured command manually and check its environment and Python installation. Protocol logs must go to standard error, never standard output, because stdout is reserved for MCP messages.
