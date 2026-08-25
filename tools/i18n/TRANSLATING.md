# Translating this site

English is the source. Every file in `content/` other than `en.json` is a
translation of it. Translate `en.json` into `<code>.json` with the **same keys,
the same nesting and the same array lengths**, and nothing else.

The build refuses to run if a key is missing, so a partial file fails loudly
rather than shipping a blank paragraph.

---

## 1. What this company sounds like

The site exists so that investors, partners, suppliers and the press can check
an Italian software company and come away convinced it is serious. It is not an
advertisement and must never read like one.

- **Short declarative sentences.** Statements of fact, not claims.
- **Dry, occasionally wry.** "an Italian tax authority does not file bug
  reports" is a joke, and it is the only kind this site makes: understated,
  never at the reader's expense, never a pun.
- **No marketing register.** No exclamation marks. No "revolutionary",
  "cutting-edge", "seamless", "empower", "unlock", "game-changing", "solution".
  If your language has an equivalent set of words that mean nothing, avoid those
  too.
- **Concrete over abstract.** The English says "twelve clips from three cameras"
  rather than "multiple assets". Keep the specificity.
- **Confident, never boastful.** The site says what exists and what does not. It
  admits there is no SOC 2 attestation. Do not soften that; it is the point.

The register to aim for is a serious trade or business publication in your
language — *Il Sole 24 Ore*, *Handelsblatt*, *Nikkei*, *Les Echos* — not a
product brochure and not a press release.

## 2. Never translate

Leave these **exactly** as they appear, in Latin script, in every language
including those with a different writing system:

Spinne Software · Spinne Software di Luci Manuel · Sparkle · sparkle.software ·
spinnesoftware.com · hello@spinnesoftware.com · spinnesoftware@pec.it · PEC ·
IT 18636231005 · RM-1797481 · REA · Registro Imprese · LinkedIn · GitHub Pages ·
Fastly · Stripe · OpenRouter · Google Cloud · Deepgram · fal.ai · Higgsfield ·
Whisper · ONNX Runtime · NVIDIA · NVENC · Intel Quick Sync · AMD · Apple ·
AI/ML API · Claude · GPT-5 · Gemini · Google Veo · Kling · MiniMax Hailuo ·
Luma Ray · Nano Banana · FLUX · Seedream · Ideogram · ElevenLabs · Suno · Topaz ·
VideoToolbox · x264 · x265 · SVT-AV1 · H.264 · HEVC · AV1 · DNxHR · HDR ·
3D LUT · EBU R128 · GPU · API · GDPR · SOC 2 · ISO/IEC 27001

`impresa individuale` in `facts.legal_form_value` stays in Italian — it is the
legal form as the Italian register records it — but the surrounding words are
translated.

`pages.home.rail_motto` is **Weave the web**, and it stays in English in all
fifteen languages. It is the company's motto, which is a name rather than a
sentence: translating it produces fifteen different mottos and the company then
has none. The paragraph under it, `rail_motto_body`, IS translated — it is the
thing that explains the motto to a reader who does not speak it.

If your language conventionally writes an acronym differently (for example GDPR
is *RGPD* in French and Spanish, *DSGVO* in German), use your language's
standard form. That is a translation, not a rename.

## 3. Markup you must preserve

Some values contain HTML. Keep the tags and entities byte-for-byte; translate
only the words between them.

- `<strong>…</strong>`, `<em>…</em>`
- `&middot;` (the separator in the legal line), `&nbsp;` (a non-breaking space)
- `&copy;` if present

Never add tags that are not in the English. Never use straight quotes `"` inside
a value without escaping them for JSON.

## 4. Fragments that wrap a link

A few values are **sentence fragments** that the template joins around a link.
They must read as one correct sentence once joined, which usually means the word
order has to change and the fragments have to be re-cut differently in your
language. This is the part machine translation gets wrong.

| Key | Joined result in English |
| --- | --- |
| `pages.about.built_p1` | `Sparkle` + this + link + `.` |
| `pages.privacy.who_a` / `who_b` / `who_c` / `who_d` | text + **name** + text + link + text + link + text |
| `pages.privacy.host_a` / `host_b` / `host_c` | text + link + text + link + text + link — three processors, so the separators are a comma and an "and" |
| `pages.privacy.absent_links_a` / `absent_links_b` | text + link + text |
| `pages.privacy.rights_p2a` / `rights_p2b` | text + link + text |
| `pages.notfound.report_before` / `report_link` / `report_after` | text + link + text |

If your language cannot put the link where English puts it, move the words
between the fragments — the fragments exist to be re-balanced. Leading and
trailing spaces in these values are load-bearing: keep them where the join needs
them.

## 5. The idioms

These carry the voice and must be **adapted, not translated literally**. Find
the equivalent that a native reader would find natural and slightly dry. If a
literal rendering would be baffling, write the nearest true thing instead.

- `Hard technology, simple software.` — the home page h1, and the shortest
  statement of what the company is. Two halves, and the contrast between them is
  the whole sentence: the difficulty is real and it is on our side of the screen.
  Not "powerful and easy", which is a brochure saying nothing.
- `Spiders do not spin for the pleasure of it. The structure is what makes
  everything after it possible.` — *Spinne* is German for spider; the company is
  named after it. The web metaphor must survive.
- `Independence is not a preference. It is the difference between choosing and
  being told.` — the /about/ pull quote. "Being told" is being handed someone
  else's roadmap, not being given advice. It sits in a 26-character measure, so
  the shorter your rendering the better.
