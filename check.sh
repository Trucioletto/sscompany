#!/bin/sh
# check.sh — the parts of this site that break silently.
#
# Not a build step. Nothing here generates anything; what is in git is still
# exactly what ships. This only reads the files and complains, because every
# defect it looks for is one that a browser renders happily and a crawler
# punishes weeks later.
#
# Run it before every push:  ./check.sh
# Exit code is non-zero if anything failed, so it also works as a CI job or a
# pre-push hook.

fail=0
say() { printf '%s\n' "$1"; }
bad() { printf '  FAIL  %s\n' "$1"; fail=1; }
ok()  { printf '  ok    %s\n' "$1"; }

# tools/ is excluded: it holds the page TEMPLATES, whose canonical tag is the
# literal string {{canonical}} and whose body is full of {{placeholders}}. They
# are inputs to the build, never served, and every check below would fail on
# them for reasons that mean nothing.
pages=$(find . -name '*.html' -not -path './.git/*' -not -path './tools/*' | sort)

say ''
say 'Unfilled placeholders'
# The one that would publish a placeholder company registration number.
if grep -rln 'FILL:' $pages >/dev/null 2>&1; then
  for f in $(grep -rln 'FILL:' $pages); do
    if grep -q 'name="robots" content="noindex' "$f"; then
      ok "$f has FILL: but is noindex — gated, not published"
    else
      bad "$f contains FILL: and is INDEXABLE"
    fi
  done
else
  ok 'no FILL: markers anywhere'
fi

say ''
say 'Canonical and og:url agree, and there is exactly one canonical'
for f in $pages; do
  case "$f" in ./404.html) continue ;; esac
  n=$(grep -c 'rel="canonical"' "$f")
  can=$(grep -o 'rel="canonical" href="[^"]*"' "$f" | cut -d'"' -f4)
  og=$(grep -o 'property="og:url" content="[^"]*"' "$f" | cut -d'"' -f4)
  [ "$n" = "1" ] || bad "$f has $n canonical tags"
  [ "$can" = "$og" ] || bad "$f canonical=$can but og:url=$og"
done
[ "$fail" = "0" ] && ok 'all pages agree'

say ''
say 'Trailing slashes — a canonical pointing at a redirect is ignored'
grep -h 'rel="canonical"' $pages | grep -o 'href="[^"]*"' | cut -d'"' -f2 |
  grep -v '/$' | grep -v '\.html$' |
  while read -r u; do bad "canonical without trailing slash: $u"; done

say ''
say 'CSP is byte-identical on every page'
variants=$(grep -h -A1 'Content-Security-Policy' $pages | grep 'content=' | sort -u | wc -l | tr -d ' ')
if [ "$variants" = "1" ]; then ok 'one CSP, everywhere'; else bad "$variants different CSP strings"; fi

say ''
say 'Organization JSON-LD is one node, not several under one @id'
orgs=$(python3 - <<'PY'
import glob, json, re
shapes = set()
for f in glob.glob('**/*.html', recursive=True):
    # Templates are not documents: the JSON-LD there is a {{jsonld}} token that
    # build.py fills per page. Parsing the template as JSON tests the wrong file.
    if '.git' in f or f.startswith('tools/'): continue
    s = open(f, encoding='utf-8').read()
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        for node in json.loads(m.group(1)).get('@graph', []):
            if node.get('@id', '').endswith('#organization'):
                shapes.add(json.dumps(node, sort_keys=True))
print(len(shapes))
PY
)
if [ "$orgs" -le 1 ]; then ok 'single Organization definition'; else bad "$orgs different Organization shapes share one @id"; fi

say ''
say 'JSON-LD parses'
python3 - <<'PY' || exit 1
import glob, json, re, sys
bad = 0
for f in glob.glob('**/*.html', recursive=True):
    # Templates are not documents: the JSON-LD there is a {{jsonld}} token that
    # build.py fills per page. Parsing the template as JSON tests the wrong file.
    if '.git' in f or f.startswith('tools/'): continue
    s = open(f, encoding='utf-8').read()
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        try:
            json.loads(m.group(1))
        except Exception as e:
            print(f'  FAIL  {f}: {e}'); bad = 1
