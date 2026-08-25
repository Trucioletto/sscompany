/* ARRIVE IN YOUR OWN LANGUAGE.

   The site publishes fifteen versions and English sits at the root, so somebody
   who types the domain gets English whatever they speak. This reads the
   browser's language list once and, if a version exists, replaces the address
   with it. Nothing is stored, nothing is sent, nothing is remembered.

   Loaded from <head> without defer on purpose. Deferred, the English page has
   already painted by the time this runs and the reader watches it swap; the
   cost of avoiding that is one blocking request for a file smaller than the
   favicon, on the same connection as the page.

   THREE WAYS THIS GOES WRONG, AND WHAT STOPS EACH:

   1. The loop. GitHub Pages serves 404.html for every unknown path, and that
      document says lang="en" no matter what URL produced it. Deciding from the
      lang attribute, /it/nonesuch would look like an English page and be sent
      to /it/it/nonesuch, which is also unknown, which is also lang="en"...
      So the decision is made from the PATH: if the first segment is already one
      of the fifteen, this has nothing to do.

   2. The trap. English is the root, so a reader with an Italian browser who
      deliberately picks English from the switcher would land on / and be sent
      straight back to /it/, with no way out but to fight it. A same-origin
      referrer means the reader chose this page from inside the site, and a
      choice is not something to overrule. Storing the preference would work
      too, and would cost the notice its "no storage" sentence for a flag.

   3. The crawler. Googlebot renders scripts and reports en-US, so it is never
      redirected off an English page and the root stays indexable. It is worth
      saying plainly that Google advises against automatic language redirects
      at all: the hreflang cluster is what actually makes the other fourteen
      findable, and this only changes where a human lands. */
(function () {
  'use strict';

  /* Same order as the switcher, and the same strings: these are the directory
     names, so a typo here is a redirect to a page that does not exist. */
  var CODES = ['en', 'zh-Hans', 'hi', 'es', 'fr', 'ar', 'bn', 'pt-BR', 'ru',
               'ur', 'id', 'de', 'ja', 'ko', 'it'];
  var DEFAULT = 'en';

  var path = location.pathname;
  var first = path.split('/')[1];

  /* Already under a language prefix — including the 404 case above. */
  for (var i = 0; i < CODES.length; i++) {
    if (first === CODES[i]) return;
  }

  /* Arrived from somewhere on this site, so this address was chosen. */
  /* origin + '/' and not origin alone: "https://spinnesoftware.com.example/"
     starts with the origin too. Getting this wrong only ever suppresses a
     redirect that should have happened, never causes one that should not — but
     a same-origin test that is not one is worth two characters to fix. */
  if (document.referrer && document.referrer.indexOf(location.origin + '/') === 0) return;

  var tags = navigator.languages || (navigator.language ? [navigator.language] : []);

  /* A browser in Taiwan or Hong Kong sends zh-TW — or zh-Hant-TW, zh-Hant — and
     then a bare zh. Decided tag by tag, the Traditional one is refused and the
     bare one that follows matches Simplified anyway, which is the opposite of
     the intent. So Chinese is settled once, from the first Chinese tag in the
     list, before any matching starts. */
  var zhSimplified = null;
  for (var z = 0; z < tags.length; z++) {
    var zt = String(tags[z]).toLowerCase();
    if (zt.split('-')[0] === 'zh') {
      zhSimplified = !/hant|-tw|-hk|-mo/.test(zt);
      break;
    }
  }

  function match(tag) {
    var t = String(tag).toLowerCase();
    var base = t.split('-')[0];
    if (base === 'zh') return zhSimplified ? 'zh-Hans' : null;
    for (var j = 0; j < CODES.length; j++) {
      if (CODES[j].toLowerCase() === t) return CODES[j];
    }

    /* Only Brazilian Portuguese is published. A reader in Portugal gets it for
       the same reason a reader in Britain gets American English here. */
    if (base === 'pt') return 'pt-BR';

    for (var k = 0; k < CODES.length; k++) {
      if (CODES[k].toLowerCase() === base) return CODES[k];
    }
    return null;
  }

  for (var n = 0; n < tags.length; n++) {
    var code = match(tags[n]);
    if (!code) continue;
    if (code === DEFAULT) return;           /* English is already here */
    /* replace, not assign: pressing Back should leave the site rather than
       return to a page that immediately forwards again. */
    location.replace('/' + code + path + location.search + location.hash);
    return;
  }
})();
