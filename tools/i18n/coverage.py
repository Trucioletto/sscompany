#!/usr/bin/env python3
"""Is every language actually TRANSLATED, and translated whole?

validate.py proves the shape matches and the identifiers survived. factcheck.py
proves a denial is still a denial. Neither can see the failure this file is for:
a value that was never translated at all, or one that arrived a clause short.
Both render perfectly, and in fourteen languages nobody on the team reads, both
survive review indefinitely.

  1. STILL ENGLISH   — byte-identical to the English WHERE THAT MEANS SOMETHING.
                       Most identical values are correct: "Innovation" and
                       "Ambition" are French and German words, "Rome" is spelled
                       the same in French, Italian keeps "Home", "Privacy" and
                       "Email" because that is what Italian UI says. So identity
                       is only a failure for PROSE (four or more words), where a
                       coincidence is not available.
  2. ENGLISH LEAKED  — a clause left in English inside a translated sentence.
                       Unambiguous English function words only, and only when
                       TWO share one value: one "was" is German, two of
                       "the/which/without" together are not.
  3. SCRIPT MISSING  — prose on a non-Latin page containing none of that page's
                       own script. This is what an untranslated paste looks like
                       once somebody edits a word of it and check 1 goes quiet.
                       Short labels are exempt: "undo" is a loanword in the
                       Hindi, Urdu and Bengali copy on purpose, and the rail
                       label agrees with the prose around it.
  4. LENGTH OUTLIER  — a value far off the ratio THIS language runs at in the
                       rest of the same file. The baseline is the file's own
                       median, never a constant: Japanese runs at 0.50x and
                       German at 1.13x, and a hard-coded factor would call one
                       of them broken forever.
  5. SENTENCES LOST  — materially fewer sentence ends than the English, counted
                       on the language's own terminator (. 。 ۔ । ？ ！).

Checks 4 and 5 are measured on FRAGMENT GROUPS, not on single keys. The values
the template joins around a link are cut differently in every language — Hindi
and Bengali move the whole "for any question about this notice" clause from the
last fragment into the second, which is what the brief tells translators to do.
Measured per key that reads as 90% of the text missing; measured per group it is
what it is, which is complete. A checker that is confidently wrong about correct
input gets ignored, and then it is worse than not existing.

    python3 tools/i18n/coverage.py            # every language
    python3 tools/i18n/coverage.py hi bn      # just these

Exit code is non-zero for 1, 2 and 3 — the ones that mean something was not
translated. 4 and 5 print under LOOK.
"""
from __future__ import annotations

import json
import pathlib
import re
import statistics
import sys
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
CONTENT = HERE / "content"
SOURCE = "en"

# The writing system each page is set in, as unicodedata name prefixes.
SCRIPTS = {
    "zh-Hans": ("CJK",),
    "ja":      ("CJK", "HIRAGANA", "KATAKANA"),
    "ko":      ("HANGUL",),
    "ar":      ("ARABIC",),
    "ur":      ("ARABIC",),
    "hi":      ("DEVANAGARI",),
    "bn":      ("BENGALI",),
    "ru":      ("CYRILLIC",),
}

# Values the template concatenates around a link. Compared as one string,
# because where a clause sits inside the group is the translator's choice.
FRAGMENT_GROUPS = [
    ("pages.privacy.who_a", "pages.privacy.who_b", "pages.privacy.who_c", "pages.privacy.who_d"),
    ("pages.privacy.host_a", "pages.privacy.host_b", "pages.privacy.host_c"),
    ("pages.privacy.absent_links_a", "pages.privacy.absent_links_b"),
    ("pages.privacy.rights_p2a", "pages.privacy.rights_p2b"),
    ("pages.notfound.report_before", "pages.notfound.report_link", "pages.notfound.report_after"),
]
IN_A_GROUP = {k for g in FRAGMENT_GROUPS for k in g}

TERMINATORS = "[.。۔।？！?!]"

# Dots that end no sentence. These are ABBREVIATIONS and must be matched on a
# word boundary: the first version of this list held the bare string "n.", and
# str.replace ate the final period of every German sentence ending in a word
# like "anzunehmen." — which reported six correct German paragraphs as having
# lost two thirds of their sentences.
NOT_A_SENTENCE_END = re.compile(
    r"\b(?:no|No|n|nr|Nr|Art|art|art\. ?\d+|Abs|cfr|vgl|стр|ст)\.", re.UNICODE)

# Names and identifiers that are supposed to survive verbatim. A value made of
# nothing but these is legitimately identical in every language.
LITERALS = [
    "Spinne Software di Luci Manuel", "Spinne Software", "Sparkle",
    "sparkle.software", "spinnesoftware.com", "hello@spinnesoftware.com",
    "spinnesoftware@pec.it", "IT 18636231005", "RM-1797481", "REA", "PEC",
    "LinkedIn", "GitHub Pages", "Fastly", "Stripe", "OpenRouter", "Deepgram",
    "Higgsfield", "Whisper", "ONNX Runtime", "NVENC", "VideoToolbox",
    "Quick Sync", "H.264", "HEVC", "AV1", "DNxHR", "HDR", "EBU R128", "GPU",
    "API", "GDPR", "SOC 2", "ISO/IEC 27001", "3D LUT", "x264", "x265", "SVT-AV1",
]

# Deliberately identical everywhere. The motto is a name, not a sentence:
# translating it produces fifteen mottos and the company then has none.
NEVER_DIFFERS = {"pages.home.rail_motto"}

