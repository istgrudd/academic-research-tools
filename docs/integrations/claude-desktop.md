# Claude Desktop integration

Install Academic Research Tools in a stable virtual environment or launch it from PyPI with `uvx`.

Add a server entry to Claude Desktop's MCP configuration. The exact config file location can change by operating system and Claude Desktop version; consult Anthropic's current MCP documentation if the app does not expose the server.

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

For a source checkout, replace `command` with the absolute path to `.venv/bin/academic-research` and set `args` to `["serve"]`.

The simplest local credential path is `academic-research configure`; the MCP process reads the protected user configuration. Optional credentials can instead be placed in the server's `env` object if the desktop configuration is private:

```json
{
  "env": {
    "SEMANTIC_SCHOLAR_API_KEY": "your-key",
    "ELSEVIER_API_KEY": "your-key"
  }
}
```

Prefer the operating system's or an MCP launcher's secret management when available. Restart Claude Desktop, confirm the server connects, call `research_provider_status`, and test arXiv before credentialed providers.

Do not ask Claude to reveal its process environment and do not paste provider keys into prompts.
