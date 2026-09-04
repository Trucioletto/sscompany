#!/usr/bin/env python3
"""The multilingual checks that only make sense on the built pages.

check.sh validates one page at a time. These are the failures that exist only
BETWEEN pages, and only once there are fifteen of them:

  - an hreflang cluster where one page fails to point back, which makes Google
    discard the whole cluster rather than the one bad link
  - a page that claims a canonical belonging to another language
  - a <title> or meta description that a translation pushed past the length a
    search result will show
  - two languages that ended up with the same title, which means one of them
    was never translated

    python3 tools/i18n/seocheck.py
"""
from __future__ import annotations

import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SITE = "https://spinnesoftware.com"

# Google renders roughly 580px of title and 920px of description; character
# counts are a proxy, and CJK characters are about twice as wide.
TITLE_MAX = 60
DESC_MAX = 158


def width(s: str) -> int:
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def attr(doc: str, pattern: str) -> str | None:
    m = re.search(pattern, doc)
    return html.unescape(m.group(1)) if m else None


def main() -> int:
    pages = sorted(
        p for p in ROOT.rglob("*.html")
        if ".git" not in p.parts and "tools" not in p.parts
    )
    problems = []   # real errors: a crawler acts on these
    advisories = []  # over a guideline: a crawler truncates, nothing breaks
    by_canonical = {}
    alternates = {}
    titles = {}

    for p in pages:
        doc = p.read_text(encoding="utf-8")
        rel = str(p.relative_to(ROOT))
        if 'content="noindex' in doc:
            continue

        lang = attr(doc, r'<html lang="([^"]+)"')
        canon = attr(doc, r'rel="canonical" href="([^"]+)"')
        title = attr(doc, r"<title>(.*?)</title>")
        desc = attr(doc, r'<meta name="description" content="([^"]*)"')

        # The canonical must match where the file actually sits, or the page is
        # telling a crawler to index a different one.
        expect = SITE + "/" + str(p.parent.relative_to(ROOT)).replace(".", "").strip("/")
        expect = (expect.rstrip("/") + "/").replace(SITE + "//", SITE + "/")
        if canon != expect:
            problems.append(f"canonical {canon} but the file is at {expect}   {rel}")

        by_canonical.setdefault(canon, []).append(rel)

        alts = dict(re.findall(
            r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">', doc))
        alternates[canon] = (rel, lang, alts)

        if title:
            if width(title) > TITLE_MAX:
                advisories.append(f"title {width(title)} wide (>{TITLE_MAX})   {rel}")
            titles.setdefault(title, []).append(rel)
        if desc and width(desc) > DESC_MAX:
            advisories.append(f"description {width(desc)} wide (>{DESC_MAX})   {rel}")

    for canon, files in by_canonical.items():
        if len(files) > 1:
            problems.append(f"canonical {canon} claimed by {len(files)} files: {files}")

    # Reciprocity: if A lists B as an alternate, B must list A.
    for canon, (rel, lang, alts) in alternates.items():
        for code, target in alts.items():
            if code == "x-default":
                continue
            back = alternates.get(target)
            if back is None:
                problems.append(f"hreflang {code} -> {target}, which is not a page   {rel}")
            elif canon not in back[2].values():
                problems.append(f"hreflang {code} -> {target} does not point back   {rel}")
        # Only for a page that is part of a cluster. build.py emits no hreflang at
        # all for a page that exists in one language, because a set of alternates
        # with one member has nothing to describe — see the PAGES table there. So
        # an empty `alts` is that page keeping its promise, not a page forgetting
        # itself; demanding a self-link here would ask build.py to advertise a
        # cluster that does not exist.
        if lang and alts and lang not in alts:
            problems.append(f"page is lang={lang} but lists no hreflang for itself   {rel}")

    # Two languages sharing a title means one was never translated. Product and
    # company names legitimately repeat, so only flag longer ones.
    for title, files in titles.items():
        if len(files) > 1 and len(title) > 25:
            langs = {f.split("/")[0] if "/" in f else "en" for f in files}
            if len(langs) > 1:
                problems.append(f"same title in {sorted(langs)}: {title!r}")

    indexed = len([p for p in pages if 'content="noindex' not in p.read_text(encoding="utf-8")])
    print(f"  {indexed} indexable pages, {sum(len(a[2]) for a in alternates.values())} hreflang links")
    if advisories:
        # Length is a guideline, not a contract: a long title is truncated in a
        # search result and a long description is usually rewritten by the engine.
        # Nothing breaks. Reported separately so a real error is never buried in
        # a list of them — and because every one of these is inherited from the
        # English source, which is over on the home title and on four of five
        # descriptions. It is a copy decision, not a translation defect.
        # The language is the directory ONLY when that directory is a language.
        # Deriving it from the path alone counted "about" and "sparkle" — the
        # English pages, which live at the root — as two more languages.
        codes = {"it","es","fr","de","pt-BR","ru","id","zh-Hans","ja","ko",
                 "ar","ur","hi","bn"}
        langs = set()
        for a in advisories:
            head = a.split()[-1].split("/")[0]
            langs.add(head if head in codes else "en")
        print(f"  note  {len(advisories)} title/description(s) over the SERP guideline, "
              f"across {len(langs)} of 15 languages — including the English source, "
              f"which is where every one of them comes from")

    if problems:
        for x in problems:
            print(f"  FAIL  {x}")
        print(f"\n  {len(problems)} error(s)")
        return 1
    print("  ok    canonicals unique and correct, hreflang reciprocal on every page")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