print('  ok    all JSON-LD blocks parse' if not bad else '')
sys.exit(bad)
PY
[ $? -eq 0 ] || fail=1

say ''
say 'Every character has a glyph, or a system font meant to supply it'
# The check that would have caught the arrow, the minus sign and the
# less-than-or-equal that shipped in the first draft. A codepoint outside the
# declared unicode-range makes the browser swap fonts for that one character.
#
# Fifteen languages changed what this can honestly assert. Six scripts — Han,
# Kana, Hangul, Arabic, Devanagari, Bengali — are DELIBERATELY rendered in the
# reader's own system fonts, because neither Inter nor Fraunces contains a
# single glyph for them and subsetting cannot add what the source lacks. So the
# rule is now conditional on the page's own script class:
#
#   latin / cyrl pages : every character must be in a declared range.
#   all other pages    : every LATIN, GREEK, CYRILLIC, general-punctuation or
#                        currency character must be in a declared range, while
#                        characters of the page's own script are expected to
#                        fall through to the system stack.
#
# The weaker rule is still the strong one where it matters. What actually breaks
# is a stray curly quote, an en-dash or an embedded Latin technical term with no
# glyph — and those appear on every page in every language.
python3 - <<'PY' || exit 1
import glob, html, re, sys

css = open('style.css', encoding='utf-8').read()
decls = re.findall(r'unicode-range:([^;]+);', css, re.S)
allowed = set()
for part in ','.join(decls).split(','):
    part = part.strip()
    if not part.startswith('U+'):
        continue
    body = part[2:]
    if '-' in body:
        a, b = body.split('-')
        allowed.update(range(int(a, 16), int(b, 16) + 1))
    else:
        allowed.add(int(body, 16))

# The blocks the two shipped families are responsible for. A character in here
# without a glyph is a defect on any page in any language.
def ours(o):
    return ((0x0020 <= o <= 0x024F)     # Latin and its extensions
            or (0x0370 <= o <= 0x052F)  # Greek and Cyrillic
            or (0x2000 <= o <= 0x206F)  # general punctuation
            or (0x20A0 <= o <= 0x20BF))  # currency symbols

bad = 0
pages = 0
for f in sorted(glob.glob('**/*.html', recursive=True)):
    if '.git' in f or f.startswith('tools/'):
        continue
    s = open(f, encoding='utf-8').read()
    if '<body' not in s:
        continue
    m = re.search(r'<body class="script-([a-z]+)', s)
    script = m.group(1) if m else 'latin'
    strict = script in ('latin', 'cyrl')
    body = s.split('<body', 1)[1].split('>', 1)[1].split('</body>', 1)[0]
    body = re.sub(r'<svg.*?</svg>', '', body, flags=re.S)
    # The language switcher is the one element that MUST contain scripts this
    # page's own font does not have: every language is labelled in its own
    # writing system, because a reader who cannot read the current page cannot
    # read the word "German" either. Six of those labels are Han, Kana, Hangul,
    # Arabic, Devanagari and Bengali, and they are rendered by the system font
    # on purpose. Checking them would fail every page in every language for the
    # one thing that is deliberately correct.
    # Match the open tag by its class, not by its exact text. Adding a second
    # attribute to that element — translate="no", so a machine translator cannot
    # rewrite the language names into the reader's current language — silently
    # stopped this pattern matching, and every Korean and Chinese endonym in the
    # switcher was suddenly reported as a missing glyph on the English page.
    body = re.sub(r'<details[^>]*class="lang"[^>]*>.*?</details>', ' ', body, flags=re.S)
    body = re.sub(r'<[^>]+>', ' ', body)
    pages += 1
    for ch in sorted(set(html.unescape(body))):
        o = ord(ch)
        if o <= 0x1F or o in allowed:
            continue
        if strict or ours(o):
            print(f'  FAIL  {f} [{script}]: {ch!r} U+{o:04X} has no glyph in the subset')
            bad = 1
