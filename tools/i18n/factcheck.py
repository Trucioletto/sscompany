#!/usr/bin/env python3
"""Did a translation quietly change what the site SAYS?

validate.py proves the shape matches. consistency.py proves a term is rendered
the same way twice. Neither can see the failure that would actually damage the
company: a sentence that is a denial in English arriving as an assertion.

REVIEWING.md puts it first for a reason. "There is no SOC 2 attestation" turning
into "there is a SOC 2 attestation" is a false compliance claim on a page whose
whole purpose is to be checked by people doing diligence. The same applies to
card data never reaching us, the controller keeping no logs, not selling
personal information, and the speech-to-text sentence, which an earlier version
of this site got wrong in English and had to correct.

The test: every English string that carries a negation must carry one in the
translation too. It cannot tell you the negation attaches to the right verb —
only a reader can — but a DROPPED negation has nowhere to hide from it.

It also checks the identifiers, which must survive byte-for-byte, and the
marketing vocabulary the brief bans.

    python3 tools/i18n/factcheck.py
    python3 tools/i18n/factcheck.py de ja
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
CONTENT = HERE / "content"

# A word that makes an English sentence a denial. Ordered longest-first so
# "cannot" is not counted twice.
EN_NEG = re.compile(
    r"\b(?:cannot|can't|doesn't|don't|isn't|aren't|won't|never|neither|nor|"
    r"nothing|nobody|none|without|not|no)\b", re.I)

# "VAT no. IT 18636231005" is an abbreviation for "number", not a denial. It put
# pages.privacy.who_b on the report for all fourteen languages — a checker
# confidently wrong about the English before it ever looked at a translation.
ABBREV = re.compile(r"\b(?:VAT|REA)\s+no\.", re.I)

# The negation machinery of each language. Not a dictionary of "no" — the forms
# that actually carry sentence negation, including the bound morphemes that
# Korean and Japanese use where European languages use a particle.
NEG = {
    # Each list needs the bare answer-word as well as the sentence particle:
    # the site literally says "the answers, including the ones that are no", and
    # German renders that "nein", French "non". Both were missing, which is why
    # de and fr reported four dropped negations that were never dropped.
    "it":      r"non|mai|né|nessun|nulla|nient|senza|neppure|nemmeno|\bno\b",
    "es":      r"no|ni|nunca|jamás|ningun|ningún|nada|nadie|sin|tampoco",
    "fr":      r"ne |n'|pas|jamais|aucun|ni |rien|personne|sans|\bnon\b",
    "pt-BR":   r"não|nunca|jamais|nem|nenhum|nada|ninguém|sem",
    "de":      r"nicht|kein|nie|niemals|niemand|nichts|ohne|weder|\bnein\b",
    "ru":      r"не|ни|нет|никогда|ничего|никто|без",
    "id":      r"tidak|bukan|tanpa|tak |belum|jangan|tiada|tak,|takkan",
    "zh-Hans": r"不|没|无|未|非|否|别|从不|并不",
    # «いいえ» e «否» sono la parola giapponese per «no». Mancavano, e la pagina
    # dice «Where the answer is no, we say that too»: la resa corretta
    # 「答えが「いいえ」になるところも」 veniva segnalata come negazione persa.
    "ja":      r"ない|なし|なけれ|なかっ|ありません|ません|ず|なく|いない|いいえ|否|不|無|非|以外",
    # «안» e il negatore preverbale piu comune del coreano («안 됩니다»), e
    # non combaciava con «아니»: in NFD la sua ᆫ finale e un jongseong, non
    # il ᄂ iniziale di 아니. Lo spazio finale evita 안내, 안전 e simili.
    "ko":      r"않|없|아니|안 |못|아닙|없습|않습|미|비",
    # «ليس» si coniuga cambiando radice: «لسنا» (non siamo) e «لست» non
    # contengono «ليس» come sottostringa, quindi sfuggivano. «تعذّر» e una
    # negazione lessicale — «e risultato impossibile» — senza particella.
    "ar":      r"لا|ليس|لسنا|لست|لسن|ليسوا|تعذّر|تعذر|لم|لن|ما |دون|غير|بلا|ولا|أي ",
    "ur":      r"نہیں|نہ |بغیر|بلا|کوئی|کبھی|نفی|بجائے",
    "hi":      r"नहीं|न |बिना|कोई|कभी|ना ",
    "bn":      r"না|নয়|নেই|ছাড়া|বিনা|কখনো|কোনো",
}

# Must survive byte-for-byte in every language.
IDENTIFIERS = [
    "IT 18636231005", "RM-1797481", "Spinne Software", "Sparkle",
    "sparkle.software", "spinnesoftware.com", "hello@spinnesoftware.com",
    "spinnesoftware@pec.it", "ONNX Runtime", "SOC 2", "ISO/IEC 27001",
    # The model names on /about/. They are the one part of that page a reader can
    # check against the product, so a translation that drops or transliterates one
    # should fail here rather than ship.
    "Claude", "GPT-5", "Gemini", "Google Veo", "Kling", "MiniMax Hailuo",
    "Luma Ray", "Nano Banana", "FLUX", "Seedream", "Ideogram", "ElevenLabs",
    "Suno", "Topaz", "fal.ai", "OpenRouter", "AI/ML API", "Higgsfield",
]

# Words the brief bans outright, plus the local equivalents that mean nothing.
BANNED = {
    "*":       r"\b(?:revolutionary|cutting-edge|game-?changing|best-in-class)\b",
    "it":      r"\b(?:rivoluzionari[oa]|all'avanguardia|senza soluzione di continuità|potenzia)\w*",
    "es":      r"\b(?:revolucionari[oa]|vanguardia|sin fisuras|potenciar|empoderar)\w*",
    # `de pointe` is bounded: the \w* that inflects the others also swallowed the
    # ordinary verb `pointer`, and a guard against marketing language has no
    # business flagging "permet de pointer un modèle sur…".
    "fr":      r"\b(?:révolutionnaire\w*|de pointe\b|sans couture\w*|sans faille\w*)",
    # `de ponta` è delimitato per la stessa ragione del francese `de pointe`: lo \w*
    # che flette gli altri termini si mangiava anche «de ponta a ponta», che vuol dire
    # «da cima a fondo» e non ha niente a che vedere con il marketing.
    "pt-BR":   r"\b(?:revolucionári[oa]\w*|de ponta\b(?!\s+a\s+ponta)|sem emendas\w*|sem costura\w*|empoderar\w*)",
    "de":      r"\b(?:revolutionär|nahtlos|wegweisend|bahnbrechend)\w*",
    "ru":      r"\b(?:революционн|беспроблемн|бесшовн|передов)\w*",
    "id":      r"\b(?:revolusioner|mulus tanpa|terdepan|canggih)\w*",
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


def main(argv) -> int:
    en = dict(walk(json.loads((CONTENT / "en.json").read_text(encoding="utf-8"))))
    langs = argv[1:] or sorted(p.stem for p in CONTENT.glob("*.json") if p.stem != "en")

    # Only strings long enough to be a sentence. A three-word nav label with
    # "no" in it is not a claim anyone does diligence on.
    # _note is documentation for translators, not page copy; TRANSLATING.md
    # tells them to copy it verbatim, so of course it is still English.
    denials = {k: v for k, v in en.items()
               if not k.endswith("_note")
               and EN_NEG.search(ABBREV.sub(" ", strip_markup(v)))
               and len(v.split()) >= 6}

    print(f"  {len(denials)} English strings carry a negation\n")
    problems = []

    for lang in langs:
        d = dict(walk(json.loads((CONTENT / f"{lang}.json").read_text(encoding="utf-8"))))
        neg = re.compile(unicodedata.normalize("NFD", NEG[lang])
                         if lang == "ko" else NEG[lang], re.I)

        # Hangul composes jamo into precomposed syllable blocks, so 아니 ("not")
        # is NOT a substring of 아닌 ("that is not") — they share no codepoint
        # after the first. Searching for the citation form finds nothing the
        # moment the word is inflected, which is always. Decomposing both sides
        # turns the block back into its jamo and makes the stem findable.
        def norm(s, _l=lang):
            return unicodedata.normalize("NFD", s) if _l == "ko" else s

        missing = [k for k in denials
                   if k in d and not neg.search(norm(strip_markup(d[k])))]

        ident = []
        for k, v in en.items():
            for token in IDENTIFIERS:
                if token in v and k in d and token not in d[k]:
                    ident.append(f"{k}: {token!r} missing")

        bad = []
        for pat in (BANNED["*"], BANNED.get(lang)):
            if not pat:
                continue
            for k, v in d.items():
                for m in re.finditer(pat, v, re.I):
                    bad.append(f"{k}: {m.group(0)!r}")

        bang = [k for k, v in d.items() if "!" in v and "!" not in en.get(k, "!")]

        flag = "ok " if not (missing or ident or bad or bang) else "LOOK"
        print(f"  {flag} {lang:<8} negations {len(denials) - len(missing)}/{len(denials)}"
              f"   identifiers {'ok' if not ident else str(len(ident)) + ' missing'}"
              f"   banned {len(bad)}   '!' {len(bang)}")
        for k in missing:
            problems.append(f"{lang} {k}\n        en: {en[k][:110]}\n        {lang}: {d[k][:110]}")
        problems += [f"{lang} identifier {x}" for x in ident]
        problems += [f"{lang} banned word {x}" for x in bad]
        problems += [f"{lang} exclamation mark not in the English: {k}" for k in bang]

    print()
    if problems:
        for x in problems:
            print(f"  FAIL  {x}")
        print(f"\n  {len(problems)} to look at")
        return 1
    print("  ok    every denial is still a denial, identifiers intact, no banned vocabulary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
