# Claude Code integration

Academic Research Tools provides a local stdio MCP server and a workflow skill for Claude Code.

## One-command setup

Install the Python package, then run:

```bash
academic-research install --platform claude-code
```

The installer:

1. calls the official `claude mcp add` command with user scope
2. registers an MCP server named `academic-research`
3. uses `uvx` when available, otherwise the installed Python executable
4. copies the bundled workflow to `~/.claude/skills/academic-research-workflow/SKILL.md`
5. does not request credentials or launch the configuration wizard

If the same MCP server is already registered, setup is treated as idempotent and the workflow skill is refreshed.

## Manual MCP registration

The equivalent official command with an ephemeral PyPI launcher is:

```bash
claude mcp add \
  --scope user \
  --transport stdio \
  academic-research -- \
  uvx --from academic-research-tools academic-research serve
```

Verify registration:

```bash
claude mcp list
```

Restart or reconnect Claude Code if newly registered tools are not visible in the current session.

## First use

Start with a keyless provider status check and arXiv search. Semantic Scholar public access is also available without a key, subject to shared rate limits.

Optional provider setup can be performed later in a trusted local terminal:

```bash
academic-research configure
```

Claude should not ask you to paste a key into chat. If a requested provider is unavailable, it should offer arXiv or Semantic Scholar as an immediate fallback.

## Removal

Remove the MCP registration with the Claude Code CLI:

```bash
claude mcp remove academic-research --scope user
```

The workflow skill is a regular local file and can be removed separately from `~/.claude/skills/academic-research-workflow/`.

See [Credential setup](../credentials.md) and [Generic MCP integration](generic-mcp.md).

Official references: [Claude Code MCP](https://code.claude.com/docs/en/mcp) and [Claude Code skills](https://code.claude.com/docs/en/skills).
