# Imported baseline

- Source: `/home/ubuntu/.hermes/plugins/scopus_research`
- Imported: 2026-09-08
- Purpose: preserve the working Hermes plugin before extracting a harness-neutral package.
- Baseline command: `cd scopus_research && python3 -m unittest discover -s tests -v`
- Result: 15 tests passed.
- Compilation command: `python3 -m compileall -q .`
- Result: passed.
- Credential policy: no `.env`, API key, token, cache, or bytecode artifact is part of the repository.

The live plugin remains untouched. New implementation work must happen in this repository.
