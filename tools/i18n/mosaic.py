#!/usr/bin/env python3
"""Generate the Voronoi mesh that draws itself in the pull field.

The mesh in the shells used to be pasted in by hand, and it was built over an
area far taller than the strip that shows it: a quarter of its points sat
outside y 0..96, so cells left the top or the bottom and came back, and what a
reader saw was fragments — cells with pieces missing. This builds the mesh for
the window it is actually seen through.

Two things are deliberate and were asked for: cells get smaller toward the
middle and wider toward the left and right edges, and the spacing is jittered
so the result reads as a web rather than as a grid.

    python3 tools/i18n/mosaic.py            # print the <path> lines
    python3 tools/i18n/mosaic.py --write    # rewrite both shells in place
"""
import math
import random
import re
import sys
import pathlib

W, H = 1440.0, 96.0          # the viewBox the shells declare
BLEED_X, BLEED_TOP, BLEED_BOT = 70.0, 26.0, 26.0
ROW_GAP = 50.0               # ~2 rows inside 96, so whole cells fit in view
GAP_MID, GAP_EDGE = 68.0, 155.0  # column spacing at the centre and at the sides
JITTER = 0.34                # of the local spacing
SEED = 20260831
GROUPS = 4                   # length buckets, matching .pull-g0..g3 in the CSS

ROOT = pathlib.Path(__file__).resolve().parents[2]
SHELLS = ("tools/i18n/templates/_shell.html",
          "tools/i18n/templates/_shell-noindex.html")


def spacing_at(x: float) -> float:
    """Wide at the edges, tight in the middle, easing between the two."""
    t = min(1.0, abs(x - W / 2) / (W / 2))
    return GAP_MID + (GAP_EDGE - GAP_MID) * (t * t * (3 - 2 * t))


def seeds(rng: random.Random):
    pts, y = [], -BLEED_TOP
    row = 0
    while y <= H + BLEED_BOT:
        x = -BLEED_X
        # offset alternate rows so columns never line up into a grid
        x += (ROW_GAP * 0.5) if row % 2 else 0.0
        while x <= W + BLEED_X:
            g = spacing_at(x)
            pts.append((x + rng.uniform(-JITTER, JITTER) * g,
                        y + rng.uniform(-JITTER, JITTER) * ROW_GAP))
            x += g
        y += ROW_GAP
        row += 1
    return pts


def delaunay(pts):
    """Bowyer-Watson. Fine for a few hundred points and keeps the tree free of
    a numeric dependency it would otherwise need for one drawing."""
    minx = min(p[0] for p in pts); maxx = max(p[0] for p in pts)
    miny = min(p[1] for p in pts); maxy = max(p[1] for p in pts)
    dx, dy = maxx - minx, maxy - miny
    d = max(dx, dy) * 12 + 100
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    sup = [(cx - d, cy - d), (cx + d, cy - d), (cx, cy + d)]
    P = list(pts) + sup
    n = len(pts)
    tris = [(n, n + 1, n + 2)]

    def circum(a, b, c):
        ax, ay = P[a]; bx, by = P[b]; cx_, cy_ = P[c]
        d2 = 2 * (ax * (by - cy_) + bx * (cy_ - ay) + cx_ * (ay - by))
        if abs(d2) < 1e-12:
            return None
        ux = ((ax*ax + ay*ay) * (by - cy_) + (bx*bx + by*by) * (cy_ - ay)
              + (cx_*cx_ + cy_*cy_) * (ay - by)) / d2
        uy = ((ax*ax + ay*ay) * (cx_ - bx) + (bx*bx + by*by) * (ax - cx_)
              + (cx_*cx_ + cy_*cy_) * (bx - ax)) / d2
        return ux, uy, math.hypot(ax - ux, ay - uy)

    for i in range(n):
        px, py = P[i]
        bad, keep = [], []
        for t in tris:
            c = circum(*t)
            if c and math.hypot(px - c[0], py - c[1]) <= c[2] + 1e-9:
                bad.append(t)
            else:
                keep.append(t)
        edges = {}
        for a, b, c in bad:
            for e in ((a, b), (b, c), (c, a)):
                k = tuple(sorted(e))
                edges[k] = edges.get(k, 0) + 1
        tris = keep + [(k[0], k[1], i) for k, v in edges.items() if v == 1]
    return [t for t in tris if all(v < n for v in t)], P, circum


def voronoi_edges(pts):
    """The dual: one segment per Delaunay edge shared by two triangles."""
    tris, P, circum = delaunay(pts)
    centres, byedge = {}, {}
    for t in tris:
        c = circum(*t)
        if not c:
            continue
        centres[t] = (c[0], c[1])
        for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            byedge.setdefault(tuple(sorted(e)), []).append(t)
    segs = []
    for _e, ts in byedge.items():
        if len(ts) == 2 and ts[0] in centres and ts[1] in centres:
            a, b = centres[ts[0]], centres[ts[1]]
            if math.dist(a, b) > 0.6:
                segs.append((a, b))
    return segs


