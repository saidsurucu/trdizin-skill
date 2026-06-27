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
