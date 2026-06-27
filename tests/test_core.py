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


if __name__ == "__main__":
    unittest.main()
