import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import trdizin


class TestPdf(unittest.TestCase):
    def test_pdf_to_text_with_injected_deps(self):
        out = trdizin.pdf_to_text(
            "uuid-123",
            _resolve=lambda u: "https://download.example/x",
            _fetch=lambda url: b"%PDF-1.4 fake",
            _convert=lambda path: "# Title\n\nbody",
        )
        self.assertEqual(out["schema_version"], 1)
        self.assertEqual(out["pdf_uuid"], "uuid-123")
        self.assertIn("body", out["markdown"])

    def test_missing_markitdown_returns_install_error(self):
        def convert_raises(path):
            raise ImportError("No module named 'markitdown'")

        out = trdizin.pdf_to_text(
            "uuid-123",
            _resolve=lambda u: "https://download.example/x",
            _fetch=lambda url: b"%PDF",
            _convert=convert_raises,
        )
        self.assertIn("error", out)
        self.assertIn("markitdown", out["error"])

    def test_download_failure_returns_error(self):
        def boom(u):
            raise RuntimeError("404")

        out = trdizin.pdf_to_text("uuid-123", _resolve=boom)
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()