def clip(segs):
    """Keep what the window can show, plus a little past every edge so cells
    close against the boundary instead of stopping short of it."""
    x0, x1 = -12.0, W + 12.0
    y0, y1 = -10.0, H + 10.0

    def inside(p):
        return x0 <= p[0] <= x1 and y0 <= p[1] <= y1

    out = []
    for a, b in segs:
        ia, ib = inside(a), inside(b)
        if ia and ib:
            out.append((a, b))
        elif ia or ib:
            # walk the segment to the boundary rather than dropping it, so an
            # edge that leaves the window still reaches it
            p, q = (a, b) if ia else (b, a)
            lo, hi = 0.0, 1.0
            for _ in range(40):
                m = (lo + hi) / 2
                pt = (p[0] + (q[0] - p[0]) * m, p[1] + (q[1] - p[1]) * m)
                if inside(pt):
                    lo = m
                else:
                    hi = m
            out.append((p, (p[0] + (q[0] - p[0]) * lo, p[1] + (q[1] - p[1]) * lo)))
    return out


def chains(segs):
    """Walk the segments into polylines, so each stroke draws as one gesture."""
    def key(p):
        return (round(p[0], 2), round(p[1], 2))

    adj = {}
    for a, b in segs:
        adj.setdefault(key(a), []).append((key(b), a, b))
        adj.setdefault(key(b), []).append((key(a), b, a))
    used, out = set(), []
    for a, b in segs:
        eid = tuple(sorted((key(a), key(b))))
        if eid in used:
            continue
        used.add(eid)
        pts = [a, b]
        for end in (0, 1):
            while True:
                tip = key(pts[0] if end == 0 else pts[-1])
                nxt = None
                for other, frm, to in adj.get(tip, []):
                    cand = tuple(sorted((tip, other)))
                    if cand not in used:
                        nxt = (cand, to)
                        break
                if not nxt:
                    break
                used.add(nxt[0])
                if end == 0:
                    pts.insert(0, nxt[1])
                else:
                    pts.append(nxt[1])
        out.append(pts)
    return out


def d_attr(pts, rng) -> str:
    """Straight edges with a breath of bow in them.

    The corners are the point: a Voronoi cell is a polygon, and rounding its
    vertices turns the mesh into scallops. So every vertex stays sharp and the
    curve lives in the middle of each edge — a quadratic whose control point is
    the midpoint pushed a couple of percent off the straight line. Enough that
    no two edges read as machined, not enough to lose the tessellation.
    """
    def f(v):
        return f"{v:.1f}".rstrip("0").rstrip(".")
    out = [f"M{f(pts[0][0])} {f(pts[0][1])}"]
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        mx, my = (ax + bx) / 2, (ay + by) / 2
        dx, dy = bx - ax, by - ay
        n = math.hypot(dx, dy) or 1.0
        bow = rng.uniform(-0.035, 0.035) * n
        cx, cy = mx - dy / n * bow, my + dx / n * bow
        out.append(f"Q{f(cx)} {f(cy)} {f(bx)} {f(by)}")
    return "".join(out)


def length(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def build():
    rng = random.Random(SEED)
    ch = [c for c in chains(clip(voronoi_edges(seeds(rng)))) if length(c) > 8]
    ch.sort(key=length, reverse=True)
    per = math.ceil(len(ch) / GROUPS)
    lines, longest = [], []
    for g in range(GROUPS):
        bucket = ch[g * per:(g + 1) * per]
        if not bucket:
            continue
        cls = f"pull-a pull-g{g}" if g == 0 else f"pull-n pull-g{g}"
        longest.append((g, max(length(c) for c in bucket), len(bucket)))
        for c in bucket:
            lines.append(f'     <path class="{cls}" d="{d_attr(c, rng)}"/>')
    return lines, longest


def main():
    lines, longest = build()
    for g, ln, n in longest:
        print(f"# g{g}: {n} catene, la piu' lunga {ln:.0f} unita", file=sys.stderr)
    block = "\n".join(lines)
    if "--write" not in sys.argv:
        print(block)
        return
    for rel in SHELLS:
        p = ROOT / rel
        s = p.read_text()
        new = re.sub(r'( *<path class="pull-[^"]*" d="[^"]*"/>\n)+',
                     block + "\n", s, count=1)
        p.write_text(new)
        print(f"scritto {rel}", file=sys.stderr)


if __name__ == "__main__":
    main()
