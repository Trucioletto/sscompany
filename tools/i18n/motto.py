#!/usr/bin/env python3
"""Set the motto in the pull field, and open the weave to make room for it.

Both halves are here because they are one decision. The three words in the blue
field are a filled outline, and the mesh around them fades out as it reaches
them: a solid word on a lattice with threads running through its counters is a
blot, and an opening in the mesh with nothing in it is a bald patch. Neither
half works without the other.

Which is why the mesh is not cut away for them. Two shapes were tried for that
— an ellipse, then the letters dilated into a halo — and both overshoot by
construction: the clearing is always bigger than the ink, so the weave stops
short of the words and the two read as separate objects. A mask is also static
while the phrase fades in, so it cut word-shaped holes into the field a third
of a gesture before there was anything to put in them.

An opaque shape painted after the mesh needs none of it. It hides exactly its
own outline, and it hides it on exactly the frames it is visible.

FOUR VERSIONS CAME BEFORE THIS ONE. They are worth recording because each was
the obvious next thing to try, and the last two were only wrong in a way you
can see rather than reason about.

  1. An HTML div laid over the field, display serif, near-white, label size.
     A sticker: it shared none of the field's material.
  2. An SVG <text> stroked in the mesh's own colour. Right material, but the
     letterforms are then whatever face the browser actually loaded.
  3. Outlines, stroked. That fixes the face — and is still hollow. An unfilled
     letter on a field of unfilled cells has nothing to tell it from the cells,
     so the phrase had to be hunted for rather than read.
  4. Uppercase, at 2 and 3. A row of capitals is the one rigid thing in a
     tessellation where no two cells are alike, and it read as a stamp laid
     across the weave rather than as anything belonging to it.

    THE FACE. Marcellus (Brian J. Bonislawsky, Astigmatic), SIL Open Font
    License 1.1 — see fonts/OFL-Marcellus.txt. Inscriptional: cut rather than
    written, which is the quality that was actually wanted. It was rejected
    once, while the words were still outlines, on the ground that outlined at
    1px a serif is mostly bracket and stress and reads as a wobble. That
    objection died with the outline. Filled, the same modelling is the whole
    point of it.

    The file in fonts/ is that face subset to the nine glyphs this phrase uses,
    2KB rather than 48. It is a build input and is never served — what ships is
    the outline data below, so there is no third face on a site that ships two,
    no request, and no way for the shapes to differ between one reader and the
    next. To rebuild it from upstream:

        curl -O https://raw.githubusercontent.com/google/fonts/main/ofl/\\
              marcellus/Marcellus-Regular.ttf
        pyftsubset Marcellus-Regular.ttf --text="Weave the web" \\
              --output-file=Marcellus-motto.ttf --layout-features='' \\
              --no-hinting --desubroutinize

    LOWER CASE, and not as a preference. See failure 4 above. It is also the
    casing the home page sets the phrase in, so this is the same mark and not a
    second treatment of it — and the phrase carries no descender at all, which
    is what lets it sit as low in the band as it does.

    python3 tools/i18n/motto.py            # print the two lines
    python3 tools/i18n/motto.py --write    # rewrite both shells in place
"""
import json
import pathlib
import re
import sys

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.misc.transform import Transform

TEXT = "Weave the web"

# The viewBox the shells declare, and the centre of the band inside it that a
# reader ever sees. The field is 96 tall and the pull is 64, so the top 32 is
# margin that exists only so the field's own top edge is never reached — see
# the note over .pull-field. Centring in 96 would put the line 16px above the
# middle of the only part that is ever on screen.
W, H = 1440.0, 96.0
MAX_PULL = 64.0
BAND_CENTRE = H - MAX_PULL / 2.0          # 64.0

# x-height, not size. It is what the eye reads as the size of a lower case
# line, and the only number that means the same thing in two faces with
# different em squares — which is what made the seven candidates comparable.
X_HEIGHT = 15.5
TRACK = 0.03      # em. Inscriptional letters want air; much past this and the
                  # line stops being a phrase and becomes a row of letters.

# Optical centring. The mass of a lower case line sits between the baseline and
# the ascender, so that box is what gets centred — but centred on it
# geometrically the line reads low, because the x-height mass is nearer the
# baseline than the ascender. 1.7px of lift is what settled it against the mesh.
LIFT = 1.7

ROOT = pathlib.Path(__file__).resolve().parents[2]
FONT = pathlib.Path(__file__).resolve().parent / "fonts" / "Marcellus-motto.ttf"
SHELLS = ("tools/i18n/templates/_shell.html",
          "tools/i18n/templates/_shell-noindex.html")


