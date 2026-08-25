#!/usr/bin/env python3
"""Measure the masthead and the footer at every narrow width, in every language.

sweep.py answers "does anything overflow". That is the floor, not the bar. The
two bands that frame every page are the ones that break first and the ones a
visitor sees before anything else, and they break differently per language: the
nav is five words in English and five much longer words in German, the footer
headings are short in Chinese and long in Russian, and the whole thing mirrors
in Arabic and Urdu.

So this walks the width axis in small steps rather than sampling four points,
and reports numbers: how tall the masthead got, how many rows the nav wrapped
to, how close two tap targets came, whether a box escaped its container. A
breakpoint hole shows up here as a width where a number jumps.

    python3 tools/i18n/edges.py            # every language, home page
    python3 tools/i18n/edges.py de ar      # just these
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile

import sweep  # free_port, Tab, CHROME, ROOT

# Dense through the phone range, where the layout actually has to work, and
# thinner above it. 320 is the narrowest device still in the statistics; 430 is
# a large phone; 768 is where the two-column rail returns.
WIDTHS = [320, 340, 360, 375, 390, 412, 430, 480, 540, 600, 680, 768]

# Two targets closer than this read as one control. WCAG 2.5.8 measures the
# target; this measures the space between two of them, which is the thing that
# makes a thumb hit the wrong one.
MIN_GAP = 8.0

PROBE = r"""
(() => {
  const out = {};
  const box = el => { const r = el.getBoundingClientRect();
    return {x: r.x, y: r.y, w: r.width, h: r.height, r: r.right, b: r.bottom}; };
  const rows = els => {                       // how many visual rows they wrap to
    const tops = new Set();
    for (const e of els) tops.add(Math.round(e.getBoundingClientRect().top));
    return tops.size;
  };
  // Two kinds of neighbour, and only one of them is a problem.
  //
  // Links stacked in a list SHOULD have touching boxes: a gap between them is a
  // dead strip where a tap does nothing, which is worse than contiguity. The
  // first version of this flagged every footer list at 0px and called it a
  // finding — it was measuring the normal case.
  //
  // Side by side is different. Two controls on one row with nothing between them
  // is where a thumb lands on the wrong one, so horizontal proximity is reported
  // and vertical is only summarised.
  const closest = els => {
    let minX = Infinity, pairX = null, minY = Infinity;
    const bs = els.map(e => [e, e.getBoundingClientRect()]);
    const label = e => (e.textContent||'').trim().slice(0,18);
    for (let i = 0; i < bs.length; i++) for (let j = i + 1; j < bs.length; j++) {
      const [ea, a] = bs[i], [eb, b] = bs[j];
      const overlapY = a.top < b.bottom && b.top < a.bottom;   // same row
      const overlapX = a.left < b.right && b.left < a.right;   // same column
      if (overlapY) {
        const dx = Math.max(a.left - b.right, b.left - a.right);
        if (dx < minX) { minX = dx; pairX = [label(ea), label(eb)]; }
      } else if (overlapX) {
        minY = Math.min(minY, Math.max(a.top - b.bottom, b.top - a.bottom));
      }
    }
    return {gapX: minX === Infinity ? null : Math.round(minX*10)/10, pairX,
            gapY: minY === Infinity ? null : Math.round(minY*10)/10};
  };

  const mast = document.querySelector('.masthead');
  const navLinks = [...document.querySelectorAll('.site-nav a')];
  const mark = document.querySelector('.mark');
  const lang = document.querySelector('details.lang, .lang');
  out.masthead = {
    h: Math.round(mast.getBoundingClientRect().height),
    navRows: rows(navLinks),
    navCount: navLinks.length,
    close: closest(navLinks),
    markBox: mark ? box(mark) : null,
    langBox: lang ? box(lang) : null,
  };

  const foot = document.querySelector('footer');
  const cols = [...document.querySelectorAll('.footer-col')];
  const fLinks = [...document.querySelectorAll('footer a')];
  const colo = document.querySelector('.colophon');
  out.footer = {
    h: Math.round(foot.getBoundingClientRect().height),
    colRows: rows(cols),
    colCount: cols.length,
    close: closest(fLinks),
    colophonTop: colo ? Math.round(colo.getBoundingClientRect().top
                                   - cols[cols.length-1].getBoundingClientRect().bottom) : null,
  };

  // Anything at all sticking out of the viewport, named.
  const vw = window.innerWidth;
  out.escapes = [];
  for (const el of document.querySelectorAll('.masthead *, footer *')) {
    const r = el.getBoundingClientRect();
    if (!r.width && !r.height) continue;
    // Chrome still lays out an absolutely positioned <ul> inside a CLOSED
    // <details>, so the language menu reported as escaping at forty-one widths
    // while being invisible at every one of them. Measured open, it is 176px
    // and fits everywhere. Ask the browser whether the thing can be seen before
    // asking where it is.
    if (el.checkVisibility && !el.checkVisibility({checkVisibilityCSS: true})) continue;
    // A box inside a clipping ancestor is allowed to be wider than the window:
    // .pull-field is overflow:hidden and the decorative layers inside it are
    // deliberately oversized. Reporting them buried the real output under
    // five thousand lines of SVG paths doing exactly what they should.
    let clipped = false;
    for (let a = el.parentElement; a; a = a.parentElement) {
      const o = getComputedStyle(a).overflowX;
      if (o === 'auto' || o === 'scroll' || o === 'hidden') { clipped = true; break; }
    }
    if (clipped) continue;
    if (r.right > vw + 1 || r.left < -1)
      // className on an SVG element is an SVGAnimatedString, not a string.
      out.escapes.push({tag: el.tagName.toLowerCase(),
                        cls: (el.getAttribute('class') || '').slice(0,24),
                        left: Math.round(r.left), right: Math.round(r.right),
                        text: (el.textContent||'').trim().slice(0,24)});
  }
  out.pointer = matchMedia('(pointer: coarse)').matches ? 'coarse' : 'fine';
  return out;
})()
"""


def main(argv) -> int:
    langs = argv[1:] or ["en", "it", "es", "fr", "pt-BR", "de", "ru", "id",
                         "zh-Hans", "ja", "ko", "ar", "ur", "hi", "bn"]

    port = sweep.free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=sweep.ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    profile = tempfile.mkdtemp(prefix="edges-")
    dbg = sweep.free_port()
    chrome = subprocess.Popen(
        [sweep.CHROME, "--headless=new", f"--remote-debugging-port={dbg}",
         "--remote-allow-origins=*", f"--user-data-dir={profile}", "--no-first-run",
         "--no-default-browser-check", "--hide-scrollbars",
         "--force-device-scale-factor=1", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    findings = []
    worst = {"mastH": (0, "", 0), "navRows": (0, "", 0), "gap": (999, "", 0, None),
             "footH": (0, "", 0)}
    try:
        tab = sweep.Tab(dbg)
        tab.send("Page.enable"); tab.send("Runtime.enable")
        print(f"  {len(langs)} lingue × {len(WIDTHS)} larghezze = "
              f"{len(langs)*len(WIDTHS)} misure\n")
        for lang in langs:
            path = "index.html" if lang == "en" else f"{lang}/index.html"
            row = []
            for width in WIDTHS:
                tab.send("Emulation.setDeviceMetricsOverride", width=width, height=900,
                         deviceScaleFactor=1, mobile=width < 768,
                         screenWidth=width, screenHeight=900)
                tab.send("Emulation.setTouchEmulationEnabled",
                         enabled=width < 768, maxTouchPoints=5)
                tab.goto(f"http://127.0.0.1:{port}/{path}")
                v = tab.send("Runtime.evaluate", expression=PROBE,
                             returnByValue=True)["result"]["value"]
                m, f = v["masthead"], v["footer"]
                row.append(f"{width}:{m['h']}/{m['navRows']}r")
                if m["h"] > worst["mastH"][0]: worst["mastH"] = (m["h"], lang, width)
                if m["navRows"] > worst["navRows"][0]: worst["navRows"] = (m["navRows"], lang, width)
                if f["h"] > worst["footH"][0]: worst["footH"] = (f["h"], lang, width)
                for where, c in (("nav", m["close"]), ("footer", f["close"])):
                    g = c["gapX"]
                    if g is not None and g < worst["gap"][0]:
                        worst["gap"] = (g, f"{lang} {where}", width, c["pairX"])
                    if g is not None and g < MIN_GAP:
                        findings.append(f"{lang} @{width} {where}: solo {g}px fra "
                                        f"{c['pairX'][0]!r} e {c['pairX'][1]!r} sulla stessa riga")
                for e in v["escapes"]:
                    findings.append(f"{lang} @{width} esce dal viewport: "
                                    f"<{e['tag']} class={e['cls']!r}> right={e['right']} {e['text']!r}")
            print(f"  {lang:<8} " + "  ".join(row))
    finally:
        chrome.terminate(); server.terminate()
        shutil.rmtree(profile, ignore_errors=True)

    print("\n  peggiori valori")
    print(f"    masthead più alto : {worst['mastH'][0]}px  ({worst['mastH'][1]} @{worst['mastH'][2]})")
    print(f"    righe nav max     : {worst['navRows'][0]}  ({worst['navRows'][1]} @{worst['navRows'][2]})")
    print(f"    footer più alto   : {worst['footH'][0]}px  ({worst['footH'][1]} @{worst['footH'][2]})")
    print(f"    distanza minima   : {worst['gap'][0]}px  ({worst['gap'][1]} @{worst['gap'][2]}) {worst['gap'][3]}")

    print()
    if findings:
        seen = []
        for x in findings:
            if x not in seen: seen.append(x)
        for x in seen[:40]:
            print(f"  DA GUARDARE  {x}")
        if len(seen) > 40: print(f"  … e altri {len(seen)-40}")
        print(f"\n  {len(seen)} rilievi")
        return 1
    print(f"  ok    nessuna sovrapposizione, niente sotto {MIN_GAP}px, niente fuori dal viewport")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