if not bad:
    print(f'  ok    {pages} pages, no character missing a glyph the site ships')
sys.exit(bad)
PY
[ $? -eq 0 ] || fail=1

say ''
say 'Bidirectional control characters'
# Invisible, and they survive copy-paste into a terminal. The Arabic and Urdu
# pages set dir="rtl" on <html>, which is all they need; a stray U+202E in a
# translation would reverse text in ways nobody can see in a diff.
python3 - <<'PY' || exit 1
import glob, sys
bad = 0
for f in sorted(glob.glob('**/*.html', recursive=True)):
    if '.git' in f or f.startswith('tools/'):
        continue
    for i, ch in enumerate(open(f, encoding='utf-8').read()):
        o = ord(ch)
        if 0x200B <= o <= 0x200F or 0x202A <= o <= 0x202E or o == 0x2060 or o == 0xFEFF:
            print(f'  FAIL  {f}: U+{o:04X} at offset {i}')
            bad = 1
            break
print('  ok    no bidi overrides or zero-width characters' if not bad else '')
sys.exit(bad)
PY
[ $? -eq 0 ] || fail=1

say ''
say 'Sitemap matches what is actually publishable'
# Note: BSD sed (macOS) has no \? in basic regex, so strip the two tags separately.
for u in $(grep -o '<loc>[^<]*</loc>' sitemap.xml | sed 's|<loc>||; s|</loc>||'); do
  p=$(printf '%s' "$u" | sed 's|https://spinnesoftware.com||')
  case "$p" in
    /) f='./index.html' ;;
    */) f=".${p}index.html" ;;
    *) f=".${p}" ;;
  esac
  [ -f "$f" ] || bad "sitemap lists $u but $f does not exist"
  grep -q 'content="noindex' "$f" 2>/dev/null && bad "sitemap lists $u but the page is noindex"
done
for f in $pages; do
  case "$f" in ./404.html) continue ;; esac
  grep -q 'content="noindex' "$f" && continue
  u=$(printf '%s' "$f" | sed 's|^\.||; s|index\.html$||')
  grep -q "<loc>https://spinnesoftware.com${u}</loc>" sitemap.xml ||
    bad "indexable page $f is missing from sitemap.xml"
done

say ''
say 'security.txt is present and has not expired'
# RFC 9116: a parser MUST ignore this file once Expires has passed. A stale date
# does not weaken the file, it removes it — while the file stays on disk looking
# fine. Sixty days of warning is enough to move the date without hurrying.
sec='.well-known/security.txt'
if [ ! -f "$sec" ]; then
  bad "$sec is missing"
else
  exp=$(grep -i '^Expires:' "$sec" | head -1 | sed 's/^[Ee]xpires:[[:space:]]*//')
  if [ -z "$exp" ]; then
    bad "$sec has no Expires field — RFC 9116 requires one"
  else
    grep -qi '^Contact:' "$sec" || bad "$sec has no Contact field — RFC 9116 requires one"
    # Compare as YYYYMMDD integers: no date(1) portability problem between
    # BSD and GNU, and no dependency on how the timestamp is punctuated.
    expday=$(printf '%s' "$exp" | tr -d -c '0-9' | cut -c1-8)
    today=$(date -u +%Y%m%d)
    soon=$(python3 -c "import datetime;print((datetime.date.today()+datetime.timedelta(days=60)).strftime('%Y%m%d'))")
    if [ "$expday" -le "$today" ]; then
      bad "$sec expired on $exp — every parser is now ignoring it"
    elif [ "$expday" -le "$soon" ]; then
      bad "$sec expires on $exp, within 60 days — move the date"
    else
      ok "expires $exp"
    fi
  fi
