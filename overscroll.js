/* THE TOP EDGE, MADE TO GIVE.

   Why this file exists at all, on a site whose whole point was that it has no
   script. Three things were tried first, in the browser, and all three came
   back empty:

     1. The field as page content positioned above the document origin.
        Not painted. The overscroll area does not show the page.
     2. The field as a background image on the root element.
        Not painted either. Backgrounds do not reach that area.
     3. A flat background-colour on the root.
        THIS is the only thing that shows — and it does not animate: a moving
        background-position on the same element stayed frozen while the bounce
        ran.

   So the browser's own bounce can be one static colour and nothing more. It
   cannot carry a field with anything moving in it. The bounce had to be
   replaced rather than decorated, and replacing it needs a script.

   What this changes about the site's privacy claims: nothing. No cookie, no
   storage, no network request, no third party, nothing recorded. The notice
   says the site sets no cookies, runs no analytics and embeds nothing from
   elsewhere, and all three stay true. What is no longer true is the sentence
   "the page runs no script", which is why that comment changed too.

   TWO GESTURES, ONE PULL. A wheel arrives as a stream of deltas with no end
   event, a finger arrives as a position with a very clear one, so they are read
   separately and meet at the same accumulator. What they must NOT share is the
   idle timer: 90ms of silence ends a wheel gesture, and a finger that simply
   holds still is not finished with anything.

   The one thing this needs from the browser is overscroll-behavior: without it
   the native bounce runs underneath and the page is dragged twice. Where it is
   missing — iOS before 16 — the edge is left exactly as it was rather than
   taken over badly. */
