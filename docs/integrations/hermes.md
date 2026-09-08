# Hermes Agent integration

## Install directly from GitHub

```bash
hermes plugins install istgrudd/academic-research-tools --enable
```

Pin a reviewed commit for reproducible installation:

```bash
hermes plugins install istgrudd/academic-research-tools \
  --ref <full-commit-sha> --enable
```

The repository root contains `plugin.yaml` and a compatibility shim. The plugin registers eight native tools and the bundled `academic-research-workflow` skill.

## Install as a Python distribution

After the package is published:

```bash
python -m pip install academic-research-tools
hermes plugins enable academic-research
```

The distribution declares `academic_research.hermes_plugin:register` in the `hermes_agent.plugins` entry-point group.

## Configure credentials

Set environment variables in the environment that starts Hermes, then restart the Hermes session or gateway:

```bash
export SEMANTIC_SCHOLAR_API_KEY="..."  # optional
export ELSEVIER_API_KEY="..."          # Scopus only
export ELSEVIER_INST_TOKEN="..."       # optional entitlement token
export SERPAPI_API_KEY="..."           # experimental adapter only
```

There is no global `requires_env` gate. arXiv, provider status, unified search, and unauthenticated Semantic Scholar remain available without optional keys. Hermes hides Scopus or SerpAPI tools through per-tool checks when their required key is absent.

## Verify

```bash
hermes plugins list
hermes plugins doctor academic-research
hermes plugins compat academic-research
```

Inside Hermes, call `research_provider_status`, then make a one-result arXiv query. Do not paste credentials into a chat message.

## Relationship to MCP

The native adapter gives Hermes first-class toolsets and skill discovery. The MCP server remains available when a deployment prefers a standard cross-harness integration. Both use the same provider core.
