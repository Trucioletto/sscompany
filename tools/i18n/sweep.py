#!/usr/bin/env python3
"""Render every page in every language at four widths and look for damage.

check.sh reads the HTML. This one renders it, which is the only way to catch
the failures that are a property of the LAYOUT rather than of the markup: a
German compound that will not break and pushes the page sideways, an Arabic
heading that overflows a rail, a Sparkle lockup that 404s, a tap target that a
translation shrank below the WCAG floor.

Fifteen languages times five pages times four widths is 300 renders. Doing that
by eye is not a thing anyone does twice, which is why it lives in a file.

    python3 tools/i18n/sweep.py            # everything
    python3 tools/i18n/sweep.py de ja      # just these languages

Requires Chrome. Serves the site on a loopback port and drives it over CDP;
nothing leaves the machine.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time

import requests
import websocket

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Narrowest phone still in the statistics, a modern phone, a tablet, a desktop.
# 320 is where a fifteen-language site breaks if it is going to.
WIDTHS = [320, 390, 768, 1440]

# WCAG 2.5.8 (AA). Not 2.5.5's 44, which is AAA and which this site meets only
# under a coarse pointer — measuring against it here would report the desktop
# rendering as a failure it is not.
TAP_MIN = 24

PROBE = r"""
(() => {
  const out = {overflow: null, wide: [], broken: [], placeholder: [], small: []};
  const doc = document.documentElement;
  const vw = window.innerWidth;

  if (doc.scrollWidth > vw + 1) out.overflow = [doc.scrollWidth, vw];

  // Which element is actually sticking out. An overflowing page is useless to
  // report without the thing causing it.
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    const style = getComputedStyle(el);
    if (style.position === 'fixed') continue;
    // A deliberately scrollable box is allowed to have wide content inside it.
    let clipped = false;
    for (let p = el.parentElement; p; p = p.parentElement) {
      const o = getComputedStyle(p).overflowX;
      if (o === 'auto' || o === 'scroll' || o === 'hidden') { clipped = true; break; }
    }
    if (clipped) continue;
    if (r.right > vw + 1 || r.left < -1) {
      out.wide.push({tag: el.tagName.toLowerCase(), cls: el.className || '',
                     left: Math.round(r.left), right: Math.round(r.right),
                     text: (el.textContent || '').trim().slice(0, 60)});
    }
  }

  for (const img of document.images) {
    if (!img.complete || img.naturalWidth === 0)
      out.broken.push(img.getAttribute('src'));
  }

  // A template that did not get its value renders as the literal token. This
  // is the failure that would actually reach a reader.
  const body = document.body.innerText;
  for (const m of body.matchAll(/\{\{[^}]*\}\}|FILL:/g)) out.placeholder.push(m[0]);

  for (const el of document.querySelectorAll('a[href], button')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;   // hidden
    // 2.5.8's INLINE exception: "the target is in a sentence, or its size is
    // otherwise constrained by the line-height of non-target text." A link
    // inside a paragraph cannot be made 24px tall without opening a hole in the
    // leading, and the criterion says so. Reporting these buried the finding
    // that matters under thirty that do not.
    const inline = getComputedStyle(el).display === 'inline';
    const parent = el.parentElement;
    const surrounded = parent &&
      (parent.textContent || '').trim().length > (el.textContent || '').trim().length;
    if (inline && surrounded) continue;
    if (r.width < __TAP__ || r.height < __TAP__)
      out.small.push({text: (el.textContent || '').trim().slice(0, 40),
                      w: Math.round(r.width), h: Math.round(r.height)});
  }

  // Report what we are actually testing. The site's 44px targets are behind
  // @media (pointer: coarse); if emulation never turns that on, a pass at 320
  // is a pass for a rendering no phone will ever get.
  out.pointer = matchMedia('(pointer: coarse)').matches ? 'coarse' : 'fine';
  return out;
})()
"""


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Tab:
    def __init__(self, port: int):
        for _ in range(100):
            try:
                tabs = requests.get(f"http://127.0.0.1:{port}/json", timeout=1).json()
                url = [t for t in tabs if t["type"] == "page"][0]["webSocketDebuggerUrl"]
                break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError("Chrome never answered on the debugging port")
        self.ws = websocket.create_connection(url, timeout=30)
        self.n = 0

    def send(self, method, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def goto(self, url):
        self.send("Page.navigate", url=url)
        # Poll for readiness rather than sleeping a fixed amount: fonts are
        # font-display: optional, so layout settles fast, but navigation itself
        # is async and a fixed sleep is either slow or flaky.
        for _ in range(200):
            r = self.send("Runtime.evaluate",
                          expression="document.readyState === 'complete' && "
                                     "document.fonts.status === 'loaded' && location.href",
                          returnByValue=True)
            v = r.get("result", {}).get("value")
            if v and url.split("#")[0] in str(v):
                return
            time.sleep(0.05)


def main(argv) -> int:
    only = set(argv[1:])
    pages = sorted(
        p for p in ROOT.rglob("*.html")
        if ".git" not in p.parts and "tools" not in p.parts
    )
    if only:
        def lang_of(p):
            rel = p.relative_to(ROOT).parts
            return rel[0] if len(rel) > 1 and re.fullmatch(r"[a-z]{2}(-[A-Za-z]+)?", rel[0]) else "en"
        pages = [p for p in pages if lang_of(p) in only]

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    profile = tempfile.mkdtemp(prefix="sweep-")
    dbg = free_port()
    chrome = subprocess.Popen(
        [CHROME, "--headless=new", f"--remote-debugging-port={dbg}",
         # Chrome refuses a debugging websocket whose Origin it did not
         # whitelist, and the python client sends one. The port is bound to
         # loopback and the profile is a throwaway temp dir, so the origin check
         # is protecting nothing here.
         "--remote-allow-origins=*",
         f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
         "--hide-scrollbars", "--force-device-scale-factor=1", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    problems = []
    pointers = {}
    n = 0
    try:
        tab = Tab(dbg)
        tab.send("Page.enable")
        tab.send("Runtime.enable")
        probe = PROBE.replace("__TAP__", str(TAP_MIN))

        for p in pages:
            rel = str(p.relative_to(ROOT))
            url = f"http://127.0.0.1:{port}/" + rel
            for w in WIDTHS:
                # width alone is not enough: without screenWidth/screenHeight a
                # mobile override reports widths that are wrong by the device
                # scale factor, which is how a clean page looks broken.
                tab.send("Emulation.setDeviceMetricsOverride",
                         width=w, height=900, deviceScaleFactor=1,
                         mobile=w < 768, screenWidth=w, screenHeight=900)
                # Metrics alone do not change the pointer media query, so a
                # narrow viewport would still be evaluated as a mouse. Touch
                # emulation is what makes (pointer: coarse) match, which is what
                # the site's larger tap targets are keyed off.
                tab.send("Emulation.setTouchEmulationEnabled",
                         enabled=w < 768, maxTouchPoints=5)
                tab.goto(url)
                r = tab.send("Runtime.evaluate", expression=probe,
                             returnByValue=True, awaitPromise=True)
                v = r["result"]["value"]
                n += 1
                pointers.setdefault(w, set()).add(v["pointer"])
                where = f"{rel} @{w}"
                if v["overflow"]:
                    sw, vw = v["overflow"]
                    worst = sorted(v["wide"], key=lambda x: -x["right"])[:2]
                    problems.append(f"overflow {sw}px in {vw}px   {where}\n" +
                                    "".join(f"        <{x['tag']} class={x['cls']!r}> "
                                            f"right={x['right']} {x['text']!r}\n" for x in worst))
                for b in set(v["broken"]):
                    problems.append(f"image does not load: {b}   {where}")
                for ph in set(v["placeholder"]):
                    problems.append(f"unfilled placeholder {ph!r}   {where}")
                for s in v["small"]:
                    problems.append(f"tap target {s['w']}x{s['h']} (<{TAP_MIN}) "
                                    f"{s['text']!r}   {where}")
            sys.stdout.write(".")
            sys.stdout.flush()
        print()
    finally:
        chrome.terminate()
        server.terminate()
        shutil.rmtree(profile, ignore_errors=True)

    shown = ", ".join(f"{w}px {'/'.join(sorted(pointers.get(w, {'?'})))}"
                      for w in WIDTHS)
    print(f"\n  {n} renders across {len(pages)} pages at {shown}")
    if problems:
        seen = []
        for x in problems:
            if x not in seen:
                seen.append(x)
        for x in seen:
            print(f"  FAIL  {x}")
        print(f"\n  {len(seen)} distinct problem(s)")
        return 1
    print("  ok    no overflow, no broken image, no placeholder, no small tap target")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
