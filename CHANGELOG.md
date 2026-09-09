# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Planned

- Crossref and OpenAlex providers
- Citation and reference graph traversal
- BibTeX and CSV export
- Structured literature-screening sessions

## [0.2.0] - 2026-09-10

### Added

- Central credential resolver shared by the Python API, CLI, MCP server, and Hermes adapter
- Protected per-user credential configuration with Unix directory mode `0700` and file mode `0600`
- Interactive hidden-input `academic-research configure` wizard with provider selection, listing, and removal
- Credential-safe offline `academic-research doctor` diagnostics
- One-command MCP and workflow-skill installation for Claude Code and Codex
- Machine-readable configuration commands for explicitly requested providers that are unavailable
- Claude Code and Codex integration guides

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

[Unreleased]: https://github.com/istgrudd/academic-research-tools/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/istgrudd/academic-research-tools/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/istgrudd/academic-research-tools/releases/tag/v0.1.0
