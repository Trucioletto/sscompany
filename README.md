# spinnesoftware.com

Static one-page site. No backend, no build step, no JavaScript. Open `index.html`
in a browser to see it exactly as it ships.

## Files that get published

```
index.html            the page (the logo is an inline SVG; JSON-LD at the bottom of <head>)
privacy.html          privacy notice; update it if the controller or contact changes
404.html              custom not-found page; GitHub Pages serves it for any unknown URL
style.css             all styles, including the @font-face
fonts/inter.woff2     Inter, subset to the glyphs in use, weight axis clipped to 400–600
logo.svg              standalone logo, referenced by the JSON-LD "logo" field
favicon.svg           browser tab icon, used by every modern browser
favicon.ico           16/32/48 raster fallback; also stops the bare /favicon.ico 404
favicon-96.png        96×96 raster, the size Google prefers for search results
apple-touch-icon.png  180×180, used when the site is saved to an iOS home screen
og-image.png          1200×630 preview shown when the link is shared
robots.txt
sitemap.xml           update <lastmod> when the page content changes
CNAME                 must contain exactly: spinnesoftware.com
.nojekyll             tells GitHub Pages to serve the files as-is
```

Everything else in this folder is a working file and is excluded by `.gitignore`:
`og-image.svg` and `touch-icon-src.svg` are the sources the two PNGs were rendered
from, and `avvia-sito.sh` is a local preview helper. They must never be served from
the public domain.

## Regenerating the images

Both PNGs are rendered from the matching `.svg` with headless Chrome:

```sh
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --screenshot=og-image.png \
  --window-size=1200,630 --hide-scrollbars "file://$PWD/og-image.svg"
"$CHROME" --headless=new --disable-gpu --screenshot=apple-touch-icon.png \
  --window-size=180,180 --hide-scrollbars "file://$PWD/touch-icon-src.svg"
```

Both SVG sources are fully self-contained: the tagline in `og-image.svg` is stored as
vector outlines drawn from `fonts/inter.woff2`, not as live text, so the PNGs render
identically on any machine with no fonts installed. If you ever re-typeset that tagline,
outline it again — a live `<text>` element would silently pick up whatever font the
rendering machine happens to have.

The favicons are rasterised from `favicon.svg`; regenerate them with:

```sh
"$CHROME" --headless=new --disable-gpu --screenshot=/tmp/f512.png \
  --window-size=512,512 --hide-scrollbars --default-background-color=00000000 \
  "file://$PWD/favicon.svg"
magick /tmp/f512.png -resize 96x96 favicon-96.png
magick /tmp/f512.png \( -clone 0 -resize 16x16 \) \( -clone 0 -resize 32x32 \) \
  \( -clone 0 -resize 48x48 \) -delete 0 favicon.ico
```

## Publishing to GitHub Pages

1. Create the repo and push. `.gitignore` keeps the working files out.

   ```sh
   git init
   git add .
   git commit -m "Spinne Software landing page"
   git branch -M main
   git remote add origin https://github.com/<user>/<repo>.git
   git push -u origin main
   ```

2. On GitHub: **Settings → Pages → Deploy from a branch**, branch `main`, folder `/ (root)`.

3. At the domain registrar, point the DNS at GitHub:

   | Type  | Name | Value |
   |-------|------|-------|
   | A     | @    | `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153` |
   | AAAA  | @    | `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153` |
   | CNAME | www  | `<user>.github.io` |

   The AAAA records are what make the site reachable over IPv6 — on mobile networks
   that are IPv6-only, an apex domain with A records alone can fail to resolve.

4. **Settings → Pages → Custom domain**: enter `spinnesoftware.com`, wait for the DNS
   check to pass, then tick **Enforce HTTPS**. The certificate can take up to an hour.

5. **Verify the domain** under account (or organisation) *Settings → Pages → Add a domain*.
   This is not cosmetic. Without it, if this repository is ever deleted, made private,
   or has Pages switched off while the DNS records still point at GitHub, anyone can
   create their own repository containing a `CNAME` file with `spinnesoftware.com` and
   GitHub will serve *their* content on your domain. Domain verification binds the
   hostname to your account, so nobody else can claim it. Do this once; it costs nothing.

Do not delete `CNAME`. GitHub rewrites it from the Pages settings, and if it goes
missing the custom domain silently detaches.

If you ever take the site down, **remove the DNS records first**, then delete the
repository — never the other way round. Dangling DNS pointed at a shared host is how
domains get taken over.

With both the apex A/AAAA records and the `www` CNAME in place, GitHub redirects
`www.spinnesoftware.com` to the apex automatically. There is no duplicate-content
problem to solve.

## Getting found

Publishing does not make Google aware of the site. A brand-new domain with no inbound
links is never crawled on its own, and the `Sitemap:` line in `robots.txt` only helps
*after* a crawler already knows the host exists. Two steps, once:

1. **Google Search Console** → add `spinnesoftware.com` as a *Domain* property, verify
   with the DNS TXT record it gives you, then submit `https://spinnesoftware.com/sitemap.xml`.
2. **Bing Webmaster Tools** → same, or just import the Search Console property.

