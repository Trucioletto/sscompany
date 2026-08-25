# Reviewing a translation

You are not the person who wrote it. Read `TRANSLATING.md` first — it is the
brief the translator worked to, and half of reviewing is knowing what was asked
for.

Your job is to find what would embarrass the company, in this order.

## 1. Facts (fix on sight)

The site exists to be checked by investors, partners and suppliers. A
translation that changes what it says is worse than no translation.

- **Dropped or inverted negations.** The single worst failure available here.
  `There is no SOC 2 attestation and no ISO/IEC 27001 certificate` must stay a
  denial in every language. So must: card data *never* reaches us; *no* card
  number touches a system we operate; *not* a partnership, endorsement or
  affiliation; the controller keeps *no* logs; we do *not* sell your personal
  information; *never* used to profile you; *not* directed at children; the
  whole list of absences in "What is not here"; and `one signature is not
  enough`.
- **The speech-to-text sentence.** English says speech to text *can* run
  locally, that cloud engines also exist, and that **the default reaches for a
  cloud engine first**. An earlier version of this site claimed it always ran
  locally; that was false and was corrected. A translation that flattens it back
  to "runs on your machine" reintroduces a false claim about where a customer's
  audio goes. Check it word by word.
- **Numbers and identifiers.** Twelve clips, three cameras, four vendor stacks,
  three editors and three seats, Article 6(1)(f), Articles 15 to 22, 10 July
  2023, 24 August 2026, `IT 18636231005`, `RM-1797481`. Writing a number as a
  digit where the language does that is correct; changing it is not.
- **Nothing added.** No claim, customer, certification, guarantee or date that
  is not in the English. `The desktop editor is free` must not become a promise
  that it stays free.
- **`In private preview`** must survive. The product has not launched.

## 2. Language (fix on sight)

- Grammatical errors, wrong agreement, wrong particles, wrong spacing.
- The wrong legal term. The privacy notice must use the vocabulary of the
  official version of the GDPR in your language where one exists.
- A technical term rendered as something that means a different thing.
- Text that reads as machine output: calques, false friends, a word order no
  native writer would use, transliteration where a real word exists.

## 3. Voice (report, do not change)

The register is a serious business publication, not a brochure: short
declarative sentences, dry, no marketing words, no exclamation marks. If a
choice is defensible but you would have made another, **say so and leave it**.
The translator had reasons you cannot see, and a reviewer rewriting to taste is
how a consistent voice becomes fifteen inconsistent ones.

## What to change, and how

Edit `content/<code>.json` in place. Keep the key set, the nesting, the array
lengths, the `<strong>`/`<em>`/`&middot;`/`&nbsp;` tokens and the leading and
trailing spaces on the link fragments exactly as they are.

Then run, from the repository root:

    python3 tools/i18n/validate.py <code>
    python3 tools/i18n/build.py
    ./check.sh

All three must pass before you report.

## What to report

1. Every change you made, with the English, the old translation and the new one.
2. Everything you would change but did not, and why you left it.
3. One sentence: would you sign this page as your own work?
