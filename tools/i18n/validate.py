#!/usr/bin/env python3
"""Check every translation against the English source, before it becomes HTML.

build.py already refuses to run on a missing key. This catches the failures that
are not missing keys — the ones that produce a page which renders, looks
plausible, and is wrong in a language nobody on the team reads:

  - a <strong> that was dropped, or an &nbsp; that became a normal space
  - a sentence fragment that lost the leading space the template joins on, so
    the text runs into the link
  - an email address, a VAT number or a product name that got "translated"
  - an invisible bidi override pasted in from a right-to-left editor
  - an array that came back with three items where English has four

    python3 tools/i18n/validate.py           # all languages
    python3 tools/i18n/validate.py it de     # just these
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
CONTENT = HERE / "content"
SOURCE = "en"

# Must appear, unchanged, in the translation wherever it appears in the English.
# Not a style preference: these are identifiers, addresses and product names, and
# a "translated" one is a broken link or a wrong company.
LITERAL = [
    "Spinne Software", "Sparkle", "sparkle.software", "spinnesoftware.com",
    "hello@spinnesoftware.com", "spinnesoftware@pec.it",
    "IT 18636231005", "RM-1797481", "Registro Imprese",
    "GitHub", "Fastly", "Stripe", "OpenRouter", "Deepgram", "fal.ai",
    "Higgsfield", "Whisper", "ONNX Runtime", "NVENC", "Quick Sync",
    "VideoToolbox", "H.264", "HEVC", "AV1", "DNxHR", "HDR", "EBU R128",
    "SOC 2", "ISO/IEC 27001", "LinkedIn", "x264", "x265", "SVT-AV1",
]

# Markup that must survive token-for-token.
TOKENS = ["<strong>", "</strong>", "<em>", "</em>", "&middot;", "&nbsp;", "&copy;"]

# NOTE: there is no fragment-join check here, and there were two.
# The first compared each fragment's edge whitespace to English and reported 22
# correct values as broken, because Chinese and Japanese use no inter-word
# spaces, German puts none before a comma and French puts one before a
# semicolon. The second read the templates to find which fragments abut a tag
# and reported 2,849, because it could not tell a sentence continuing into a
# link from a <title> element abutting its own tags.
# The check now lives in check.sh, where it reads the RENDERED page and looks at
# the actual joined sentence. A test that keeps being wrong about the input
# belongs on the output.

# Invisible characters that change rendering and never show up in review.
def invisible(text: str):
    for ch in text:
        o = ord(ch)
        if 0x200B <= o <= 0x200F or 0x202A <= o <= 0x202E or o in (0x2060, 0xFEFF):
            yield f"U+{o:04X}"


def walk(node, path=""):
    """Yield (dotted path, string) for every leaf string."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}.{i}")
    elif isinstance(node, str):
        yield path, node


def shape(node, path=""):
    """Yield (path, kind) so a list that lost an item is caught as a shape
    difference rather than as a missing key."""
    if isinstance(node, dict):
        yield path, "dict"
        for k, v in node.items():
            yield from shape(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        yield path, f"list[{len(node)}]"
        for i, v in enumerate(node):
            yield from shape(v, f"{path}.{i}")
    else:
        yield path, "str"


def main(argv) -> int:
    src = json.loads((CONTENT / f"{SOURCE}.json").read_text(encoding="utf-8"))
    src_shape = dict(shape(src))
    src_text = dict(walk(src))

    wanted = argv[1:] or sorted(
        p.stem for p in CONTENT.glob("*.json") if p.stem != SOURCE
    )

    total_problems = 0
    for lang in wanted:
        path = CONTENT / f"{lang}.json"
        if not path.exists():
            print(f"{lang:<8} MISSING {path}")
            total_problems += 1
            continue

        raw = path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"{lang:<8} INVALID JSON: {e}")
            total_problems += 1
            continue

        problems = []

        # 1. Same shape, including array lengths.
        got_shape = dict(shape(data))
        for k, kind in src_shape.items():
            if k == "_note":
                continue
            if k not in got_shape:
                problems.append(f"missing key   {k}")
            elif got_shape[k] != kind:
                problems.append(f"shape {kind} -> {got_shape[k]}   {k}")
        for k in got_shape:
            if k not in src_shape and not k.startswith("_"):
                problems.append(f"extra key     {k}")

        text = dict(walk(data))

        for key, en in src_text.items():
            if key == "_note" or key not in text:
                continue
            tr = text[key]

            # 2. Markup survives token for token.
            for tok in TOKENS:
                if en.count(tok) != tr.count(tok):
                    problems.append(
                        f"{tok} x{en.count(tok)} -> x{tr.count(tok)}   {key}")

            # 3. Identifiers and product names survive verbatim.
            for lit in LITERAL:
                if lit in en and lit not in tr:
                    problems.append(f"lost literal {lit!r}   {key}")

            # 4. Joining. These fragments are concatenated around a link, and a
            #    fragment that loses its edge space runs into it.
            #
            #    Comparing the whitespace to English is the WRONG test and was
            #    the first thing this script did: it flagged 22 values across
            #    Chinese, Japanese, Korean, German, French, Russian and Bengali,
            #    every one of them correct. Chinese and Japanese do not put
            #    spaces between words at all; German puts none before a comma;
            #    French puts one before a semicolon where English puts none.
            #    So the test is whether the JOIN works in that language, not
            #    whether it matches English.
            if "  " in tr:
                problems.append(f"double space            {key}")

            # 5. Untranslated. Identical long prose is almost always a value the
            #    translator skipped, not a coincidence.
            if len(en) > 60 and en == tr:
                problems.append(f"identical to English    {key}")

        # 6. Invisible characters, anywhere in the file.
        for key, tr in text.items():
            found = sorted(set(invisible(tr)))
            if found:
                problems.append(f"invisible {', '.join(found)}   {key}")

        # 7. What scripts does this file actually use? Reported, not judged —
        #    it is how you notice a Cyrillic 'а' hiding in a Latin word.
        scripts = {}
        for _key, tr in text.items():
            for ch in tr:
                if ch.isalpha():
                    name = unicodedata.name(ch, "?").split()[0]
                    scripts[name] = scripts.get(name, 0) + 1
        top = ", ".join(f"{k} {v}" for k, v in
                        sorted(scripts.items(), key=lambda x: -x[1])[:3])

        if problems:
            print(f"{lang:<8} {len(problems)} PROBLEM(S)   [{top}]")
            for p in problems[:25]:
                print(f"         - {p}")
            if len(problems) > 25:
                print(f"         ... and {len(problems) - 25} more")
            total_problems += len(problems)
        else:
            print(f"{lang:<8} ok   {len(text)} strings   [{top}]")

    print()
    if total_problems:
        print(f"  {total_problems} problem(s) across {len(wanted)} language(s)")
        return 1
    print(f"  all {len(wanted)} language(s) match the English source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
