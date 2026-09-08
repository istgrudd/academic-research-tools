# Scopus Research plugin for Hermes

Tools:

- `arxiv_search`: official public arXiv API; no key required.
- `semantic_scholar_search`: official Semantic Scholar Academic Graph API; key optional.
- `scopus_search`: official Scopus Search API with normalized paper metadata.
- `scopus_abstract`: Abstract Retrieval API by DOI, EID, Scopus ID, PII, PubMed ID, or PUI.
- `scopus_author_search`: Scopus Author Search API.
- `google_scholar_search`: Google Scholar discovery through SerpAPI (third-party; Google has no official public Scholar API).

The default three-source suite is Scopus + arXiv + Semantic Scholar. The Google Scholar adapter remains optional and is hidden when `SERPAPI_API_KEY` is absent.

## Credential setup

Add this line to `~/.hermes/.env` without quotes:

```bash
ELSEVIER_API_KEY=your_key_here
```

If Elsevier supplied an institutional token, optionally add:

```bash
ELSEVIER_INST_TOKEN=your_institution_token_here
```

Google Scholar is optional. Create a SerpAPI key at `https://serpapi.com/` and add:

```bash
SERPAPI_API_KEY=your_serpapi_key_here
```

This plugin does not scrape `scholar.google.com` directly because Google exposes no official public Scholar API and automated VPS scraping is brittle, CAPTCHA-prone, and may violate service terms.

Semantic Scholar works without a key. For a dedicated quota, optionally request a key and add `SEMANTIC_SCHOLAR_API_KEY` to `~/.hermes/.env`.

Then enable and restart:

```bash
hermes plugins enable scopus-research
hermes gateway restart
```

Do not commit `.env` or send the key through chat. API-key-only access may be limited when the VPS is outside the institution's subscribed IP range.

## Tests

```bash
cd ~/.hermes/plugins/scopus_research
python3 -m unittest discover -s tests -v
```
