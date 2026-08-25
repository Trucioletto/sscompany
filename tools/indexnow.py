#!/usr/bin/env python3
"""Tell IndexNow the pages changed, instead of waiting to be asked.

Bing, Yandex, Seznam and Naver share one endpoint: submit a list of URLs and
they fetch them soon rather than whenever a crawler next wanders past. Google
does not participate — for Google the sitemap and Search Console are the route,
and this changes nothing there.

The URL list is read from sitemap.xml rather than typed here, for the same
reason llms.txt is generated: a hand-kept list is correct on the day somebody
last remembered it. Whatever build.py published is exactly what gets submitted.

Ownership is proved by a key file served from the domain root. The key is public
by design — it demonstrates control of the site, it protects nothing — so it
lives in the repository like any other served file.

    python3 tools/indexnow.py            # submit every URL in the sitemap
    python3 tools/indexnow.py --dry-run  # show what would be sent

Run it after a deploy has actually gone live. Submitting a URL that still serves
the old page asks a search engine to come and index the old page.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOST = "spinnesoftware.com"
ENDPOINT = "https://api.indexnow.org/indexnow"
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def key() -> tuple[str, str]:
    """The key is whatever <key>.txt sits in the root, and its name must match
    its contents. Deriving both from one file means they cannot drift apart —
    a mismatch is the one failure IndexNow reports as a flat 403."""
    found = [p for p in ROOT.glob("*.txt")
             if p.stem not in {"robots", "llms"} and p.read_text().strip() == p.stem]
    if len(found) != 1:
        names = [p.name for p in found] or "none"
        sys.exit(f"  expected exactly one <key>.txt whose contents are its own name; found {names}")
    k = found[0].stem
    return k, f"https://{HOST}/{found[0].name}"


def urls() -> list[str]:
    sm = ROOT / "sitemap.xml"
    if not sm.exists():
        sys.exit("  no sitemap.xml — run tools/i18n/build.py first")
    root = ET.parse(sm).getroot()
    return [u.find("s:loc", NS).text for u in root.findall("s:url", NS)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    k, location = key()
    us = urls()
    print(f"  host      {HOST}")
    print(f"  key file  {location}")
    print(f"  urls      {len(us)}")

    if args.dry_run:
        for u in us[:5]:
            print(f"            {u}")
        print(f"            … and {len(us) - 5} more" if len(us) > 5 else "")
        return 0

    body = json.dumps({"host": HOST, "key": k, "keyLocation": location,
                       "urlList": us}).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            code, text = r.status, r.read().decode("utf-8", "replace").strip()
    except urllib.error.HTTPError as e:
        code, text = e.code, e.read().decode("utf-8", "replace").strip()
    except urllib.error.URLError as e:
        sys.exit(f"  could not reach {ENDPOINT}: {e.reason}")

    # 200 accepted, 202 accepted while the key is verified. The rest are worth
    # spelling out: the codes are documented but the responses are usually empty,
    # so a bare number tells you nothing at the moment you need it to.
    meaning = {
        200: "accepted",
        202: "accepted — key still to be validated, which is normal on a first run",
        400: "malformed request",
        403: "key rejected — the key file did not match, or is not being served",
        422: "a URL did not belong to this host, or the key does not match the host",
        429: "too many requests — wait and try again",
    }.get(code, "unexpected")
    print(f"  → HTTP {code}: {meaning}")
    if text:
        print(f"    {text[:300]}")
    return 0 if code in (200, 202) else 1


if __name__ == "__main__":
    raise SystemExit(main())
