"""TR Dizin skill CLI. Python stdlib only (except the optional `pdf` command).

Usage:
    python3 scripts/trdizin.py search --q "yapay zeka" --order publicationYear-DESC
    python3 scripts/trdizin.py journals --q "egitim"
    python3 scripts/trdizin.py authors --q "ahmet"
    python3 scripts/trdizin.py institutions --q "ankara"
    python3 scripts/trdizin.py advanced --criteria '[{"field":"title","term":"yapay zeka"}]'
    python3 scripts/trdizin.py pdf --uuid <pdf_uuid>
"""
import json
import sys
import time
import urllib.error
import urllib.request

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_USER_AGENT = "trdizin-skill/1.0"


def _sleep(seconds):
    time.sleep(seconds)


def _default_opener(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_get_json(url, timeout=20, retries=2, _opener=None):
    opener = _opener or _default_opener
    attempt = 0
    while True:
        try:
            raw = opener(url, timeout)
            return json.loads(raw)
        except urllib.error.HTTPError as e:
            if e.code in _RETRYABLE_STATUS and attempt < retries:
                attempt += 1
                _sleep(attempt)
                continue
            raise RuntimeError("HTTP %s for %s" % (e.code, url))
        except urllib.error.URLError:
            if attempt < retries:
                attempt += 1
                _sleep(attempt)
                continue
            raise RuntimeError("network error for %s" % url)
