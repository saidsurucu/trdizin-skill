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


if __name__ == "__main__":
    unittest.main()
