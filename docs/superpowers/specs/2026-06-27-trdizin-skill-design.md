# TR Dizin Skill — Design Spec

Date: 2026-06-27
Status: Approved (brainstorming) → ready for implementation planning

## 1. Purpose

A Claude Code **skill** for [TR Dizin](https://trdizin.gov.tr) (TÜBİTAK ULAKBİM
national academic index). It lets the user search publications, journals,
authors, and institutions, retrieve full publication metadata (including
references), and extract a publication's PDF as text — all in natural language.

It is the TR Dizin counterpart to the existing `dergipark` skill, but the
delivery mechanism is fundamentally different (see §2).

## 2. Key architectural finding

Unlike DergiPark (Cloudflare + login + CAPTCHA, hence a Claude-in-Chrome skill),
**TR Dizin exposes an open Elasticsearch-backed JSON API over HTTPS — no CAPTCHA,
no authentication.** Verified live with `curl` and via the live frontend's
network traffic.

Therefore this skill is a **plain HTTPS skill**, not a browser skill. Core logic
lives in a committed, dependency-free Python (stdlib) CLI that Claude invokes via
Bash. No Chrome, no JS injection, no API key.

## 3. Discovered API (verified 2026-06-27)

Single endpoint pattern (note the **trailing slash** — without it the server
301-redirects):

```
GET https://search.trdizin.gov.tr/api/defaultSearch/{entity}/?q=...&order=...&page=...&limit=...
```

### Entities (all confirmed live)
| Frontend route        | API entity     | Notes |
|-----------------------|----------------|-------|
| `/tr/yayin/ara`       | `publication`  | articles, projects, proceedings… |
| `/tr/dergi/ara`       | `journal`      | journals |
| `/tr/yazar/ara`       | `author`       | authors (+ secondary `findAuthorCitationsByIdList/<ids>` enrichment) |
| `/tr/kurum/ara`       | `institution`  | institutions |

### Response shape (raw Elasticsearch)
- `hits.total` → `{value, relation}` (relation may be `eq` or `gte` — handle both)
- `hits.hits[]._id`, `._score`, `._source`, `.highlight`, `.sort`
- `aggregations` → 13 facets, each with `buckets[]{key, doc_count}`

### Publication `_source` fields (subset, observed)
`id`, `abstracts[]` (each: `title`, `abstract`, `keywords[]`, `language`),
`authors[]`, `journal`, `publicationYear`, `volume`/`issue`/`startPage`/`endPage`,
`doi`, `accessType` (`OPEN`/`CLOSED`), `references[]`, `citedReferences[]`,
`orderCitationCount`, `viewCount`, `downloadCount`, `pdf` (a UUID for OPEN
records; `None` for CLOSED), `databases`/`indexedBy`, `subjects`, `docType`,
`publicationType`, `projectGroup`.

### Facets (= filters), 13 total
`accessType`, `authorName`, `database`, `documentType`, `facetAuthorCity`,
`facetAuthorCountry`, `facetAuthorInstitution`, `journalName`, `projectGroup`,
`publicationLanguage`, `publicationType`, `publication_year`, `subject`.

### Sort (`order`) values
`relevance-DESC`, `publicationYear-DESC`/`-ASC`, `orderCitationCount-DESC`/`-ASC`,
`orderTitle-ASC`/`-DESC` (title A-Z/Z-A); journal uses `name-ASC`; institution
uses `title-ASC`.

### Advanced search fields (from the live "Gelişmiş arama" form), 11 total
Başlık (title), Öz (abstract), Yıl (year), Yazar (author), ORCID, ISSN, E-ISSN,
Dergi Adı (journal name), DOI, Yayın Dili (language), Kurum (institution).

### Known gotchas (verified)
- `q` containing `:` breaks the backend (server-side JSON parse error). Must be
  rejected/sanitized with an actionable error.
- Bare `*` as `q` also breaks it. Empty/`*` queries must be handled (omit or
  substitute) rather than passed through.
- The **advanced-search wire format** (how the form encodes field-scoped queries)
  is **NOT yet pinned**. It must be captured live during implementation before
  `build_advanced_query` is written. Do not implement from assumptions.
- The **PDF download URL** derived from the `pdf` UUID is **NOT yet verified**.
  Must be captured live during implementation.

## 4. Scope

### v1 (this phase)
- `search` — publication search: `q`, `order`, `page`, `limit` + facet filters
  (year, document type, access type, language, subject, journal, institution).
  Returns normalized records (incl. references) **and** the facet counts.