EN_STOPWORDS = {
    "the", "and", "with", "that", "which", "without", "your", "our", "their",
    "there", "when", "what", "from", "into", "rather", "because", "every",
    "nobody", "something", "does", "cannot", "they", "them", "these", "those",
    "than", "then", "only", "also", "both", "each", "such", "while", "where",
    "whose", "about", "after", "before", "between", "through", "is", "are",
    "was", "were", "been", "have", "has", "will", "would", "could", "should",
}
# Words above that are ordinary words in a target language. German "was"/"will",
# Italian "in", Indonesian "are": without this the same correct sentences are
# reported forever.
STOPWORD_EXCEPTIONS = {
    "de": {"was", "will", "in", "hat", "ist", "also", "der", "die"},
    "id": {"has", "are", "when"},
    "it": {"in", "one", "e"},
    "es": {"in", "no", "the"},
    "fr": {"on", "in", "the", "or"},
    "pt-BR": {"in", "no", "a", "the", "e"},
    "ru": {"in"},
    "ko": set(), "ja": set(), "zh-Hans": set(), "ar": set(), "ur": set(),
    "hi": set(), "bn": set(),
}


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}.{i}")
    elif isinstance(node, str):
        yield path, node


def strip_markup(s: str) -> str:
    return re.sub(r"<[^>]+>|&\w+;", " ", s)


def without_literals(s: str) -> str:
    out = strip_markup(s)
    for lit in LITERALS:
        out = out.replace(lit, " ")
    return out


def is_identifier_only(s: str) -> bool:
    """Nothing but names, numbers and punctuation — identical by design."""
    return not re.search(r"[^\W\d_]", without_literals(s), re.UNICODE)


def en_words(s: str) -> int:
    return len(re.findall(r"[A-Za-z]{2,}", without_literals(s)))


def scripts_in(text: str) -> set:
    return {unicodedata.name(ch, "?").split()[0] for ch in text if ch.isalpha()}


def sentences(text: str) -> int:
    s = NOT_A_SENTENCE_END.sub(" ", without_literals(text))
    s = re.sub(r"\d+[.,]\d+", " ", s)
    return len(re.findall(TERMINATORS, s))


def lower_words(text: str) -> set:
    return set(re.findall(r"[a-z]{2,}", without_literals(text).lower()))


def main(argv) -> int:
    src = dict(walk(json.loads((CONTENT / f"{SOURCE}.json").read_text(encoding="utf-8"))))
    langs = argv[1:] or sorted(p.stem for p in CONTENT.glob("*.json") if p.stem != SOURCE)

    failures = advisories = 0
    for lang in langs:
        tr = dict(walk(json.loads((CONTENT / f"{lang}.json").read_text(encoding="utf-8"))))
        own = SCRIPTS.get(lang)
        exceptions = STOPWORD_EXCEPTIONS.get(lang, set())
        fails, looks = [], []

        # Units of comparison: single keys, plus each fragment group joined.
        units = []
        for key, en in src.items():
            if key == "_note" or key in IN_A_GROUP or key not in tr:
                continue
            units.append((key, en, tr[key]))
        for group in FRAGMENT_GROUPS:
            if all(k in src and k in tr for k in group):
                units.append(("+".join(k.split(".")[-1] for k in group),
                              "".join(src[k] for k in group),
                              "".join(tr[k] for k in group)))

        ratios = [len(without_literals(t)) / len(without_literals(e))
                  for _k, e, t in units
                  if len(without_literals(e)) >= 60 and e != t]
        median = statistics.median(ratios) if ratios else 1.0

        for key, en, got in units:
            if not en.strip():
                if got.strip():
                    fails.append(f"[English is empty, this is not]      {key}")
                continue
            if not got.strip():
                fails.append(f"[empty]                              {key}")
                continue
            if key in NEVER_DIFFERS or is_identifier_only(en):
                continue

            prose = en_words(en) >= 4

            # 1. Still English — only where a coincidence is unavailable.
            if got == en and prose:
                fails.append(f"[still English]  {key}  {en[:60]!r}")

            # 2. English leaked into a translated sentence.
            leaked = sorted((lower_words(got) & EN_STOPWORDS) - exceptions)
            if len(leaked) >= 2 and got != en:
                fails.append(f"[English leaked: {', '.join(leaked[:5])}]  {key}  {got[:60]!r}")

            # 3. None of the page's own script, in prose.
            if own and prose and not (scripts_in(got) & set(own)):
                fails.append(f"[no {'/'.join(own)} anywhere]  {key}  {got[:50]!r}")

            # 4. Length outlier against this language's own median.
            if len(without_literals(en)) >= 60 and got != en:
                r = len(without_literals(got)) / len(without_literals(en))
                if r < median * 0.55:
                    looks.append(f"[{r:.2f}x vs {median:.2f}x median — short]  {key}")
                elif r > median * 2.0:
                    looks.append(f"[{r:.2f}x vs {median:.2f}x median — long]  {key}")

            # 5. Sentences lost.
            en_s, got_s = sentences(en), sentences(got)
            if en_s >= 3 and got_s <= en_s - 2:
                looks.append(f"[{en_s} sentence ends -> {got_s}]  {key}")

        flag = "ok  " if not fails else "FAIL"
        print(f"  {flag} {lang:<8} {len(units)} units   median {median:.2f}x"
              f"   {len(fails)} problem(s)   {len(looks)} to look at")
        for f in fails:
            print(f"        FAIL  {f}")
        for l in looks:
            print(f"        LOOK  {l}")
        failures += len(fails)
        advisories += len(looks)

    print()
    if failures:
        print(f"  {failures} untranslated or part-English value(s); {advisories} advisory")
        return 1
    print(f"  ok    every value translated in all {len(langs)} languages "
          f"({advisories} advisory, none blocking)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
