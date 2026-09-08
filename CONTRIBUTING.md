# Contributing

Thanks for improving Academic Research Tools. Small, focused pull requests are easier to review and release safely.

## Before opening code

For new providers, public API changes, credential handling, or large refactors, open an issue first. Describe:

- the research workflow being improved
- the official or third-party API involved
- authentication and rate-limit requirements
- expected normalized fields and provenance
- relevant terms or data-license constraints

Bug fixes and documentation corrections can go directly to a pull request.

## Development setup

```bash
git clone https://github.com/istgrudd/academic-research-tools.git
cd academic-research-tools
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

Run all local quality gates:

```bash
ruff check src tests __init__.py
pytest
python -m compileall -q src __init__.py
python -m build
python -m twine check dist/*
```

## Test requirements

- Add a failing test before changing behaviour.
- Use synthetic, minimal fixtures.
- Do not include copied provider responses, licensed datasets, personal records, or credentials.
- Unit and CI tests must not make live provider calls.
- Test error responses, pagination, rate limits, and missing credentials where applicable.
- Preserve provenance when normalizing or merging records.

A manual live smoke test is optional before a release and must use the maintainer's own credential and quota. Never print the credential or commit the output.

## Provider implementation checklist

A provider should:

1. live under `src/academic_research/providers/`
2. use an official API where available
3. validate limits before making a request
4. use a bounded timeout and a descriptive user agent
5. translate provider errors into actionable exceptions
6. return normalized models with source IDs and provenance
7. report whether authentication is required or optional
8. document terms, coverage, quotas, and access caveats
9. include synthetic offline tests

Direct scraping of websites that prohibit it is out of scope.

## Pull requests

Keep commits understandable and use descriptive messages such as:

```text
feat: add Crossref provider
fix: preserve DOI during Semantic Scholar normalization
docs: clarify Scopus subscription requirements
```

In the pull request, include the commands run and their real outputs. CI must pass before merge. Maintainers may ask for narrower scope, additional fixtures, or legal/provider clarification.

## Releases

Only maintainers publish packages and tags. The release process verifies a clean source distribution and wheel, installs the wheel in a fresh environment, smoke-tests the CLI and MCP server, and checks that no credentials or large provider responses are included.
