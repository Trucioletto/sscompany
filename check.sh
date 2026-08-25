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
    body = re.sub(r'<details class="lang">.*?</details>', ' ', body, flags=re.S)
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
if [ "$fail" = "0" ]; then
  say 'All checks passed.'
else
  say 'Some checks FAILED — see above.'
fi
exit $fail