def _contour_area(d):
    """Signed area of one subpath, from its on-curve points alone.

    The control points are ignored on purpose. This only has to tell an outer
    contour from a counter, and no bezier ever crosses its own hull far enough
    to flip that sign.
    """
    nums = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', d)]
    pts = list(zip(nums[0::2], nums[1::2]))
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return a / 2


def counters_only(d):
    """The glyph's counters — the holes in it — and nothing else.

    A filled letter hides the mesh behind its INK and not behind its counters:
    the eye of an `e` is a hole in the shape, so a thread crossing it stays
    visible inside the letter as a fragment with no cause. Measured on the
    built page at 8x, that happened in the e of `Weave`, both e's of `the` and
    `web`, and the bowl of the b.

    So the counters are painted in the field's own colour and the letters go on
    top. It covers exactly the holes — not a pixel outside the outline, because
    a counter has no outside — and it belongs to the same element as the type,
    so it arrives on the frames the type does.

    Counters only, rather than a whole silhouette behind the letters: the ink
    already covers itself, so a silhouette would be six thousand characters of
    path data restating what the next path draws anyway. These are six small
    closed loops.

    They are the contours wound against the largest one in their glyph. In
    TrueType the two are wound oppositely under the nonzero rule, so the sign of
    the area is the whole test.
    """
    subs = ["M" + part for part in d.split("M") if part.strip()]
    if len(subs) < 2:
        return ""
    areas = [_contour_area(sp) for sp in subs]
    outer = 1 if max(areas, key=abs) > 0 else -1
    return "".join(sp for sp, a in zip(subs, areas) if (1 if a > 0 else -1) != outer)


def build():
    font = TTFont(FONT)
    upm = font["head"].unitsPerEm
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]

    def raw_bounds(ch):
        pen = BoundsPen(glyphs)
        glyphs[cmap[ord(ch)]].draw(pen)
        return pen.bounds

    size = X_HEIGHT / ((raw_bounds("e")[3] - raw_bounds("e")[1]) / upm)
    scale = size / upm
    ascender = raw_bounds("h")[3] / upm * size
    baseline = BAND_CENTRE + ascender / 2 - LIFT

    names = [cmap[ord(c)] for c in TEXT]
    advances = [hmtx[n][0] * scale + TRACK * size for n in names]
    # The trailing track is laid to the right of the last letter like every
    # other, and a line centred on the advance width would sit half a step left
    # of centre. Dropping it is the whole correction, and it is one more thing
    # baked geometry settles that live text needs a dx to fix.
    width = sum(advances) - TRACK * size
    x = W / 2 - width / 2

    parts, solids = [], []
    ink = BoundsPen(glyphs)
    for name, advance in zip(names, advances):
        transform = Transform(scale, 0, 0, -scale, x, baseline)
        svg = SVGPathPen(glyphs, ntos=lambda v: f"{v:.1f}")
        glyphs[name].draw(TransformPen(svg, transform))
        d = svg.getCommands()
        if d.strip():
            parts.append(d)
            solids.append(counters_only(d))
            glyphs[name].draw(TransformPen(ink, transform))
        x += advance

    x0, y0, x1, y1 = ink.bounds
    d, solid = "".join(parts), "".join(solids)
    meta = dict(size=round(size, 2), width=round(width, 1), baseline=round(baseline, 2),
                ink=[round(v, 1) for v in (x0, y0, x1, y1)],
                chars=len(d), counterChars=len(solid))
    return d, solid, meta


def main():
    d, solid, meta = build()
    # One path, painted after the mesh and opaque, which is the whole of it.
    # There was a mask here that cut the weave open around the letters and it is
    # gone — see the note over .pull-word in style.css. A solid shape drawn on
    # top already hides exactly what is behind it, on exactly the frames it is
    # visible, which is both more precise than a dilated outline and correct
    # during the fade in a way a static mask cannot be.
    line = (f'     <path class="pull-word pull-word-counters" d="{solid}"/>\n'
            f'     <path class="pull-word" d="{d}"/>\n')
    print(json.dumps(meta, indent=1), file=sys.stderr)
    if "--write" not in sys.argv:
        print(line, end="")
        return
    for rel in SHELLS:
        p = ROOT / rel
        s = p.read_text()
        s, n = re.subn(r'( *<path class="pull-word pull-word-counters" d="[^"]*"/>\n)?'
                       r' *<path class="pull-word" d="[^"]*"/>\n', line, s, count=1)
        if n != 1:
            raise SystemExit(f"{rel}: found {n} motto definitions, expected 1")
        p.write_text(s)
        print(f"scritto {rel}", file=sys.stderr)


if __name__ == "__main__":
    main()
