# Hermes integration

Current Hermes versions can discover the package entry point after Python installation:

```bash
pip install academic-research-tools
hermes plugins enable academic-research
```

Hermes can also install the repository as a directory plugin:

```bash
hermes plugins install <owner>/academic-research-tools --enable
```

The root `plugin.yaml` intentionally has no `requires_env` gate. arXiv and unauthenticated Semantic Scholar remain available without keys; Scopus and SerpAPI tools use per-tool availability checks.
