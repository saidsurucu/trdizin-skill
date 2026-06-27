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
