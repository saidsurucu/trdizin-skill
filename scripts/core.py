"""Pure, network-free helpers for the TR Dizin skill.

Everything here is unit-tested against committed fixtures in tests/fixtures/.
No third-party imports, no network calls.
"""

BASE = "https://search.trdizin.gov.tr/api"
SCHEMA_VERSION = 1
VALID_ENTITIES = ("publication", "journal", "author", "institution")

# order values observed live on the frontend (see reference.md).
# NOTE: `relevance-DESC` is the only order verified to work for *every* entity
# via the direct API. Some entity-specific orders (e.g. journal `name-ASC`)
# break the backend when called directly, so `relevance-DESC` is the safe
# default.
VALID_ORDERS = (
    "relevance-DESC",
    "publicationYear-DESC", "publicationYear-ASC",
    "orderCitationCount-DESC", "orderCitationCount-ASC",
    "orderTitle-ASC", "orderTitle-DESC",
    "name-ASC", "title-ASC",
)


class QueryError(ValueError):
    """Raised for invalid user query input (e.g. a colon in q)."""


from urllib.parse import urlencode


def sanitize_q(q):
    """Normalize a free-text query. Returns '' for empty/None/'*'.

    Raises QueryError if the query contains ':' — the backend rejects a bare
    colon in q (it tries to parse q as JSON). Field-scoped search must go
    through build_advanced_url instead.
    """
    if q is None:
        return ""
    q = q.strip()
    if q == "" or q == "*":
        return ""
    if ":" in q:
        raise QueryError(
            "q may not contain ':' — the TR Dizin backend rejects it. "
            "Use the 'advanced' command for field-scoped search."
        )
    return q


def _filter_params(filters):
    """Encode facet filters as `facet-<name>=<value>` params (verified live).

    `filters` keys are bare facet names (e.g. 'accessType', 'publication_year');
    a value may be a single string or a list (repeats the key).
    """
    params = []
    for key, value in (filters or {}).items():
        name = key if key.startswith("facet-") else "facet-" + key
        values = value if isinstance(value, (list, tuple)) else [value]
        for v in values:
            params.append((name, str(v)))
    return params


def build_url(entity, q="", order=None, page=1, limit=20, filters=None):
    """Build a defaultSearch URL for an entity (trailing slash before query)."""
    if entity not in VALID_ENTITIES:
        raise ValueError("unknown entity: %r (expected one of %r)"
                         % (entity, VALID_ENTITIES))
    q = sanitize_q(q)
    params = []
    if q:
        params.append(("q", q))
    if order:
        params.append(("order", order))
    params.append(("page", str(int(page))))
    params.append(("limit", str(int(limit))))
    params.extend(_filter_params(filters))
    return "%s/defaultSearch/%s/?%s" % (BASE, entity, urlencode(params))


# Advanced-search field aliases (UI label key -> q field name), verified live.
ADV_FIELDS = {
    "title": "title", "abstract": "abstract", "year": "year",
    "author": "author", "orcid": "orcid", "issn": "issn", "eissn": "eissn",
    "journal": "journalName", "journalName": "journalName",
    "doi": "publicationNumber", "publicationNumber": "publicationNumber",
    "language": "language", "institution": "institution",
}
_ADV_OPS = ("AND", "OR", "NOT")


def _norm_op(op):
    s = str(op or "AND").strip().upper()
    return s if s in _ADV_OPS else "AND"


def build_advanced_query(criteria):
    """Build the field-scoped q string.

    criteria: list of {"field", "term", "op"} dicts. First op ignored; later
    ops join with AND/OR/NOT. Produces a single outer-paren group:
        (title : ( "yapay zeka" ) AND abstract : ( "egitim" ))
    Raises QueryError if no usable criteria.
    """
    parts = []
    for i, c in enumerate(criteria or []):
        term = (c.get("term") or "").strip()
        field = c.get("field")
        if not term or not field:
            continue
        name = ADV_FIELDS.get(field, field)
        # quote the term as a phrase; escape any embedded double quotes
        safe = term.replace('"', '')
        frag = '%s : ( "%s" )' % (name, safe)
        if not parts:
            parts.append(frag)
        else:
            parts.append("%s %s" % (_norm_op(c.get("op")), frag))
    if not parts:
        raise QueryError("advanced search needs at least one {field, term}")
    return "(" + " ".join(parts) + ")"


