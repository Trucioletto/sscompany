#!/usr/bin/env python3
"""Is a repeated English term rendered the same way every time, in each language?

The site turns on a small number of load-bearing words. "machinery" is the
metaphor the home page is built around and appears on four pages; "private
preview" is the product's status and appears five times; "the cut" is the
promise Sparkle makes to an editor. If one of them comes back three different
ways in one language, the reader does not meet a metaphor — they meet three
unrelated words, and the page stops arguing anything.

This cannot check that a translation is CORRECT; fourteen reviewers did that.
It checks that it is CONSISTENT, which is the part a script can see and a
reviewer reading one page at a time cannot.

    python3 tools/i18n/consistency.py          # every language
    python3 tools/i18n/consistency.py de ja    # just these
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
CONTENT = HERE / "content"

# Deliberately short. A list of every noun would bury the real findings.
TERMS = [
    # Down to a single use, on /about/, since the home page was rewritten around
    # the six values: the h1 it anchored ("every product leaves machinery
    # behind") is gone and the home no longer inventories the plumbing. One use
    # cannot be inconsistent with itself, so this term now falls out of the
    # report — it is kept here because the word will come back the moment a
    # second product exists, and dropping it would lose the reason it is watched.
    "machinery",
    "private preview",
    # /how-we-build/ turns on this one. The brief says it must be the same word
    # every time and must be the physical join of two things, never a gap. Four
    # of the five uses are on that page and the fifth is its og:description, so
    # a language that drifted between two renderings shows up here as a dash.
    "seam",
    "ledger",
    "diligence",
    "sole proprietorship",
    "data controller",
    "legitimate interest",
    "supervisory authority",
]


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}.{i}")
    elif isinstance(node, str):
        yield path, node


def main(argv) -> int:
    en = dict(walk(json.loads((CONTENT / "en.json").read_text(encoding="utf-8"))))

    where = {}
    for term in TERMS:
        keys = [k for k, v in en.items()
                if re.search(rf"\b{re.escape(term)}\b", v, re.I)]
        if len(keys) > 1:
            where[term] = keys

    langs = argv[1:] or sorted(p.stem for p in CONTENT.glob("*.json")
                               if p.stem != "en")
    data = {l: dict(walk(json.loads((CONTENT / f"{l}.json").read_text(encoding="utf-8"))))
            for l in langs}

    print("  The longest run of characters shared by every string that carries")
    print("  the term in English. A dash means they share nothing.")
    print()
    print("  READ THIS AS A POINTER, NOT AS THE RENDERING. The run is whatever")
    print("  the strings happen to have in common, which is not always the term:")
    print("  a column often shows an ordinary word that co-occurs in every")
    print("  sentence carrying the term, rather than the term itself. A row that")
    print("  looks wrong here has usually been read by hand and is fine; a term")
    print("  that has dropped to one use disappears from the table entirely,")
    print("  because one use cannot disagree with itself.")
    print("  An attempt to filter ordinary vocabulary")
    print("  out of this column made two other rows worse and was removed; the")
    print("  honest version of this tool says where to look and stops there.")
    print(f"  {'term':<22}{'uses':>5}   " + "".join(f"{l:>8}" for l in langs))

    def longest_common(values, min_len):
        """The longest run of characters present in every value whose trimmed
        length still clears min_len.

        Two bugs lived here. The first was an off-by-one that returned a
        3-character function word for a term rendered identically in all three
        places. The second was subtler and survived the fix: the longest common
        run often INCLUDES the spaces around a function word — " aur " is five
        characters — so returning the longest and trimming afterwards reported
        the same false negative by a different route. The length that matters is
        the trimmed one, so it has to be the thing being maximised."""
        if not values or not all(values):
            return ""
        first, rest = values[0], values[1:]
        n = len(first)
        for length in range(n, 1, -1):
            for i in range(0, n - length + 1):
                cand = first[i:i + length]
                if len(cand.strip()) < min_len:
                    continue
                if all(cand in v for v in rest):
                    return cand.strip()
        return ""

    look = []
    for term, keys in where.items():
        row = ""
        for lang in langs:
            d = data[lang]
            vals = [d.get(k, "") for k in keys]
            # Two characters of Han or Hangul is a word; two Latin letters are
            # not. Scale the bar to the script rather than to the count.
            dense = any(ord(c) > 0x2E7F for v in vals for c in v)
            # An abjad sits between the two. Arabic and Urdu write the short
            # vowels as nothing, so a three-letter root IS a whole word: درز is
            # the seam, جوڑ is the join. At a bar of four this reported "no
            # shared word" for Arabic when all six occurrences were the same
            # three letters — a false negative produced entirely by the script's
            # morphology.
            abjad = any(0x0600 <= ord(c) <= 0x06FF for v in vals for c in v)
            shared = longest_common(vals, 2 if dense else 3 if abjad else 4)
            row += f"{(shared[:10] if shared else '-'):>12}"
            if not shared:
                look.append((term, lang))
        print(f"  {term:<22}{len(keys):>5}   {row}")

    print()
    if look:
        by_term = {}
        for term, lang in look:
            by_term.setdefault(term, []).append(lang)
        for term, ls in by_term.items():
            print(f"  look at {term!r}: no shared word in {', '.join(ls)}")
    print()
    print("  A zero is not automatically wrong. Some languages inflect a noun")
    print("  differently in every sentence it appears in, and some terms are")
    print("  properly rendered by a phrase rather than a word. This marks where")
    print("  to LOOK; it does not decide anything.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