(function () {
  'use strict';

  /* THE SCROLL CUE, AND IT LIVES ABOVE THE GUARDS BELOW ON PURPOSE.

     Everything after this point is the pull: an animation, correctly switched
     off for a reader who asked for less motion and for a browser without
     overscroll-behavior. The cue is not an animation. It is a hint that a long
     page continues, and a reader with reduced motion needs it at least as much
     as anyone — so it is set up here, before either guard, and the stylesheet
     is what takes the drift and the fade away for them.

     Two conditions, both from script, so a reader without any script never
     gets a label that cannot then go away: the reader is at the top, and there
     is more than 240px below. The length gate is what keeps it off a page with
     nothing under it — on a document shorter than the window scrollY is always
     zero, and without it the label would sit there forever pointing at nothing.

     And it is not there while the page is moving. A hint that rides along under
     moving text is furniture; the moment it has something to say is when the
     reader has stopped — anywhere, not only at the top. It goes at the first
     scroll event and comes back 1200ms after the last. The wait is the point:
     shorter and it flickers back between the small pauses inside one gesture,
     which is worse than never coming back at all. */
  var cueDoc = document.documentElement;
  var cueIdle = 0;

  function syncCue() {
    /* What is left BELOW where the reader is, not how long the page is. The
       first version measured the document and only ever showed the cue at the
       top, so it could not come back mid-page; measuring the remainder lets it
       come back anywhere, and takes itself away at the end of the page, where a
       label saying more follows would be pointing at nothing. */
    cueDoc.classList.toggle('has-more',
      cueDoc.scrollHeight - window.scrollY - window.innerHeight > 240);
  }

  function markScrolling() {
    cueDoc.classList.add('scrolling');
    window.clearTimeout(cueIdle);
    cueIdle = window.setTimeout(function () {
      cueDoc.classList.remove('scrolling');
    }, 1200);
  }

  syncCue();
  window.addEventListener('scroll', function () { syncCue(); markScrolling(); },
    { passive: true });
  window.addEventListener('resize', syncCue, { passive: true });

  var mm = window.matchMedia;
  if (mm && mm('(prefers-reduced-motion: reduce)').matches) return;
  if (!window.CSS || !CSS.supports || !CSS.supports('overscroll-behavior-y', 'none')) return;

  var doc = document.documentElement;
  var body = document.body;


  /* WHAT MOVES IS THE PAGE, NOT THE BODY.

     The transform used to sit on <body>, which is one write instead of three
     and was wrong for a reason CSS states plainly and this file learned the
     hard way: a transformed element becomes the containing block for every
     position: fixed descendant under it. There is exactly one on this site —
     .scroll-cue — and `bottom: 1rem` stopped meaning a rem above the viewport
     and started meaning a rem above the BOTTOM OF THE DOCUMENT. Measured on
     /it/sparkle/: the cue's box left y=622 and arrived at y=4687 in a 670px
     viewport, i.e. it vanished for the whole of every pull and came back
     afterwards. A reader at the top of the page — which is the only place this
     gesture works — is exactly the reader that invitation was written for.

     So the three blocks that make up the page carry it instead. They are flex
     items in a column; a transform on a flex item changes nothing about the
     layout, the compositor handles all three as cheaply as it handled one, and
     the scrollable overflow does not grow (checked: scrollHeight is 4735 either
     way). The skip link is left behind on purpose — it is absolute against the
     initial containing block, and a focus ring that stays where the eye expects
     it is better than one that rides an animation down. */
  var movers = [];
  (function () {
    var kids = body.children;
    for (var i = 0; i < kids.length; i++) {
      var tag = kids[i].tagName;
      if (tag === 'HEADER' || tag === 'MAIN' || tag === 'FOOTER') movers.push(kids[i]);
    }
  })();

  /* THE PULL, IN THE UNITS THE MOTTO IS DRAWN IN.

     The words are centred on the middle of the strip a reader can actually see,
     and that strip grows as the page opens — so the centre is a moving target
     and the type has to follow it. style.css does the following; this supplies
     the only number it cannot work out for itself.

     Not in CSS pixels, in the SVG's own units. The field declares a 1440x96
     viewBox with `slice`, so it scales by max(width / 1440, 1): exactly 1 up to
     a 1440px window and larger past it. A transform on a path inside that
     viewBox is in user units, so handing CSS the raw pixel distance would
     over-correct on any window wider than 1440 — by 5px at 1920, which is a
     quarter of the type's own height. Divided here, where the element that
     knows the scale is one query away, and cached because it only changes when
     the window does. */
  var netScale = 1;

  function measureNet() {
    var net = document.querySelector('.pull-net');
    netScale = net ? Math.max(net.clientWidth / 1440, 1) : 1;
  }

  measureNet();
  window.addEventListener('resize', measureNet, { passive: true });

  function centre(y) {
    doc.style.setProperty('--pull-u', (y / netScale).toFixed(2) + 'px');
  }

  function lift(css) {
    for (var i = 0; i < movers.length; i++) movers[i].style.transform = css;
  }

  /* 64px of travel against a 96px field: the field stays taller than the
     furthest the page can be pulled, so its own top edge is never reached and
     the white behind it never appears. */
  var MAX = 64;
  /* A wheel gesture has no end event. 90ms of silence is the end of one —
     comfortably longer than the ~16ms between events inside a real gesture,
     short enough that the release still feels like part of the same motion. */
  var IDLE = 90;
  var SETTLE_MS = 420;
  /* The whole length of the spinning, as the stylesheet lays it out. Nothing
     here reads it back; the two numbers have to agree, and this is the one
     place that says so. */
  var BUILD_MS = 700;
  /* The web is finished at 85% of the travel rather than at 100%. The last
     fifth of the pull is the part a reader only reaches by shoving, and a
     picture that completes only for the people who shove is a picture most
     people never see finished. */
  var FULL_AT = 0.85;

  var raw = 0;          /* what the wheel has asked for, before resistance. Only
                           ever positive: this edge is the top one. */
  var frame = 0;
  var idleTimer = 0;
  var release = 0;      /* timestamp the spring back started, 0 when not springing */
  var rescue = 0;
  var releaseFrom = 0;  /* how far open it was at that moment */

  /* THE TOP EDGE ONLY.
     overscroll-behavior-y has no per-edge form: `none` would turn the bounce
     off at the bottom too, and the bottom is the browser's to keep — nothing is
     revealed down there. So the class that carries it is put on only while the
     page is actually at the top, and taken off the moment it is not. By the time
     a reader reaches the bottom the class has been gone for a whole page of
     scrolling, and the native bounce is there waiting.

     The one exception is a page shorter than the window, where top and bottom
     are the same position: there the bottom bounce stays off. There is also
     nothing to scroll on such a page, so there is no bounce to miss.

     Set from script rather than from the stylesheet so that a reader without
     script — or with a coarse pointer, or with reduced motion asked for — keeps
     the browser's own behaviour instead of an edge that does nothing. */
  function syncEdge() {
    if (window.scrollY <= 0) doc.classList.add('pull-active');
    else doc.classList.remove('pull-active');
  }

  syncEdge();
  window.addEventListener('scroll', syncEdge, { passive: true });

  /* Asymptotic, so the page gives less the further it is pulled and can never
     pass MAX however hard the gesture is. exp() rather than a linear ratio
     because a linear one has a hard stop at the end, and the hard stop is the
     thing that makes a pull feel like a bug.

     STIFF is what makes the spinning legible. Against the bare curve, three
     ticks of a wheel — a flick — already opened it 94% of the way, so the web
     went from nothing to finished in one gesture and there was nothing to
     watch. At 2.5 the same flick opens it about two thirds; filling it takes a
     deliberate pull, which is the point of tying the picture to the distance. */
  var STIFF = 2.5;

  function resisted(v) {
    return MAX * (1 - Math.exp(-v / (MAX * STIFF)));
  }

  /* ONE SOURCE OF TRUTH, AND THE WEB IS DOWNSTREAM OF IT.
     The spinning used to run on its own 700ms clock the moment the class went
     on. A wheel gesture is often shorter than that, so the web was still being
     spun after the reader had finished pulling and let go — it always arrived
     late, and on release it did not leave, it was simply cut off.

     Now the distance drives it. --pull-t is a position on the stylesheet's
     timeline, every animation over there is paused, and each one's delay is
     its own stagger MINUS that position — a paused animation with a negative
     delay shows the frame it would be at. So the web is spun exactly as far as
     the page is open: half a pull is half a web, and letting go unwinds it
     through the same frames, backwards, in step with the page coming home.

     One transform and one custom property per frame, both on the root, both
     cheap; the fifty threads are the browser's problem and it solves them on
     the compositor. */
  function paint() {
    frame = 0;
    var y = travel();
    if (!y && !release && !raw) {
      done();
      return;
    }
    lift('translate3d(0,' + y.toFixed(2) + 'px,0)');
    var p = Math.min(1, y / MAX / FULL_AT);
    /* One property, and it used to be two. --pull-p carried the position of the
       front that decided WHERE the web had been spun so far; the front was the
       sweep mask, the mask was removed (style.css says why, at length), and the
       property went on being written every frame for months with no rule
       anywhere reading it. A number nothing reads is not free — it is a thing
       the next reader has to prove is dead. */
    doc.style.setProperty('--pull-t', (p * BUILD_MS).toFixed(1) + 'ms');
    centre(y);
    if (release) frame = window.requestAnimationFrame(paint);
  }

  /* Where the page actually sits: the resisted pull while the gesture is live,
     and the spring's own curve once it has been let go. The spring is run here
     rather than handed to a CSS transition because the web has to unwind on
     exactly the same curve, and two clocks cannot be trusted to agree. */
  function travel() {
    if (!release) return resisted(raw);
    var t = (now() - release) / SETTLE_MS;
    if (t >= 1) {
      release = 0;
      return 0;
    }
    /* The mirror of the ease the transition used: fast away, soft home. */
    var e = 1 - Math.pow(1 - t, 3);
    return releaseFrom * (1 - e);
  }

  function now() {
    return window.performance && window.performance.now
      ? window.performance.now()
      : new Date().getTime();
  }

  /* Two ways a pull ends, and both have to clean up. Released while still open,
     it springs back and tidies when the spring lands. Pushed shut against the
     scroll, it is already home and there is nothing to animate — but the class
     still has to come off, or the web goes on being spun on a field nobody can
     see, forever. The early return that used to sit here left exactly that. */
  function settle() {
    idleTimer = 0;
    if (!raw && !release) {
      done();
      return;
    }
    releaseFrom = resisted(raw);
    raw = 0;
    release = now();
    if (!frame) frame = window.requestAnimationFrame(paint);
    /* requestAnimationFrame does not run in a background tab, so a reader who
       switches away mid-spring would come back to a page still held open. This
       is the only thing that finishes the job in that case, and it costs one
       timer per gesture. */
    window.clearTimeout(rescue);
    rescue = window.setTimeout(function () {
      if (release) done();
    }, SETTLE_MS + 80);
  }

  function done() {
    window.clearTimeout(rescue);
    rescue = 0;
    release = 0;
    releaseFrom = 0;
    lift('');
    doc.style.removeProperty('--pull-t');
    doc.style.removeProperty('--pull-u');
    doc.classList.remove('is-pulling');
  }

  /* deltaMode is pixels on every trackpad and most mice, but a plain wheel can
     report lines or pages, and 3 lines read as 3px would make the field
     unreachable with a mouse. */
  function pixels(e) {
    if (e.deltaMode === 1) return e.deltaY * 16;
    if (e.deltaMode === 2) return e.deltaY * window.innerHeight;
    return e.deltaY;
  }

  function onWheel(e) {
    var d = pixels(e);
    if (!d) return;

    /* Ordinary scrolling, which is almost every event this handler will ever
       see: nothing is held open, and the wheel is not pushing up against a page
       that is already at its first pixel. */
    if (!raw && !(window.scrollY <= 0 && d < 0)) return;

    /* A pull collapses at zero and stops there. Pushing back hard enough must
       resume scrolling down the page, never open anything below. */
    var next = raw - d;
    if (next < 0) next = 0;

    /* The event that closes the pull is left alone, so the wheel tick that ends
       the gesture is also the one that resumes scrolling — no dead tick. */
    if (next !== 0 && e.cancelable) e.preventDefault();

    open(next);
    window.clearTimeout(idleTimer);
    idleTimer = window.setTimeout(settle, IDLE);
  }

  /* Where both gestures meet. `next` is how far the reader is asking for,
     before resistance; everything downstream of here is the same whether it
     came from a wheel or a finger. */
  function open(next) {
    /* Caught mid-flight: the spring is abandoned where it is, and the pull
       carries on from exactly that opening rather than from zero. */
    if (release) {
      raw = unresisted(travel()) + next;
      release = 0;
      releaseFrom = 0;
    } else {
      raw = next;
    }
    if (raw) doc.classList.add('is-pulling');
    if (!frame) frame = window.requestAnimationFrame(paint);
  }

  /* resisted() run backwards: what the accumulator would have to hold for the
     page to sit where it currently sits. */
  function unresisted(y) {
    return -MAX * STIFF * Math.log(1 - Math.min(0.999, y / MAX));
  }

  window.addEventListener('wheel', onWheel, { passive: false });

  /* THE FINGER.
     A drag is a position, not a stream of deltas, so the pull is measured from
     where the finger went down rather than accumulated — that way a finger that
     comes back up closes the field on the way, in step with itself.

     No idle timer on this path. A finger resting still is not a gesture that
     ended; touchend says that, and says it exactly. */
  var touchFrom = 0;
  var touchOpen = false;

  function onTouchStart(e) {
    if (e.touches.length !== 1) return;
    touchOpen = window.scrollY <= 0;
    touchFrom = e.touches[0].clientY - unresisted(travel());
  }

  function onTouchMove(e) {
    if (!touchOpen || e.touches.length !== 1) return;

    var next = e.touches[0].clientY - touchFrom;
    if (next < 0) {
      /* Dragged back past the top of the pull: hand the page back to the
         browser and re-anchor, so the same drag can go on to scroll down
         without the field reopening under it. */
      if (raw) open(0);
      touchOpen = window.scrollY <= 0;
      touchFrom = e.touches[0].clientY;
      return;
    }

    /* cancelable is false once the browser has committed the gesture to
       scrolling — which at the top, with overscroll-behavior none, it has not.
       Checked rather than assumed: preventing a non-cancelable event throws
       nothing but logs a warning on every frame. */
    if (e.cancelable) e.preventDefault();
    open(next);
  }

  window.addEventListener('touchstart', onTouchStart, { passive: true });
  window.addEventListener('touchmove', onTouchMove, { passive: false });
  window.addEventListener('touchend', settle);
  window.addEventListener('touchcancel', settle);


  /* Leaving the window mid-pull would come back to a page still held open. */
  window.addEventListener('blur', settle);


  /* NOTHING HAPPENS ON ARRIVAL, AND THAT IS THE INSTRUCTION.

     There was a greeting here: on an external arrival the page opened itself
     to 54px, spun the whole web, held it, and put it away again — 2.2 seconds
     of it — on the reasoning that the edge gesture was the only thing that ever
     drew the web and so almost nobody learned it was there.

     Asked for directly, and removed: a page that performs at you before you
     have done anything is a page that opened by itself. The cost is real and
     is accepted — the top edge is now undiscovered unless a reader pushes
     against it — and it is the smaller cost of the two.

     What went with it: GREET_*, the smoothstep, the referrer test that told an
     arrival from an internal click, and the hand-over in open() that let a
     gesture take the page over from a greeting mid-flight. None of it has a
     caller any more. The h1 and the lede keep their own 300ms fade, declared
     in style.css and owing nothing to this file, which is what they fall back
     to in every other case as well.

     Everything below the field is unchanged: pull the top edge and the web
     spins, exactly as far as the page is open. */
})();