fi

say ''
say "lang.js knows which pages exist in one language only"
# lang.js redirects a reader to their own language. For a page published in
# English only there is nothing to redirect to, so it must skip those paths —
# and it can only skip the ones it has been told about. Drift here is silent
# and expensive: the reader gets a 404 instead of the page they asked for, and
# only in the fourteen languages nobody tests in.
langjs_list=$(sed -n 's/.*var ENGLISH_ONLY = \[\(.*\)\];.*/\1/p' lang.js | tr -d "' " | tr ',' '\n' | sort -u)
build_list=$(python3 - <<'PYEOF'
import sys
sys.path.insert(0, "tools/i18n")
from build import PAGES, langs_for, DEFAULT
segs = set()
for _key, path, _tmpl, locales in PAGES:
    codes = langs_for(locales)
    if codes == [DEFAULT] and path:
        segs.add(path.split("/")[0])
print("\n".join(sorted(segs)))
PYEOF
)
if [ "$langjs_list" = "$build_list" ]; then
  ok "lang.js skips: ${langjs_list:-(none)}"
else
  bad "lang.js ENGLISH_ONLY is [$(echo $langjs_list)] but build.py publishes [$(echo $build_list)] in English only"
fi

say "nothing is parked past a physical edge"
# `left: -9999px` is the classic way to hide a focusable element, and it is a bug
# in half the languages here. A browser does not make overflow past the inline
# START edge scrollable — but with dir="rtl" the physical left IS the end, so the
# page becomes 9999px wide. The Arabic and Urdu pages shipped like that: 10613px
# of scrollWidth against a 614px viewport, swipeable sideways into nothing, for a
# link nobody could see. Hide focusable things with the 1px-and-clip-path device
# instead, and position them with inset-inline-* so they land on the reading side.
# Comments are stripped first: the note above the skip link explains why NOT to do
# this and says `left: -9999px` in prose, which a naive grep reads as the defect.
if python3 - <<'PYEOF'
import re, sys
css = re.sub(r'/\*.*?\*/', '', open('style.css').read(), flags=re.S)
sys.exit(0 if re.search(r'(left|right)\s*:\s*-\d{4,}px', css) else 1)
PYEOF
then
  bad "style.css parks something at a large negative physical offset — in RTL that is scrollable overflow, not a hiding place"
else
  ok "no large negative left/right in style.css"
fi

say "asset URLs carry the hash of the asset they point at"
# The pages ask for /style.css?v=<hash>. If somebody edits an asset and does not
# rebuild, the pages keep asking for the old hash — and because that URL is
# already in every cache, the change reaches nobody. This is not hypothetical:
# before the hashes existed, a stylesheet change shipped against four-hour cached
# CSS and put a blue band across the top of every page until the cache expired.
asset_drift=0
for f in style.css lang.js overscroll.js; do
  want=$(shasum -a 256 "$f" | cut -c1-8)
  got=$(grep -ho "$f?v=[a-f0-9]*" index.html | head -1 | cut -d= -f2)
  if [ -z "$got" ]; then
    bad "$f is not referenced with a version hash"
    asset_drift=1
  elif [ "$want" != "$got" ]; then
    bad "$f has hash $want but the pages ask for $got — rebuild"
    asset_drift=1
  fi
  n=$(grep -rho "$f?v=[a-f0-9]*" --include='*.html' . 2>/dev/null | sort -u | wc -l | tr -d ' ')
  if [ "$n" != "1" ]; then
    bad "$f is referenced with $n different hashes across the pages"
    asset_drift=1
  fi
done
[ "$asset_drift" = "0" ] && ok "style.css, lang.js and overscroll.js match the pages that ask for them"

say ''
if [ "$fail" = "0" ]; then
  say 'All checks passed.'
else
  say 'Some checks FAILED — see above.'
fi
exit $fail
