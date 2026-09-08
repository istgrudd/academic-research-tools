# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Planned

- Crossref and OpenAlex providers
- Citation and reference graph traversal
- BibTeX and CSV export
- Structured literature-screening sessions

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

[Unreleased]: https://github.com/istgrudd/academic-research-tools/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/istgrudd/academic-research-tools/releases/tag/v0.1.0