The LinkedIn company page should link back to the domain. That backlink is what
corroborates, for Google, that this site and that company are the same entity — the
`sameAs` field in the page's structured data asserts it, the LinkedIn link confirms it.

When you first share the link on LinkedIn, its crawler caches the preview image for a
long time. If the preview looks wrong, fix `og-image.png`, then force a refresh through
the LinkedIn Post Inspector rather than waiting for the cache to expire.

## Legal

`privacy.html` names **Manuel Luci** as the data controller, with
`manuelluci173@gmail.com` as the contact address. GDPR Art. 13 requires only
those two things: an identity and a way to reach it. Update the page if either
changes — in particular, replace the natural person with the legal entity once a
company is incorporated.

A VAT number, registered office and PEC are *company-law* obligations
(art. 2250 c.c., D.Lgs 70/2003) that bind an incorporated company carrying out
commercial activity online. They do not apply to this purely informational page.

No cookie banner is needed: the site sets no cookies and uses no storage,
analytics or third-party embeds of any kind.

### Why the notice is written the way it is

Every extraterritorial privacy law hangs on the same hook: it reaches you when you
**offer goods or services** to people in that territory, or monitor their behaviour.
This site offers nothing and monitors nobody, so **no jurisdiction requires a consent
banner, a local representative, or registration with an authority.** Checked against
GDPR, UK GDPR/PECR, LGPD (Brazil), CCPA/CPRA and the ~20 US state laws, PIPEDA and
Quebec Law 25, the Australian Privacy Act, the Swiss revFADP, NZ, China PIPL, India
DPDP, Japan APPI, Korea PIPA and Singapore PDPA — July 2026.

The one law that *does* apply is the GDPR, and not because the site targets Europe:
it applies because the **controller is established in Italy** (Art. 3(1)). For the same
reason no EU representative is needed — Art. 27 binds only controllers established
*outside* the Union. The Italian Garante is therefore the competent authority, and
naming another country's regulator would falsely imply it has jurisdiction.

Three sentences in the notice exist for foreign readers rather than for Italian law:
the explicit *sell / share* wording (terms of art under California law), the children's
paragraph, and the "Visitors outside Europe" section — which also records, for the
avoidance of doubt, that the site targets no country in particular. That statement is
what keeps the offering-based hooks above from engaging. **If you ever add a contact
form, a newsletter, prices, or country-targeted content, this analysis has to be redone
before launch.**

The notice deliberately states **no retention period**: neither GitHub nor Fastly
publishes one for server logs, and inventing a window would be a false statement.

## Global reach

The site loads nothing from a third party — no font CDN, no analytics, no embeds — so
it renders identically where Google, Meta or a CDN is blocked, and it works fully
offline once cached. There is no JavaScript, so it survives a blocked script, a
restrictive proxy and a text-only browser. Without CSS the HTML is still readable;
without the web font the system font takes over; without images the logo has alt text.

**Slow networks.** The critical path is 3 same-origin requests and about 30 KB on the
wire: roughly 6 seconds on a poor 2G connection, under a second on 3G.

**Old browsers.** Every modern CSS function used here (`min()`, `max()`, `clamp()`,
`env()`, custom properties, flexbox `gap`, `:focus-visible`) is preceded by a plain
fallback declaration. A browser that cannot parse the modern value discards that one
declaration and keeps the plain one, so the layout degrades instead of collapsing.
Verified against a build with every modern declaration stripped out. **If you edit the
CSS, keep the fallback first and the modern value second** — and never put
`:focus-visible` in the same selector list as `:hover`, because a browser that does not
know the former throws away the whole rule, hover included.

**IPv6.** The `AAAA` records above are what make the apex reachable on mobile networks
that no longer route IPv4. Do not skip them.

**China.** GitHub Pages is unreliable behind the Great Firewall — sometimes slow,
sometimes DNS-poisoned, occasionally unreachable. Nothing in this repository can fix
that; it is where the files are hosted. If Chinese visitors ever matter, put a CDN that
terminates inside China in front of the domain, or mirror the same files on a
China-based host. The site is a handful of static files, so mirroring it is trivial.

## Things worth knowing before you change anything

The font carries only the ~120 characters these pages use, and only weights 400–600.
Two CSS declarations must stay in step with the binary: `unicode-range` and
`font-weight` in the `@font-face`. Declare a character the font lacks and the browser
silently drops Inter for it; declare a weight the axis lacks and it may synthesise one.
If you add a glyph (a new symbol, an accented letter, another language), regenerate the
subset from a full Inter release rather than trusting the file in this repo.

Only `index.html` inlines the wordmark, because it is the first thing painted. The other
two pages reference `logo.svg` so it is fetched once and cached.

- The logo's SVG `viewBox` is cropped tight to the artwork (`79.08 145.78 216.1 90.16`).
  The original export had ~35px of invisible padding above the wordmark, which threw
  every margin off. If you re-export the logo, crop it the same way or re-tune the spacing.
- `--column` (23rem) is both the logo width and the description's measure, so the
  wordmark stays the widest element in the stack. Changing one changes the composition.
- Animations are opacity-only by deliberate choice. No translation, no movement.
- The footer year is hard-coded. With no build step and no JavaScript there is nowhere
  to compute it, so update it by hand each January.
