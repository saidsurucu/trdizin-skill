import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import trdizin


class TestHttp(unittest.TestCase):
    def test_returns_parsed_json(self):
        calls = []

        def fake(url, timeout):
            calls.append(url)
            return b'{"ok": true}'

        out = trdizin.http_get_json("https://x/y", _opener=fake)
        self.assertEqual(out, {"ok": True})
        self.assertEqual(len(calls), 1)

    def test_retries_then_succeeds(self):
        trdizin._sleep = lambda s: None
        state = {"n": 0}

        def flaky(url, timeout):
            state["n"] += 1
            if state["n"] < 2:
                raise trdizin.urllib.error.URLError("boom")
            return b'{"ok": 1}'

        out = trdizin.http_get_json("https://x", retries=2, _opener=flaky)
        self.assertEqual(out, {"ok": 1})
        self.assertEqual(state["n"], 2)

    def test_raises_after_exhaustion(self):
        trdizin._sleep = lambda s: None

        def always(url, timeout):
            raise trdizin.urllib.error.URLError("down")

        with self.assertRaises(RuntimeError):
            trdizin.http_get_json("https://x", retries=1, _opener=always)


if __name__ == "__main__":
    unittest.main()