- `The machine takes the labour. You keep the cut.` — "the cut" is the editor's
  creative decision, not a wound.
- `Money deserves accounting, not hope.`
- `A retry does not become a second charge.`
- `an Italian tax authority does not file bug reports`
- `A customer never sees any of it. Anyone doing diligence sees all of it.`
- `Nothing is somebody else's problem`
- `AI is not a button`
- `Never let the preview lie`

## 6. Length

Most languages run 15–30% longer than English. The layout is a fixed 34rem
reading column and a 16.5rem rail, and long words break it.

- `nav.*`, `facts.*` and `cta.*` are **interface labels in a narrow column**.
  Keep them at or below the English character count. `nav.how` has about 14
  characters of room.
- `pages.home.what` is the six values, each `{name, body}`. The **name** is one
  word in a cell about 26 characters wide — one word in your language too, and if
  the obvious noun is a four-syllable abstraction, prefer the plain word a trade
  publication would use. The **body** is one sentence that makes the value
  checkable rather than decorative; keep it to a single sentence.
- Headings (`h1`, `h2_*`) should not grow by more than about a third.
- Body paragraphs may run long.
- German, Finnish-style compounds and Tamil-style agglutination: prefer two
  short words to one unbreakable long one.

## 7. The privacy notice is a legal document

`pages.privacy.*` is not marketing copy. Use the **established legal vocabulary
of your language**, not a literal rendering:

- "data controller" → *titolare del trattamento* (it), *Verantwortlicher* (de),
  *responsable du traitement* (fr), *responsable del tratamiento* (es)
- "legitimate interest", "supervisory authority", "erasure", "restriction",
  "processor" all have fixed terms in the GDPR's own official translations.
  **Use the wording from the official version of the GDPR in your language.**
  Article numbers and the Regulation's name do not change.

Do not soften, strengthen or reinterpret any statement about what is collected.
The English text is the authoritative one and the notice says so.

## 8. Do not

- Do not add a sentence that is not in the English, however helpful.
- Do not remove one, however redundant it looks.
- Do not add a claim, a number, a certification, a customer or a date.
- Do not localise the currency, the company's country or the legal identifiers.
- Do not translate the `_note` key — drop it, or copy it verbatim.

## 9. Output

Write `content/<code>.json`, UTF-8, no BOM, `ensure_ascii=false` — real
characters, not `\uXXXX` escapes. Then run:

    python3 tools/i18n/build.py
    ./check.sh

`build.py` fails on a missing key. `check.sh` fails if a rendered character has
no glyph in the declared font subsets, which is how a stray curly quote or an
en-dash in a language that does not use one gets caught.

Then, before a release:

    python3 tools/i18n/coverage.py
    python3 tools/i18n/sweep.py

`coverage.py` answers the question the other checks cannot: is this language
actually translated, and translated whole. It finds a value left in English, a
clause left in English inside a translated sentence, prose on a non-Latin page
with none of that page's own script, a paragraph that arrived truncated and a
paragraph that lost sentences. It measures the fragment families as ONE string,
because where a clause sits inside a group is your choice (see section 4).

`sweep.py` renders all 76 pages at four widths in headless Chrome and fails on anything
the markup checks cannot see: a word too long to break pushing the page
sideways, an image that does not load, an unfilled template token, a tap target
under the 24px minimum. It found nav labels 11px wide in Korean, Urdu, Hindi and
Bengali — "Home" is one syllable in several of these languages, and the layout
had only ever been measured in English.

---

## 10. The vocabulary of /how-we-build/

That page was rewritten to be about the architecture of the editor and what it
means to put an AI inside one. It is dense with terms of art, and the register
is an engineer explaining a decision to another engineer — not a product page.

**The metaphor the page turns on is the SEAM.** "In most tools there is a seam.
You export, you upload, you wait, you download, you put the result back and hope
it still lines up." It returns twice more ("the seam reappearing at the other end
of the pipeline"). It must be one word in your language, the same word every
time, and it must be the physical seam of two things joined — a join, a weld, a
join line — not a metaphor about gaps or holes.

**Terms of art. Use the form YOUR engineering community actually writes**, which
for several of these is the English term, and which is not the same answer in
every language:

| English | What it means here |
| --- | --- |
| operation | A named, typed change to the document. The editor's unit of work. Not "operazione chirurgica"; the sense is closer to a command or an instruction. |
| document | The project file's data model — what happens when. Not a text document. |
| caller | Something that invokes an operation. The assistant is "another caller". |
| compare-and-swap | The concurrency primitive. Most languages keep it in English or use the standard local calque; do not invent one. |
| head operation | The document's current version marker, the thing the swap compares against. |
| claim / claimed | The executor asks the plan store for permission and is granted it, atomically. A reservation, not an assertion of ownership. |
| exactly once | The delivery guarantee. Every language that writes about queues has a settled form. |
| replay | Re-running a step that already ran. It returns the first result rather than acting again. |
| checkpoint | The undo point. One operation collapses to one. |
| shaders, scrub, render, export, proxies | Keep as the local post-production trade uses them, consistent with /sparkle/. |

**Do not soften the argument into marketing.** Sentences like "an edit applied
twice to a timeline is not a duplicate — it is a different timeline" and "what
proves an operation happened is a recorded operation id, not a flag in a browser
tab" are the point of the page. They are precise, and a vaguer rendering loses
the claim.

**`shape.*` are rail labels in a 264px column.** `Document`, `Assistant`,
`Undo`, `Concurrency`, `Execution`, `Local models` and their values must stay
short — at or under the English character count.
