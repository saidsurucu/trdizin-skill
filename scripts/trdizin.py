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
    adv = sub.add_parser("advanced")
    adv.add_argument("--criteria", required=True,
                     metavar='JSON',
                     help='JSON list of {"field","term","op"} objects')
    adv.add_argument("--order", default="relevance-DESC")
    adv.add_argument("--page", type=int, default=1)
    adv.add_argument("--limit", type=int, default=20)
    adv.add_argument("--no-references", action="store_true")
    pdfp = sub.add_parser("pdf")
    pdfp.add_argument("--uuid", required=True)
    return p


def _parse_filters(pairs):
    filters = {}
    for item in pairs or []:
        if "=" not in item:
            raise ValueError("--filter expects KEY=VALUE, got %r" % item)
        k, v = item.split("=", 1)
        filters.setdefault(k, []).append(v)
    return filters


import os
import tempfile


def resolve_pdf_url(pdf_uuid, _opener=None):
    """Step 1: getFile returns a JSON string = a signed download URL."""
    url = "%s/getFile/%s?showViewer=false" % (core.BASE, pdf_uuid)
    signed = http_get_json(url, _opener=_opener)
    if not isinstance(signed, str) or not signed.startswith("http"):
        raise RuntimeError("unexpected getFile response for %s" % pdf_uuid)
    return signed


def _default_pdf_fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _default_convert(path):
    from markitdown import MarkItDown
    return MarkItDown().convert(path).text_content


def pdf_to_text(pdf_uuid, _resolve=None, _fetch=None, _convert=None):
    """Resolve signed URL, download PDF, convert to markdown via markitdown.
    Returns {schema_version, pdf_uuid, markdown} or {error}."""
    resolve = _resolve or resolve_pdf_url
    fetch = _fetch or _default_pdf_fetch
    convert = _convert or _default_convert
    try:
        signed = resolve(pdf_uuid)
        data = fetch(signed)
    except Exception as e:
        return {"error": "failed to download PDF: %s" % e}
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        tmp.write(data)
        tmp.close()
        markdown = convert(tmp.name)
    except ImportError:
        return {"error": "markitdown is required for PDF extraction. "
                         "Install with: pip install 'markitdown[pdf]'"}
    except Exception as e:
        return {"error": "PDF conversion failed: %s" % e}
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    return {"schema_version": core.SCHEMA_VERSION, "pdf_uuid": pdf_uuid,
            "markdown": markdown}


def run(argv, _opener=None):
    args = _build_parser().parse_args(argv)
    try:
        if args.cmd == "pdf":
            result = pdf_to_text(args.uuid)
            print(json.dumps(result, ensure_ascii=False))
            return 1 if "error" in result else 0
        if args.cmd == "advanced":
            criteria = json.loads(args.criteria)
            url = core.build_advanced_url(criteria, order=args.order,
                                          page=args.page, limit=args.limit)
            data = http_get_json(url, _opener=_opener)
            result = core.parse_response(data, "publication", args.page,
                                         args.limit,
                                         include_references=not args.no_references)
            result["url"] = url
            print(json.dumps(result, ensure_ascii=False))
            return 0
        entity = _ENTITY[args.cmd]
        filters = _parse_filters(getattr(args, "filter", []))
        url = core.build_url(entity, q=args.q, order=args.order,
                             page=args.page, limit=args.limit, filters=filters)
        data = http_get_json(url, _opener=_opener)
        result = core.parse_response(data, entity, args.page, args.limit,
                                     include_references=not args.no_references)
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