def build_advanced_url(criteria, order="relevance-DESC", page=1, limit=20):
    """Advanced search URL. order+page are always sent (the colon-query
    requires them, see reference.md)."""
    q = build_advanced_query(criteria)
    params = [("q", q), ("order", order or "relevance-DESC"),
              ("page", str(int(page))), ("limit", str(int(limit)))]
    return "%s/defaultSearch/publication/?%s" % (BASE, urlencode(params))


def parse_pagination(data, page, limit):
    total_raw = (data.get("hits", {}) or {}).get("total", 0)
    if isinstance(total_raw, dict):
        total = int(total_raw.get("value", 0))
        relation = total_raw.get("relation", "eq")
    else:
        total = int(total_raw or 0)
        relation = "eq"
    return {"total": total, "total_relation": relation,
            "page": int(page), "limit": int(limit)}


def parse_facets(data):
    aggs = data.get("aggregations") or {}
    out = {}
    for raw_key, agg in aggs.items():
        name = raw_key[len("facet-"):] if raw_key.startswith("facet-") else raw_key
        container = agg.get("values", agg) if isinstance(agg, dict) else {}
        buckets = container.get("buckets", []) if isinstance(container, dict) else []
        out[name] = [{"key": b.get("key"), "count": b.get("doc_count", 0)}
                     for b in buckets]
    return out


def _author_names(src):
    names = []
    for a in src.get("authors") or []:
        if isinstance(a, dict):
            name = a.get("name") or a.get("fullName") or a.get("displayName")
        else:
            name = a
        if name:
            names.append(name)
    seen, out = set(), []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _first_abstract(src):
    abstracts = src.get("abstracts") or []
    return abstracts[0] if abstracts and isinstance(abstracts[0], dict) else {}


def _pages(src):
    s, e = src.get("startPage"), src.get("endPage")
    if s and e:
        return "%s-%s" % (s, e)
    return s or e or None


def normalize_record(hit, entity, include_references=True):
    src = hit.get("_source", {}) or {}
    if entity != "publication":
        return {
            "id": src.get("id") or hit.get("_id"),
            "baslik": src.get("name") or src.get("title") or src.get("orderTitle"),
            "ham": {k: v for k, v in src.items()
                    if isinstance(v, (str, int, float, bool))},
        }
    ab = _first_abstract(src)
    rec = {
        "id": src.get("id") or hit.get("_id"),
        "baslik": ab.get("title") or src.get("orderTitle"),
        "yazarlar": _author_names(src),
        "dergi": src.get("journal"),
        "yil": src.get("publicationYear"),
        "doi": src.get("doi"),
        "erisim": src.get("accessType"),
        "sayfa": _pages(src),
        "atif_sayisi": src.get("orderCitationCount"),
        "goruntulenme": src.get("viewCount"),
        "indirme": src.get("downloadCount"),
        "anahtar_kelimeler": ab.get("keywords") or [],
        "oz": ab.get("abstract"),
        "konular": src.get("subjects") or [],
        "pdf_uuid": src.get("pdf"),
        "veritabanlari": src.get("databases") or src.get("indexedBy") or [],
    }
    if include_references:
        rec["kaynakca"] = src.get("references") or []
    return rec


def parse_response(data, entity, page, limit, include_references=True):
    hits = (data.get("hits", {}) or {}).get("hits", []) or []
    return {
        "schema_version": SCHEMA_VERSION,
        "pagination": parse_pagination(data, page, limit),
        "facets": parse_facets(data),
        "results": [normalize_record(h, entity, include_references) for h in hits],
    }
