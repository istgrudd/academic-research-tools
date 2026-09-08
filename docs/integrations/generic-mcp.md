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

After the package is published to PyPI:

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

Add only required provider variables using the host's supported environment mechanism:

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

Not every MCP host expands `${...}` placeholders. If yours does not, use its secret manager or start the host from a shell where variables are already exported. Avoid committing plaintext MCP configuration.

## Verification

1. restart the MCP host
2. list tools and confirm `research_provider_status` exists
3. call `research_provider_status`
4. run `search_arxiv` with `query="agentic literature review"` and `limit=1`
5. add credentialed providers only after the keyless smoke test succeeds

If the process exits immediately, run the configured command manually and check its environment and Python installation. Protocol logs must go to standard error, never standard output, because stdout is reserved for MCP messages.
