"""Opt-in live smoke tests. Run with TRDIZIN_LIVE=1 to hit the real API."""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import trdizin


def _run(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = trdizin.run(argv)
    return code, json.loads(buf.getvalue())


@unittest.skipUnless(os.environ.get("TRDIZIN_LIVE") == "1",
                     "set TRDIZIN_LIVE=1 to run live smoke tests")
class TestLive(unittest.TestCase):
    def test_publication_search_live(self):
        code, out = _run(["search", "--q", "yapay zeka", "--limit", "3"])
        self.assertEqual(code, 0)
        self.assertGreater(out["pagination"]["total"], 0)
        self.assertTrue(len(out["results"]) >= 1)
        self.assertIn("yazarlar", out["results"][0])

    def test_facet_filter_live(self):
        code, out = _run(["search", "--q", "egitim", "--limit", "3",
                          "--filter", "accessType=OPEN"])
        self.assertEqual(code, 0)
        self.assertTrue(all(r["erisim"] == "OPEN" for r in out["results"]))

    def test_advanced_live(self):
        code, out = _run(["advanced", "--criteria",
                          json.dumps([{"field": "title", "term": "yapay zeka"}]),
                          "--limit", "3"])
        self.assertEqual(code, 0)
        self.assertGreater(out["pagination"]["total"], 0)

    def test_journals_live(self):
        code, out = _run(["journals", "--q", "egitim", "--limit", "3"])
        self.assertEqual(code, 0)
        self.assertTrue(len(out["results"]) >= 1)


if __name__ == "__main__":
    unittest.main()
