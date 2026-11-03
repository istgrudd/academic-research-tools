# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Planned

- Crossref and OpenAlex providers
- Citation and reference graph traversal
- BibTeX and CSV export
- Structured literature-screening sessions

## [0.2.1] - 2026-11-04

### Fixed

- arXiv free-text queries are now sent as all-terms field queries (`all:a AND all:b`), with quoted phrases kept as one term, instead of a raw string that matched loosely related papers; explicit arXiv syntax (`ti:`, `abs:`, `au:`, `cat:`, `AND`/`OR`/`ANDNOT`, parentheses) and ID lookups are passed through unchanged
- When no arXiv paper contains every free-text term, the first page retries once with any-term (`OR`) matching and reports a warning instead of silently returning nothing
- arXiv and Semantic Scholar retry timeouts, connection failures, HTTP 429, and HTTP 5xx up to two times with 1 s and 2 s backoff; other 4xx responses are not retried
- Network failures now explain that the host could not be reached from the current network and suggest checking firewall, ISP, or VPN restrictions or setting `HTTPS_PROXY`
- Connection resets and dropped connections are reported as provider network errors instead of escaping as unexpected exceptions
- arXiv and Semantic Scholar user agents now report the installed release and the project URL
- Unified search now includes provider warnings, prefixed by source

### Added

- `academic-research doctor --online` sends one small request with a 10 s timeout to each active provider and reports reachability with `✓`/`✗` and a credential-redacted reason; `--json` adds an `online` section, and offline `doctor` behaviour is unchanged
- `ACADEMIC_RESEARCH_TIMEOUT` sets the request timeout in seconds for all providers (default 30, clamped to 1–120)

## [0.2.0] - 2026-09-10

### Added

- Central credential resolver shared by the Python API, CLI, MCP server, and Hermes adapter
- Protected per-user credential configuration with Unix directory mode `0700` and file mode `0600`
- Interactive hidden-input `academic-research configure` wizard with provider selection, listing, and removal
- Credential-safe offline `academic-research doctor` diagnostics
- One-command MCP and workflow-skill installation for Claude Code and Codex
- Machine-readable configuration commands for explicitly requested providers that are unavailable
- Claude Code and Codex integration guides
- One-click, manually dispatched GitHub Release automation with Trusted Publishing handoff

### Changed

- Environment variables now override protected user configuration instead of being the only credential source
- MCP tools reload credentials on every call, allowing configuration changes without a server restart
- Unified MCP search keeps results from available sources when an optional requested provider is not configured
- Agent workflow guidance now treats credentials as optional capability upgrades and completes the first keyless search before recommending configuration

### Security

- Credential input is rejected outside an interactive terminal and is never accepted through command arguments
- Installer host error output is suppressed so accidental secret-bearing diagnostics are not relayed
- Insecure credential file and directory permissions are rejected on Unix
- Invalid credential configuration returns secret-safe, actionable MCP and Hermes errors

## [0.1.0] - 2026-09-08

### Added

- Harness-neutral Python API with normalized paper metadata and provenance
- Unified multi-provider search with DOI, arXiv ID, and title-year deduplication
- Official arXiv API provider with no key requirement
- Official Semantic Scholar Academic Graph provider with optional authentication
- Official Elsevier Scopus Search, Abstract Retrieval, and Author Search providers
- Experimental Google Scholar discovery through optional SerpAPI
- Local stdio MCP server using the official MCP Python SDK v2
- Command-line status, search, and MCP serve commands
- Native Hermes Agent adapter with per-provider credential gating
- Synthetic offline tests, CI, security policy, and provider documentation

[Unreleased]: https://github.com/istgrudd/academic-research-tools/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/istgrudd/academic-research-tools/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/istgrudd/academic-research-tools/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/istgrudd/academic-research-tools/releases/tag/v0.1.0
