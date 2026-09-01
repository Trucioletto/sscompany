#!/usr/bin/env python3
"""Set the motto in the pull field, and open the weave to make room for it.

Both halves are here because they are one decision. The three words in the blue
field are a filled outline, and the mesh around them fades out as it reaches
them: a solid word on a lattice with threads running through its counters is a
blot, and an opening in the mesh with nothing in it is a bald patch. Neither
half works without the other.

Which is why this writes ONE <path> and the shell uses it five times — four
widening copies inside the mask that open the weave, and the visible one under
them. The opening is the letters, dilated; there is no second shape to size and
nothing to keep in step when the phrase or the face changes. An ellipse was
tried for it first and was the wrong idea rather than the wrong number: sized
to clear the line on a desktop it swallowed the whole strip on a phone, where
the words are two thirds of the width and the mesh a reader came for went with
it.

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

    parts = []
    ink = BoundsPen(glyphs)
    for name, advance in zip(names, advances):
        transform = Transform(scale, 0, 0, -scale, x, baseline)
        svg = SVGPathPen(glyphs, ntos=lambda v: f"{v:.1f}")
        glyphs[name].draw(TransformPen(svg, transform))
        d = svg.getCommands()
        if d.strip():
            parts.append(d)
            glyphs[name].draw(TransformPen(ink, transform))
        x += advance

    x0, y0, x1, y1 = ink.bounds
    d = "".join(parts)
    meta = dict(size=round(size, 2), width=round(width, 1), baseline=round(baseline, 2),
                ink=[round(v, 1) for v in (x0, y0, x1, y1)],
                chars=len(d))
    return d, meta


def main():
    d, meta = build()
    # ONE definition, five uses: four inside the mask that open the weave, and
    # the visible one under it. The opening is derived from these same outlines
    # rather than from a shape of its own — see the halo note in style.css — so
    # there is nothing here to keep in step with the type.
    line = f'      <path id="pull-word-d" d="{d}"/>\n'
    print(json.dumps(meta, indent=1), file=sys.stderr)
    if "--write" not in sys.argv:
        print(line, end="")
        return
    for rel in SHELLS:
        p = ROOT / rel
        s = p.read_text()
        s, n = re.subn(r' *<path id="pull-word-d" d="[^"]*"/>\n', line, s, count=1)
        if n != 1:
            raise SystemExit(f"{rel}: found {n} motto definitions, expected 1")
        p.write_text(s)
        print(f"scritto {rel}", file=sys.stderr)


if __name__ == "__main__":
    main()
