import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import trdizin

FX = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture_opener(name):
    path = os.path.join(FX, name)

    def _op(url, timeout):
        with open(path, "rb") as f:
            return f.read()

    return _op


def _run(argv, fixture):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = trdizin.run(argv, _opener=fixture_opener(fixture))
    return code, buf.getvalue()


class TestCli(unittest.TestCase):
    def test_search_outputs_envelope(self):
        code, out = _run(["search", "--q", "egitim", "--limit", "3"],
                         "publication_search.json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["schema_version"], 1)
        self.assertTrue(len(data["results"]) >= 1)
        self.assertIn("url", data)

    def test_colon_query_errors_cleanly(self):
        code, out = _run(["search", "--q", "title:x"], "publication_search.json")
        self.assertEqual(code, 2)
        self.assertIn("error", json.loads(out))

    def test_journals_uses_journal_entity(self):
        code, out = _run(["journals", "--q", "egitim", "--limit", "3"],
                         "journal_search.json")
        self.assertEqual(code, 0)

    def test_no_references_flag(self):
        code, out = _run(["search", "--q", "egitim", "--no-references"],
                         "publication_search.json")
        data = json.loads(out)
        self.assertFalse(any("kaynakca" in r for r in data["results"]))

    def test_bad_filter_errors(self):
        code, out = _run(["search", "--q", "x", "--filter", "broken"],
                         "publication_search.json")
        self.assertEqual(code, 2)


class TestAdvancedCli(unittest.TestCase):
    def test_advanced_outputs_envelope(self):
        code, out = _run(
            ["advanced", "--criteria",
             json.dumps([{"field": "title", "term": "yapay zeka"}]),
             "--limit", "3"],
            "advanced_search.json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["schema_version"], 1)
        self.assertTrue(len(data["results"]) >= 1)

    def test_advanced_bad_json_errors(self):
        code, out = _run(["advanced", "--criteria", "not-json"],
                         "advanced_search.json")
        self.assertEqual(code, 2)


class TestAuthorsCli(unittest.TestCase):
    def test_authors_have_citation_count(self):
        code, out = _run(["authors", "--q", "ahmet", "--limit", "3"],
                         "author_search.json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(len(data["results"]) >= 1)
        # atif_sayisi surfaced from the author record itself (no extra call)
        self.assertIn("atif_sayisi", data["results"][0])


if __name__ == "__main__":
    unittest.main()
