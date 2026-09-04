#!/usr/bin/env python3
"""Regenerate the two self-hosted font subsets, and the @font-face rules for them.

The site went from two languages to fifteen. The shipped subsets carried 120 and
111 codepoints — ASCII, the five Italian accented vowels and some punctuation —
so Spanish, French, German, Portuguese and Russian would each have fallen back
to a system face PER CHARACTER, mid-word, wherever an accent appeared. That is
uglier than not using the webfont at all, and `check.sh` fails the build on it.

WHAT THIS PRODUCES

  fonts/inter-latin.woff2       Latin, Latin-1 Supplement, Latin Extended-A
  fonts/inter-cyrillic.woff2    Cyrillic, for Russian
  fonts/fraunces-latin.woff2    Latin only — Fraunces has no Cyrillic at all

Two files per script rather than one big one, which is how Google Fonts serves
the same families and is strictly better here: a Spanish reader downloads the
Latin file and never sees the Cyrillic one, because the browser matches on
`unicode-range` before it fetches. One merged file would have made every reader
pay for every alphabet.

Han, Kana, Hangul, Arabic, Devanagari and Bengali are NOT here and cannot be:
neither binary contains those glyphs, and subsetting cannot add what is not in
the source. Those six scripts are served by the reader's own system fonts — see
the `.script-*` stacks in style.css.

    python3 tools/i18n/fonts.py --src <dir with Inter.ttf and Fraunces.ttf>

The sources are NOT committed: they are 880 KB and 384 KB of upstream release,
and the repository ships only what the browser asks for. Fetch them from
github.com/rsms/inter and github.com/undercasetype/Fraunces.

Prints the @font-face block to paste into style.css. The unicode-range in it is
generated FROM the produced binary, never written by hand — declaring a
codepoint the file lacks makes the browser drop the whole font for that
character, which is the exact failure this script exists to prevent.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "fonts"

# Latin: everything the seven Latin-script languages on this site need, plus the
# punctuation the copy uses.
#
# Latin-1 Supplement is taken WHOLE — es, fr, de, pt and it live in it, it is
# only 96 codepoints, and picking it over is how you discover a year later that
# one language needed one letter you left out.
#
# Latin Extended-A is NOT taken whole, and that is worth 122 glyphs. None of the
# fifteen languages here needs it except French, which needs exactly three
# characters from it. Including the block for Turkish, Polish and Czech headroom
# cost 30% of the file for languages this site does not have. If one is added
# later, add the range back here and rerun — that is a two-line change, and a
# smaller price than every reader paying for it in the meantime.
LATIN = [
    (0x0020, 0x007E),   # ASCII
    (0x00A0, 0x00FF),   # Latin-1 Supplement: accents for es/fr/de/pt/it
    (0x0152, 0x0153),   # OE, oe — French
    (0x0178, 0x0178),   # Y with diaeresis — French
    (0x2013, 0x2014),   # en dash, em dash
    (0x2018, 0x2019),   # curly single quotes
    (0x201C, 0x201D),   # curly double quotes
    (0x2022, 0x2022),   # bullet
    (0x2026, 0x2026),   # ellipsis
    (0x2039, 0x203A),   # single guillemets, used in French
    (0x20AC, 0x20AC),   # euro
]

CYRILLIC = [
    (0x0400, 0x045F),   # Russian and its neighbours
    (0x0490, 0x0491),   # Ukrainian ghe with upturn, cheap headroom
]

TARGETS = [
    # name,                 source,          ranges,   axis pins
    ("inter-latin",     "Inter.ttf",    LATIN,    {"opsz": 14}, {"wght": (400, 600)}),
    ("inter-cyrillic",  "Inter.ttf",    CYRILLIC, {"opsz": 14}, {"wght": (400, 600)}),
    # Fraunces is pinned to one point in its variable space: wght 600, opsz 48,
    # and the two axes that give it its character, SOFT 40 and WONK 1. Nothing
    # ships that a heading cannot use.
    ("fraunces-latin",  "Fraunces.ttf", LATIN,
     {"wght": 600, "opsz": 48, "SOFT": 40, "WONK": 1}, {}),
    # The italic is a SEPARATE upstream file — Fraunces has no ital axis, so no
    # amount of instancing the roman produces one, and font-synthesis is off site
    # wide precisely so the browser does not shear one out of it (see the comment
    # at the top of style.css). It carries one string, the motto, on the home page
    # of fifteen languages: same pins as the roman so the two faces sit at the
    # same optical size and weight, and the same LATIN subset, which is 35 KB.
    #
    # Fetch Fraunces-Italic[SOFT,WONK,opsz,wght].ttf from
    # github.com/undercasetype/Fraunces, rename it Fraunces-Italic.ttf, and put it
    # beside the other sources. Until it is there this target is skipped rather
    # than failing the run.
    ("fraunces-latin-italic", "Fraunces-Italic.ttf", LATIN,
     {"wght": 600, "opsz": 48, "SOFT": 40, "WONK": 1}, {}),
]

# Sources whose absence is not an error. Everything the site ships today is built
# from Inter.ttf and Fraunces.ttf; the italic carries one string and is a choice,
# so a machine that has only the two required files can still regenerate the
# subsets it needs instead of failing on the one it does not want.
OPTIONAL_SOURCES = {"Fraunces-Italic.ttf"}


def codepoints(ranges) -> set[int]:
    out = set()
    for lo, hi in ranges:
        out.update(range(lo, hi + 1))
    return out


def unicode_range(font_path: pathlib.Path) -> str:
    """Read the produced file back and describe exactly what is in it."""
    font = TTFont(font_path)
    cps = set()
    for table in font["cmap"].tables:
        cps.update(table.cmap.keys())
    runs, start, prev = [], None, None
    for cp in sorted(cps):
        if start is None:
            start = prev = cp
        elif cp == prev + 1:
            prev = cp
        else:
            runs.append((start, prev))
            start = prev = cp
    if start is not None:
        runs.append((start, prev))
    return ", ".join(
        f"U+{a:04X}" if a == b else f"U+{a:04X}-{b:04X}" for a, b in runs
    )


def build(src_dir: pathlib.Path) -> int:
    OUT.mkdir(exist_ok=True)
    faces = []

    for name, source, ranges, pins, limits in TARGETS:
        src = src_dir / source
        if not src.exists():
            if source in OPTIONAL_SOURCES:
                print(f"  skipped {name}: {source} not in {src_dir}")
                continue
            print(f"  MISSING source: {src}", file=sys.stderr)
            return 1

        font = TTFont(src)
        axes = {a.axisTag for a in font["fvar"].axes} if "fvar" in font else set()

        spec = {k: v for k, v in pins.items() if k in axes}
        spec.update({k: v for k, v in limits.items() if k in axes})

        # SUBSET FIRST, INSTANCE SECOND. The other order raises
        # KeyError: 'uni00A0.tf' — instancing rewrites `gvar` while the tabular
        # -figure alternates are still reachable through the `tnum` feature, and
        # the subsetter then looks for variation data that instancing removed.
        # Dropping `tnum` would also silence it and would silently take tabular
        # figures away from the colophon and the fact tables, which are the two
        # places on the site that hold identifiers in columns.
        wanted = codepoints(ranges)
        have = set()
        for table in font["cmap"].tables:
            have.update(table.cmap.keys())
        keep = wanted & have
        if not keep:
            print(f"  {name}: source has none of the requested range — skipped")
            continue

        opts = subset.Options()
        opts.flavor = "woff2"
        opts.retain_gids = False
        opts.desubroutinize = True
        opts.layout_features = ["kern", "liga", "clig", "calt", "ccmp", "locl",
                                "mark", "mkmk", "tnum", "case"]
        opts.name_IDs = ["*"]
        opts.name_legacy = False
        opts.notdef_outline = False
        opts.recalc_bounds = True
        subsetter = subset.Subsetter(options=opts)
        subsetter.populate(unicodes=keep)
        subsetter.subset(font)

        if spec:
            font = instancer.instantiateVariableFont(font, spec, updateFontNames=False)

        dest = OUT / f"{name}.woff2"
        font.save(dest)

        still_variable = "fvar" in TTFont(dest)
        family = "Inter" if name.startswith("inter") else "Fraunces"
        weight = "400 600" if family == "Inter" else "600"
        # The style comes from the source file, not from a flag: a face built from
        # Fraunces-Italic.ttf declared font-style: normal would be a second roman
        # as far as the browser is concerned, and the italic would never be picked.
        style = "italic" if "Italic" in source else "normal"
        faces.append((family, style, weight, f"fonts/{name}.woff2", unicode_range(dest)))
        print(f"  {name:<18} {dest.stat().st_size / 1024:6.1f} KB  "
              f"{len(keep):>4} glyphs  {'variable' if still_variable else 'static'}")

    print("\n--- @font-face block for style.css "
          "(unicode-range read back from each binary) ---\n")
    for family, style, weight, path, urange in faces:
        print("@font-face {")
        print(f'  font-family: "{family}";')
        print(f"  font-style: {style};")
        print(f"  font-weight: {weight};")
        print("  font-display: optional;")
        print(f'  src: url("{path}") format("woff2");')
        print(f"  unicode-range: {urange};")
        print("}\n")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, type=pathlib.Path,
                    help="directory containing Inter.ttf and Fraunces.ttf")
    raise SystemExit(build(ap.parse_args().src))
