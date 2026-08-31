#!/usr/bin/env python3
"""Render every page of the site, in every language, from one set of strings.

WHY THIS EXISTS, AND WHY IT DOES NOT BREAK THE RULE AT THE TOP OF check.sh.

check.sh says "Not a build step. Nothing here generates anything; what is in git
is still exactly what ships." That remains true: this script writes .html files
INTO the repository, they are committed, and the browser is served those exact
bytes. Nothing is assembled at request time and there is no runtime dependency.
What changes is where a sentence is EDITED — in content/<lang>.json rather than
in fifteen copies of the same markup.

Without it, six pages in fifteen languages is ninety hand-maintained files, and
a one-word fix to the footer is ninety edits with fourteen chances to miss one.
That is not a theoretical risk: the footer block was already identical across
six files and had to be changed by script twice in this repo's short history.

    python3 tools/i18n/build.py           # write every page
    python3 tools/i18n/build.py --check    # write nothing; fail if any page on
                                           # disk differs from what would be
                                           # written (use this in CI)

Run check.sh afterwards. It validates the OUTPUT, which is the thing that ships.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
CONTENT = HERE / "content"
TEMPLATES = HERE / "templates"

SITE = "https://spinnesoftware.com"

# ---------------------------------------------------------------------------
# The languages.
#
# The brief was "the 15 most used in the world". That list, by total speakers,
# ends with Nigerian Pidgin and Marathi and does not contain Italian. Two
# deliberate departures from it, both stated rather than hidden:
#
#   - Italian is in. A company registered in Rome whose counterparties look it
#     up in the Registro Imprese cannot be readable in fourteen languages and
#     not in the one its own tax authority writes to it in.
#   - Korean replaces Nigerian Pidgin, which has no standard written orthography
#     and no plausible reader for this site.
#
# Everything else is the top of the list as it stands.
#
#   code   — the URL segment and the `lang` attribute
#   name   — how the language names ITSELF, which is the only correct label in a
#            language switcher: a reader who cannot read the current page cannot
#            read "German" either, but can always read "Deutsch"
#   dir    — ltr or rtl
#   script — which font stack the page gets (see style.css)
# ---------------------------------------------------------------------------
LANGS = [
    {"code": "en",      "name": "English",    "dir": "ltr", "script": "latin",  "locale": "en_US"},
    {"code": "zh-Hans", "name": "简体中文",      "dir": "ltr", "script": "hans",   "locale": "zh_CN"},
    {"code": "hi",      "name": "हिन्दी",        "dir": "ltr", "script": "deva",   "locale": "hi_IN"},
    {"code": "es",      "name": "Español",    "dir": "ltr", "script": "latin",  "locale": "es_ES"},
    {"code": "fr",      "name": "Français",   "dir": "ltr", "script": "latin",  "locale": "fr_FR"},
    {"code": "ar",      "name": "العربية",      "dir": "rtl", "script": "arab",   "locale": "ar_AR"},
    {"code": "bn",      "name": "বাংলা",        "dir": "ltr", "script": "beng",   "locale": "bn_BD"},
    {"code": "pt-BR",   "name": "Português",  "dir": "ltr", "script": "latin",  "locale": "pt_BR"},
    {"code": "ru",      "name": "Русский",    "dir": "ltr", "script": "cyrl",   "locale": "ru_RU"},
    {"code": "ur",      "name": "اردو",        "dir": "rtl", "script": "arab",   "locale": "ur_PK"},
    {"code": "id",      "name": "Bahasa Indonesia",  "dir": "ltr", "script": "latin",  "locale": "id_ID"},
    {"code": "de",      "name": "Deutsch",    "dir": "ltr", "script": "latin",  "locale": "de_DE"},
    {"code": "ja",      "name": "日本語",       "dir": "ltr", "script": "jpan",   "locale": "ja_JP"},
    {"code": "ko",      "name": "한국어",       "dir": "ltr", "script": "kore",   "locale": "ko_KR"},
    {"code": "it",      "name": "Italiano",   "dir": "ltr", "script": "latin",  "locale": "it_IT"},
]
BY_CODE = {l["code"]: l for l in LANGS}
DEFAULT = "en"

# page key -> (path under a language root, template file, locales)
# English lives at the root; every other language under /<code>/.
#
# `locales` is None when the page exists in every language, which is true of
# everything the site launched with. A tuple names the only languages it is
# built in.
#
# It exists for the pages that answer a question rather than describe the
# company: one is worth publishing in English long before there is time to
# translate it fifteen times. Nothing here needs it yet — the first such page
# is unwritten, and an /answers/ hub with no answers on it is an empty room
# with a sign on the door — but the column is what that page was waiting on.
#
# Its first real use is 404.html, and that is not a placeholder. The page offers
# fifteen languages and fourteen of those links lead to another 404, because
# /it/404.html was never written. Declaring the truth in this column is what
# removes the control, rather than another special case in the template.
#
# So a page built in one language declares no hreflang alternates, renders no
# language switcher, and lists no siblings in the sitemap. Not as a special
# case bolted on, but because all three are generated from this column, and a
# set of one has nothing to declare.
PAGES = [
    ("home",         "",              "home.html",         None),
    ("sparkle",      "sparkle/",      "sparkle.html",      None),
    ("how_we_build", "how-we-build/", "how-we-build.html", None),
    ("about",        "about/",        "about.html",        None),
    ("privacy",      "privacy/",      "privacy.html",      None),
    # The first page whose subject is a question rather than the company. English
    # only: it is worth publishing now, and it is worth translating only once it
    # has earned the attention that would justify fourteen more copies.
    ("answers_transcribe", "answers/transcribe-video-without-uploading/",
                                      "answer.html",       ("en",)),
]
# 404 is special: not indexed, not in the sitemap, English only (GitHub Pages
# serves one 404 document for the whole domain and cannot pick a language).
# Declaring that here rather than in prose is what finally removes the dead
# language switcher: the same column that governs every other page governs it.
ERROR_PAGE = ("notfound", "404.html", "404.html", ("en",))


def langs_for(locales) -> list[str]:
    """The codes a page is built in, in LANGS order. None means all of them."""
    if locales is None:
        return [l["code"] for l in LANGS]
    return [l["code"] for l in LANGS if l["code"] in locales]


def url_for(lang: str, path: str) -> str:
    """Canonical absolute URL. English at the root, others under /<code>/."""
    prefix = "" if lang == DEFAULT else f"{lang}/"
    return f"{SITE}/{prefix}{path}"


def out_path(lang: str, path: str) -> pathlib.Path:
    prefix = "" if lang == DEFAULT else f"{lang}/"
    rel = f"{prefix}{path}"
    if rel.endswith("/") or rel == "":
        rel += "index.html"
    return ROOT / rel


def load(lang: str) -> dict:
    with open(CONTENT / f"{lang}.json", encoding="utf-8") as fh:
        return json.load(fh)


def read_template(name: str) -> str:
    with open(TEMPLATES / name, encoding="utf-8") as fh:
        return fh.read()


_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")

# A placeholder that is alone on its line — {{switcher}}, {{hreflang}},
# {{preload}} — and resolves to nothing takes its line with it. Substituting in
# place would leave a blank line in the served HTML, which is how you can tell
# from the outside that something was meant to be there and wasn't.
_LINE_PLACEHOLDER = re.compile(r"^[ \t]*\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}[ \t]*\n", re.M)


def resolve(dotted: str, data: dict):
    """`a.b.0.c` walks dicts by key and lists by index, so a template can say
    {{page.what.2}} for the third bullet without the content file needing four
    near-identical keys."""
    node = data
    for part in dotted.split("."):
        if isinstance(node, list):
            if not part.isdigit() or int(part) >= len(node):
                raise KeyError(dotted)
            node = node[int(part)]
        elif isinstance(node, dict) and part in node:
            node = node[part]
        else:
            raise KeyError(dotted)
    return node


def render(template: str, data: dict, where: str) -> str:
    missing = []

    def sub(m):
        try:
            value = resolve(m.group(1), data)
        except KeyError:
            missing.append(m.group(1))
            return m.group(0)
        if isinstance(value, list):
            return "".join(value)
        return str(value)

    def drop_if_empty(m):
        """Only collapses a line that resolves to the empty string. A missing
        key is left alone so the report below still names it."""
        try:
            value = resolve(m.group(1), data)
        except KeyError:
            return m.group(0)
        if isinstance(value, list):
            value = "".join(value)
        return "" if str(value) == "" else m.group(0)

    out = _LINE_PLACEHOLDER.sub(drop_if_empty, template)
    out = _PLACEHOLDER.sub(sub, out)
    if missing:
        raise SystemExit(f"  MISSING in {where}: {', '.join(sorted(set(missing)))}")
    return out


def hreflang_block(page_path: str, codes: list[str]) -> str:
    """Every language the page exists in points at every other, and at itself.
    Google drops a whole hreflang cluster if the links are not reciprocal, so
    this is generated from one list rather than written per page.

    A page that exists in one language emits nothing. hreflang describes a set
    of alternates and a set of one has no alternates to describe; emitting the
    full list instead would advertise fourteen URLs nobody wrote."""
    if len(codes) < 2:
        return ""
    lines = []
    for code in codes:
        lines.append(
            f'  <link rel="alternate" hreflang="{code}" href="{url_for(code, page_path)}">'
        )
    fallback = DEFAULT if DEFAULT in codes else codes[0]
    lines.append(
        f'  <link rel="alternate" hreflang="x-default" href="{url_for(fallback, page_path)}">'
    )
    return "\n".join(lines)


def switcher(current: str, page_path: str, codes: list[str]) -> str:
    """A <details> element, because the site runs no JavaScript and this is the
    only disclosure widget HTML gives you without any. Every entry links to the
    SAME page in another language, not to that language's home page — landing on
    a homepage after asking to read the page you were already on is the standard
    way this control is got wrong."""
    # One language, no control. A switcher is a way out of the language you are
    # stuck in; one that lists fourteen pages that do not exist is a way into
    # fourteen 404s, which is precisely what 404.html has been doing.
    if len(codes) < 2:
        return ""
    cur = BY_CODE[current]
    items = []
    for l in (BY_CODE[c] for c in codes):
        aria = ' aria-current="true"' if l["code"] == current else ""
        items.append(
            f'        <li><a href="{url_for(l["code"], page_path)}" hreflang="{l["code"]}"'
            f' lang="{l["code"]}"{aria}>{l["name"]}</a></li>'
        )
    # translate="no" on the whole control. A language switcher lists each
    # language in ITS OWN language, which is the only thing that makes it
    # usable: somebody looking for 日本語 is looking for those three characters.
    # A machine translator run over the page turns the list into the reader's
    # current language — "English" arrives as "INGLESE" — and the control stops
    # being a way out of the language you are stuck in.
    return (
        '      <details class="lang" translate="no">\n'
        f'        <summary aria-label="Language — {cur["name"]}">'
        f'<span lang="{cur["code"]}">{cur["name"]}</span></summary>\n'
        '        <ul>\n' + "\n".join(items) + "\n        </ul>\n"
        "      </details>"
    )


# Preloading a font a page will never use is pure waste, and on the six pages
# rendered with system fonts it is 100 KB of it. The Cyrillic file is never
# preloaded: only Russian needs it, and it loads on demand from unicode-range.
PRELOAD = {
    "latin": ["/fonts/inter-latin.woff2", "/fonts/fraunces-latin.woff2"],
    "cyrl":  ["/fonts/inter-cyrillic.woff2"],
}


def preload_for(script: str) -> str:
    files = PRELOAD.get(script, [])
    return "\n".join(
        f'  <link rel="preload" href="{f}" as="font" type="font/woff2" crossorigin>'
        for f in files
    )


def jsonld(lang: str, page_key: str, page_path: str, data: dict) -> str:
    """Structured data, built per page rather than pasted into the shell.

    The block used to be a literal in _shell.html, which meant all 75 pages
    shipped the same two nodes — including "inLanguage": "en" on the Chinese
    page, and a knowsLanguage of two languages on a site that speaks fifteen.
    Neither is a typo a reader would catch; both are things a machine reads
    first and believes.

    What is added here is only what the pages already say. No ratings, no price,
    no operating system: an Organization that overstates itself in JSON-LD is
    lying in the one place nobody proofreads."""
    page = data["pages"][page_key]
    canonical = url_for(lang, page_path)
    ORG, SITE_ID = f"{SITE}/#organization", f"{SITE}/#website"
    graph = [
        {"@type": "Organization", "@id": ORG, "name": "Spinne Software",
         "legalName": "Spinne Software di Luci Manuel", "url": f"{SITE}/",
         "logo": f"{SITE}/logo.svg",
         # One @id is one entity, so it gets ONE description. Localising this
         # made fifteen pages describe the same organisation differently under
         # the same identifier — a consumer merging the graph gets a conflict.
         # Language belongs on WebPage and WebSite, which carry inLanguage.
         "description": "Italian software company building its own products. "
                        "Sparkle, an AI video editor, is the first.",
         "vatID": "IT18636231005", "identifier": "REA RM-1797481",
         "email": "hello@spinnesoftware.com",
         "founder": {"@type": "Person", "name": "Manuel Luci"},
         "knowsLanguage": [l["code"] for l in LANGS],
         "areaServed": {"@type": "Country", "name": "Italy"},
         "sameAs": ["https://www.linkedin.com/company/spinne-software/"]},
        {"@type": "WebSite", "@id": SITE_ID, "name": "Spinne Software",
         "url": f"{SITE}/", "inLanguage": lang,
         "publisher": {"@id": ORG}},
        {"@type": "WebPage", "@id": f"{canonical}#webpage", "url": canonical,
         "name": page["og_title"], "description": page["description"],
         "inLanguage": lang, "isPartOf": {"@id": SITE_ID}, "about": {"@id": ORG}},
    ]
    if page_key != "home":
        prefix = "" if lang == DEFAULT else f"/{lang}"
        graph.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": data["nav"]["home"],
             "item": f"{SITE}{prefix}/"},
            {"@type": "ListItem", "position": 2, "name": page["og_title"],
             "item": canonical}]})
    if page_key.startswith("answers_"):
        # TechArticle, not Article: the distinction is what the page is FOR, and
        # a consumer that filters for technical documentation should find this
        # and not a company announcement. No author node — the page is the
        # company's, and inventing a byline to satisfy a schema validator is
        # exactly the kind of decoration this graph has stayed clear of.
        graph.append({"@type": "TechArticle", "@id": f"{canonical}#article",
                      "headline": page["og_title"], "description": page["description"],
                      "inLanguage": lang, "isPartOf": {"@id": SITE_ID},
                      "mainEntityOfPage": {"@id": f"{canonical}#webpage"},
                      "publisher": {"@id": ORG},
                      "about": {"@id": f"{SITE}/sparkle/#software"},
                      "proficiencyLevel": "Expert"})
    if page_key == "sparkle":
        graph.append({"@type": "SoftwareApplication", "@id": f"{canonical}#software",
                      "name": "Sparkle", "applicationCategory": "MultimediaApplication",
                      "description": page["description"],
                      "url": "https://sparkle.software", "publisher": {"@id": ORG}})
    return json.dumps({"@context": "https://schema.org", "@graph": graph},
                      ensure_ascii=False, indent=2)


def build_page(lang: str, page_key: str, page_path: str, template_name: str,
               data: dict, indexable: bool = True,
               locales=None) -> tuple[pathlib.Path, str]:
    l = BY_CODE[lang]
    page = dict(data["pages"][page_key])

    # Which nav item is the current page is structure, not language. Keeping it
    # out of the content files means a translator can never accidentally
    # translate, drop or mangle a raw ` aria-current="page"` attribute — which is
    # the kind of thing that breaks silently in one language out of fifteen.
    page["nav_sparkle_current"] = ' aria-current="page"' if page_key == "sparkle" else ""
    page["nav_how_current"] = ' aria-current="page"' if page_key == "how_we_build" else ""
    page["nav_about_current"] = ' aria-current="page"' if page_key == "about" else ""

    # The answer page exists in English only, so the link to it is emitted only on the
    # English /sparkle/. Sending fourteen languages to a page none of them can read would
    # be a worse defect than the one it fixes — the page being unreachable from anywhere.
    # Computed here rather than carried as a string in fifteen content files, because
    # fourteen of them would hold a label for a link that is never rendered.
    page["answer_link"] = ""
    if page_key == "sparkle" and lang == DEFAULT:
        ans = data["pages"].get("answers_transcribe", {})
        if ans.get("link_from_sparkle"):
            page["answer_link"] = (
                '<p class="more"><a href="/answers/transcribe-video-without-uploading/">'
                + ans["link_from_sparkle"] + "</a></p>")

    # Navigation URLs are COMPUTED, never taken from the content file. A
    # translator's job is words; a mistyped href in one of fifteen files is a
    # dead link nobody would find, and "/it/sparkle/" is not a translation of
    # "/sparkle/" in any useful sense. The labels beside them are translated.
    prefix = "" if lang == DEFAULT else f"/{lang}"
    nav = dict(data["nav"])
    nav.update({
        "home_href": f"{prefix}/",
        "sparkle_href": f"{prefix}/sparkle/",
        "how_href": f"{prefix}/how-we-build/",
        "about_href": f"{prefix}/about/",
        "privacy_href": f"{prefix}/privacy/",
    })

    codes = langs_for(locales)

    ctx = {
        **data,
        "nav": nav,
        "lang": l["code"],
        "dir": l["dir"],
        "script": l["script"],
        "locale": l["locale"],
        "canonical": url_for(lang, page_path),
        "hreflang": hreflang_block(page_path, codes) if indexable else "",
        "switcher": switcher(lang, page_path, codes),
        "page": page,
        "rtl_class": " is-rtl" if l["dir"] == "rtl" else "",
        "preload": preload_for(l["script"]),
        "jsonld": jsonld(lang, page_key, page_path, data),
    }

    body = render(read_template(template_name), ctx, f"{lang}/{template_name}")
    ctx["body"] = body
    shell = read_template("_shell.html" if indexable else "_shell-noindex.html")
    return out_path(lang, page_path), render(shell, ctx, f"{lang}/shell")


def llms_txt() -> str:
    """The llmstxt.org convention: one plain-text map of the site for a model
    that has been pointed at the domain and has one fetch to spend.

    Generated from the same content files as the pages, for the same reason the
    sitemap is: a hand-written version would describe the site as it was on the
    day somebody last remembered to edit it. Every line below is a string that
    also appears on a page, so it cannot drift into saying something the site
    does not say.

    English only, deliberately. The point is to be read once and understood; a
    fifteen-language index would bury the five pages that matter under seventy
    that repeat them. The translations are declared in hreflang and in the
    sitemap, which is where a crawler looks for them."""
    d = load(DEFAULT)
    f, pages = d["facts"], d["pages"]
    lines = [
        "# Spinne Software",
        "",
        f"> {pages['home']['og_description']}",
        "",
        f"{pages['about']['lede']}",
        "",
        "## Pages",
        "",
    ]
    for key, path, _tmpl, locales in PAGES:
        if DEFAULT not in langs_for(locales):
            continue
        lines.append(f"- [{pages[key]['og_title']}]({url_for(DEFAULT, path)}): "
                     f"{pages[key]['description']}")
    lines += [
        "",
        "## Company",
        "",
        f"- {f['legal_name']}: Spinne Software di Luci Manuel",
        f"- {f['legal_form']}: {f['legal_form_value']}",
        f"- {f['registered']}: {f['registered_value']}",
        f"- {f['vat_number']}: IT 18636231005",
        f"- {f['email']}: hello@spinnesoftware.com",
        f"- {f['pec']}: spinnesoftware@pec.it",
        f"- {f['products']}: Sparkle{f['preview_paren']} — https://sparkle.software",
        "",
        "## Languages",
        "",
        "This site is published in "
        + ", ".join(l["name"] for l in LANGS)
        + f". Every page declares the others in hreflang; {SITE}/sitemap.xml lists all of them.",
        "",
    ]
    return "\n".join(lines)


def sitemap() -> str:
    """Only the languages each page was actually built in. A sitemap alternate
    is the same promise as an hreflang link, so a page published in one language
    lists itself and stops — the alternates block is omitted rather than filled
    with URLs that would 404."""
    rows = []
    for _key, path, _tmpl, locales in PAGES:
        codes = langs_for(locales)
        if len(codes) > 1:
            alts = "\n".join(
                f'      <xhtml:link rel="alternate" hreflang="{c}" href="{url_for(c, path)}"/>'
                for c in codes
            )
            fallback = DEFAULT if DEFAULT in codes else codes[0]
            alts += (f'\n      <xhtml:link rel="alternate" hreflang="x-default"'
                     f' href="{url_for(fallback, path)}"/>')
            alts += "\n"
        else:
            alts = ""
        for code in codes:
            rows.append(
                "  <url>\n"
                f"    <loc>{url_for(code, path)}</loc>\n"
                f"    <lastmod>{LASTMOD}</lastmod>\n"
                f"{alts}"
                "  </url>"
            )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    )


def _lastmod() -> str:
    """The newest mtime among the files a page is actually built from.

    It was a hand-maintained constant, which is a date that is correct once. All
    76 pages genuinely do change together — they come from the same content
    files — so one date for all of them is not a fudge; what was wrong was that
    nothing updated it."""
    import datetime
    newest = max(f.stat().st_mtime for f in
                 list(CONTENT.glob("*.json")) + list(TEMPLATES.glob("*.html")))
    return datetime.date.fromtimestamp(newest).isoformat()


LASTMOD = _lastmod()


def main() -> int:
    check_only = "--check" in sys.argv
    written, differs = 0, []

    for lang in [l["code"] for l in LANGS]:
        data = load(lang)
        for key, path, tmpl, locales in PAGES:
            if lang not in langs_for(locales):
                continue
            dest, html = build_page(lang, key, path, tmpl, data, locales=locales)
            if check_only:
                current = dest.read_text(encoding="utf-8") if dest.exists() else None
                if current != html:
                    differs.append(str(dest.relative_to(ROOT)))
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(html, encoding="utf-8")
                written += 1

    # 404, English only.
    data = load(DEFAULT)
    key, path, tmpl, locales = ERROR_PAGE
    dest, html = build_page(DEFAULT, key, path, tmpl, data, indexable=False,
                            locales=locales)
    if check_only:
        current = dest.read_text(encoding="utf-8") if dest.exists() else None
        if current != html:
            differs.append(str(dest.relative_to(ROOT)))
    else:
        dest.write_text(html, encoding="utf-8")
        written += 1

    for name, text in (("sitemap.xml", sitemap()), ("llms.txt", llms_txt())):
        dest = ROOT / name
        if check_only:
            if not dest.exists() or dest.read_text(encoding="utf-8") != text:
                differs.append(name)
        else:
            dest.write_text(text, encoding="utf-8")

    if check_only:
        if differs:
            print("  STALE — these files do not match the content files:")
            for d in differs:
                print("   ", d)
            return 1
        print(f"  ok    every page matches its source ({len(LANGS)} languages)")
        return 0

    print(f"  wrote {written} pages + sitemap.xml + llms.txt across {len(LANGS)} languages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
