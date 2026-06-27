import os
import sys
import json
import unittest
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import core

FX = os.path.join(os.path.dirname(__file__), "fixtures")


class TestConstants(unittest.TestCase):
    def test_base_is_https_no_trailing_slash(self):
        self.assertEqual(core.BASE, "https://search.trdizin.gov.tr/api")

    def test_entities(self):
        self.assertEqual(core.VALID_ENTITIES,
                         ("publication", "journal", "author", "institution"))


class TestSanitizeQ(unittest.TestCase):
    def test_none_and_empty_become_empty(self):
        self.assertEqual(core.sanitize_q(None), "")
        self.assertEqual(core.sanitize_q("   "), "")

    def test_bare_star_becomes_empty(self):
        self.assertEqual(core.sanitize_q("*"), "")

    def test_normal_query_trimmed(self):
        self.assertEqual(core.sanitize_q("  yapay zeka "), "yapay zeka")

    def test_colon_rejected(self):
        with self.assertRaises(core.QueryError):
            core.sanitize_q("title:yapay")


class TestBuildUrl(unittest.TestCase):
    def test_basic(self):
        url = core.build_url("publication", q="yapay zeka",
                             order="publicationYear-DESC", page=1, limit=20)
        p = urlparse(url)
        self.assertEqual(p.scheme, "https")
        self.assertEqual(p.path, "/api/defaultSearch/publication/")
        qs = parse_qs(p.query)
        self.assertEqual(qs["q"], ["yapay zeka"])
        self.assertEqual(qs["order"], ["publicationYear-DESC"])
        self.assertEqual(qs["limit"], ["20"])

    def test_empty_q_omitted(self):
        url = core.build_url("journal", q="", order="relevance-DESC")
        self.assertNotIn("q=", url)

    def test_unknown_entity_raises(self):
        with self.assertRaises(ValueError):
            core.build_url("bogus", q="x")

    def test_trailing_slash_before_query(self):
        url = core.build_url("author", q="ahmet")
        self.assertIn("/author/?", url)

    def test_filters_get_facet_prefix(self):
        url = core.build_url("publication", q="egitim",
                             filters={"accessType": "OPEN"})
        qs = parse_qs(urlparse(url).query)
        self.assertEqual(qs["facet-accessType"], ["OPEN"])

    def test_filter_multivalue_repeats_key(self):
        url = core.build_url("publication", q="x",
                             filters={"publication_year": ["2023", "2024"]})
        qs = parse_qs(urlparse(url).query)
        self.assertEqual(sorted(qs["facet-publication_year"]), ["2023", "2024"])


def _load(name):
    with open(os.path.join(FX, name)) as f:
        return json.load(f)


class TestParseMeta(unittest.TestCase):
    def setUp(self):
        self.data = _load("publication_search.json")

    def test_pagination_from_fixture(self):
        pg = core.parse_pagination(self.data, page=1, limit=3)
        self.assertIsInstance(pg["total"], int)
        self.assertIn(pg["total_relation"], ("eq", "gte"))
        self.assertEqual(pg["page"], 1)
        self.assertEqual(pg["limit"], 3)

    def test_pagination_handles_bare_int_total(self):
        pg = core.parse_pagination({"hits": {"total": 42}}, page=2, limit=10)
        self.assertEqual(pg["total"], 42)
        self.assertEqual(pg["total_relation"], "eq")

    def test_facets_stripped_and_counted(self):
        facets = core.parse_facets(self.data)
        self.assertIn("accessType", facets)
        self.assertTrue(all("key" in b and "count" in b
                            for b in facets["accessType"]))

    def test_facets_absent_returns_empty(self):
        self.assertEqual(core.parse_facets({"hits": {}}), {})


class TestNormalize(unittest.TestCase):
    def setUp(self):
        self.hit = _load("publication_search.json")["hits"]["hits"][0]

    def test_publication_core_keys(self):
        rec = core.normalize_record(self.hit, "publication")
        for k in ("id", "baslik", "yazarlar", "yil", "erisim", "pdf_uuid"):
            self.assertIn(k, rec)
        self.assertIsInstance(rec["yazarlar"], list)

    def test_no_author_named_keys(self):
        rec = core.normalize_record(self.hit, "publication")
        self.assertFalse([k for k in rec if "author" in k.lower()])

    def test_references_toggle(self):
        with_refs = core.normalize_record(self.hit, "publication", include_references=True)
        without = core.normalize_record(self.hit, "publication", include_references=False)
        self.assertIn("kaynakca", with_refs)
        self.assertNotIn("kaynakca", without)

    def test_missing_fields_tolerated(self):
        rec = core.normalize_record({"_source": {}}, "publication")
        self.assertEqual(rec["yazarlar"], [])
        self.assertIsNone(rec["baslik"])

    def test_other_entity_shape(self):
        jhit = _load("journal_search.json")["hits"]["hits"][0]
        rec = core.normalize_record(jhit, "journal")
        self.assertIn("id", rec)
        self.assertIn("ham", rec)


class TestParseResponse(unittest.TestCase):
    def test_envelope(self):
        data = _load("publication_search.json")
        out = core.parse_response(data, "publication", page=1, limit=3)
        self.assertEqual(out["schema_version"], core.SCHEMA_VERSION)
        self.assertIn("pagination", out)
        self.assertIn("facets", out)
        self.assertIsInstance(out["results"], list)
        self.assertTrue(len(out["results"]) >= 1)


class TestAdvanced(unittest.TestCase):
    def test_single_field(self):
        q = core.build_advanced_query([{"field": "title", "term": "yapay zeka"}])
        self.assertEqual(q, '(title : ( "yapay zeka" ))')

    def test_field_alias_doi_and_journal(self):
        q = core.build_advanced_query([{"field": "doi", "term": "10.1/x"}])
        self.assertIn("publicationNumber", q)
        q2 = core.build_advanced_query([{"field": "journal", "term": "Eğitim"}])
        self.assertIn("journalName", q2)

    def test_boolean_join_single_outer_paren(self):
        q = core.build_advanced_query([
            {"field": "title", "term": "a"},
            {"field": "abstract", "term": "b", "op": "NOT"},
        ])
        self.assertEqual(q, '(title : ( "a" ) NOT abstract : ( "b" ))')

    def test_empty_criteria_raises(self):
        with self.assertRaises(core.QueryError):
            core.build_advanced_query([])

    def test_url_includes_order_and_page(self):
        url = core.build_advanced_url([{"field": "title", "term": "x"}])
        qs = parse_qs(urlparse(url).query)
        self.assertIn("order", qs)
        self.assertEqual(qs["page"], ["1"])
        self.assertIn("/defaultSearch/publication/?", url)


if __name__ == "__main__":
    unittest.main()
