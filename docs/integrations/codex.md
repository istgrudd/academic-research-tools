# Codex integration

Academic Research Tools provides a local stdio MCP server and a reusable workflow skill for the Codex CLI.

## One-command setup

Install the Python package, then run:

```bash
academic-research install --platform codex
```

The installer:

1. calls the official `codex mcp add` command
2. registers an MCP server named `academic-research`
3. uses `uvx` when available, otherwise the installed Python executable
4. copies the bundled workflow to `~/.agents/skills/academic-research-workflow/SKILL.md`
5. does not request credentials or launch the configuration wizard

If the same MCP server is already registered, setup is treated as idempotent and the workflow skill is refreshed.

## Manual MCP registration

The equivalent official command with an ephemeral PyPI launcher is:

```bash
codex mcp add academic-research -- \
  uvx --from academic-research-tools academic-research serve
```

Verify registration:

```bash
codex mcp list
```

Restart Codex if the newly installed skill or MCP tools are not visible in the current session.

## First use

Start with a keyless provider status check and arXiv search. Semantic Scholar public access is also available without a key, subject to shared rate limits.

Optional provider setup can be performed later in a trusted local terminal:

```bash
academic-research configure
```

Codex should not ask you to paste a key into chat. If a requested provider is unavailable, it should offer arXiv or Semantic Scholar as an immediate fallback.

## Removal

Remove the MCP registration with:

```bash
codex mcp remove academic-research
```

The workflow skill is a regular local file and can be removed separately from `~/.agents/skills/academic-research-workflow/`.

See [Credential setup](../credentials.md) and [Generic MCP integration](generic-mcp.md).

Official references: [Codex MCP](https://developers.openai.com/codex/mcp/) and [Codex skills](https://developers.openai.com/codex/skills/).
