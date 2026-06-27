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


import argparse

import core

_ENTITY = {"search": "publication", "journals": "journal",
           "authors": "author", "institutions": "institution"}


def _build_parser():
    p = argparse.ArgumentParser(prog="trdizin.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    for cmd in _ENTITY:
        sp = sub.add_parser(cmd)
        sp.add_argument("--q", default="")
        sp.add_argument("--order", default="relevance-DESC")
        sp.add_argument("--page", type=int, default=1)
        sp.add_argument("--limit", type=int, default=20)
        sp.add_argument("--no-references", action="store_true")
        if cmd == "search":
            sp.add_argument("--filter", action="append", default=[],
                            metavar="KEY=VALUE")
    return p


def _parse_filters(pairs):
    filters = {}
    for item in pairs or []:
        if "=" not in item:
            raise ValueError("--filter expects KEY=VALUE, got %r" % item)
        k, v = item.split("=", 1)
        filters.setdefault(k, []).append(v)
    return filters


from urllib.parse import quote


def enrich_author_citations(result, _opener=None):
    """Best-effort: add `atif_sayisi` to author records via the citation list
    endpoint. Any failure leaves results unchanged."""
    ids = [str(r["id"]) for r in result.get("results", []) if r.get("id")]
    if not ids:
        return result
    id_list = ", ".join('"%s"' % i for i in ids)
    url = "%s/findAuthorCitationsByIdList/%s" % (core.BASE, quote(id_list))
    try:
        data = http_get_json(url, _opener=_opener)
    except RuntimeError:
        return result
    counts = data if isinstance(data, dict) else {}
    for r in result.get("results", []):
        key = str(r.get("id"))
        if key in counts:
            r["atif_sayisi"] = counts[key]
    return result


def run(argv, _opener=None):
    args = _build_parser().parse_args(argv)
    try:
        entity = _ENTITY[args.cmd]
        filters = _parse_filters(getattr(args, "filter", []))
        url = core.build_url(entity, q=args.q, order=args.order,
                             page=args.page, limit=args.limit, filters=filters)
        data = http_get_json(url, _opener=_opener)
        result = core.parse_response(data, entity, args.page, args.limit,
                                     include_references=not args.no_references)
        if args.cmd == "authors":
            result = enrich_author_citations(result, _opener=_opener)
        result["url"] = url
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (core.QueryError, ValueError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        print(str(e), file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        print(str(e), file=sys.stderr)
        return 1


def main():
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