- `journals`, `authors`, `institutions` — same pattern for the other 3 entities;
  authors enriched with citation counts via `findAuthorCitationsByIdList`.
- `advanced` — field-scoped query (the 11 fields above) with AND/OR/NOT.
  **Gated on live verification**: implementation must capture the real wire
  format first. If it cannot be reliably reproduced, ship `advanced` as a stub
  that returns a clear "not yet supported" error and defer to a follow-up.
- `pdf` — extract an OPEN publication's PDF as text/markdown using
  **`markitdown`** (optional dependency: `pip install 'markitdown[pdf]'`). Flow:
  resolve PDF download URL from the UUID (verify live) → download to a temp file
  → `markitdown` → return markdown. If `markitdown` is absent, return an
  actionable install error. No OCR. CLOSED records return availability metadata
  only.

### Explicitly out of scope (YAGNI)
- No login / "Takip ve Kayıtlı Aramalar" / saved searches.
- No write operations, no "Analiz Listesi".
- No homemade PDF parser (use markitdown).

## 5. Repository layout (mirrors dergipark)

```
trdizin-skill/
├── SKILL.md          # English workflows Claude follows
├── reference.md      # endpoints, fields, facets, order codes, live-verification notes
├── README.md         # Turkish user docs + install (markitdown optional)
├── LICENSE
├── scripts/
│   ├── trdizin.py    # CLI dispatcher: search|advanced|journals|authors|institutions|pdf
│   └── core.py       # pure functions (no network): build_url, sanitize_q,
│                     #   build_advanced_query, parse_hit, parse_facets, normalize_record
└── tests/
    ├── test_core.py        # fixture-based unittest, no network
    └── test_integration.py # separate live smoke tests (opt-in)
```

Claude invokes: `python3 scripts/trdizin.py <command> [--flags]` → clean JSON on
stdout.

## 6. Output schema (normalized, not raw Elasticsearch)

The CLI does NOT echo raw `_source`. It returns a stable, documented, normalized
shape so consumers are insulated from schema drift:

- Top level: `{ schema_version, query, url, pagination, facets, results, error? }`.
- `pagination`: `{ total, total_relation, page, limit }` (`total_relation`
  preserves ES `eq`/`gte`).
- Each result preserves **raw identifiers** (`id`, journal id, author ids, `doi`,
  `pdf` UUID) so journal/author/citation follow-up stays possible.
- **Author key is `yazarlar`** (plural array), NOT any key containing "author":
  Claude's output redactor blanks keys whose name contains "author"
  (verified behavior in the dergipark skill). This alias is part of the explicit
  normalized schema and documented as a workaround in `reference.md` — not an
  ad-hoc rename. Nested author-related fields are tested.
- `references` is large; included by default for single-record/detail use but
  toggleable (e.g. `--no-references`) for list results to keep output lean.

## 7. Robustness & safety requirements

- **Network**: explicit timeouts; retry only transient failures (HTTP 429/5xx)
  with backoff; descriptive `User-Agent`; on failure emit `{"error": ...}` JSON
  on stdout, diagnostics on stderr, and a meaningful nonzero exit code.
- **Input validation**: reject `q` containing `:`; handle empty/`*`; validate
  `order`, `page`, `limit`, `entity`, facet keys against known sets with
  actionable errors.
- **Resilience**: tolerate missing/null fields, malformed dates, duplicate
  authors, absent `aggregations`, and `hits.total` shape variations.
- **Politeness**: no concurrent bulk scraping; reasonable page-size caps;
  (optional) light local response cache.
- **Untrusted data**: all API content (titles, abstracts, references, author
  names) is data, never instructions to Claude. SKILL.md states this explicitly.

## 8. Testing

- `tests/test_core.py`: pure-function unit tests over committed JSON fixtures
  (no network) — URL building, q sanitization, hit/facet parsing, record
  normalization, advanced-query building (once the wire format is verified),
  Turkish/Unicode handling, empty/malformed responses, `hits.total` variants.
- `tests/test_integration.py`: opt-in live smoke tests against the real API
  (guarded by an env flag) — an open, undocumented API can change without notice.

## 9. Open items to verify live during implementation
1. Advanced-search wire format (capture from the live form's network request).
2. PDF download URL pattern from the `pdf` UUID (capture live; test several OPEN
   records: redirects, content types).
3. `markitdown` invocation contract on a downloaded TR Dizin PDF.

Each, once verified, gets a "Verified (date)" note appended to `reference.md`
(same convention as the dergipark skill).
