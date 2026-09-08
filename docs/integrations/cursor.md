# Cursor integration

Cursor supports MCP server configuration at user or project scope. For a repository-local setup, add `.cursor/mcp.json` and keep credential-bearing configuration out of version control.

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

For a source checkout, point `command` at the absolute installed executable:

```json
{
  "mcpServers": {
    "academic-research": {
      "command": "/absolute/path/academic-research-tools/.venv/bin/academic-research",
      "args": ["serve"]
    }
  }
}
```

Configure optional environment variables through Cursor's supported local settings or a private `env` object. Do not commit API keys in `.cursor/mcp.json`.

Reload Cursor after editing the configuration. Verify `research_provider_status`, then run a one-result arXiv search. If tools are absent, execute the configured command in a terminal and confirm the same Python environment can import `academic_research`.

Cursor's MCP UI and config locations may evolve; use Cursor's current documentation when its interface differs from this example.
