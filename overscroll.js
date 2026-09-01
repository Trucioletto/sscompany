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
     reader has stopped. The class goes on at the first scroll event and comes
     off 420ms after the last — long enough to sit out a flick and its momentum,
     short enough that letting go brings it back without a wait. */
  var cueDoc = document.documentElement;
  var cueIdle = 0;

  function syncCue() {
    cueDoc.classList.toggle('has-more',
      cueDoc.scrollHeight - window.innerHeight > 240);
    cueDoc.classList.toggle('at-top', window.scrollY < 24);
  }

  function markScrolling() {
    cueDoc.classList.add('scrolling');
    window.clearTimeout(cueIdle);
    cueIdle = window.setTimeout(function () {
      cueDoc.classList.remove('scrolling');
    }, 420);
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
    body.style.transform = 'translate3d(0,' + y.toFixed(2) + 'px,0)';
    var p = Math.min(1, y / MAX / FULL_AT);
    /* The same progress said twice, because CSS cannot divide a time by a time.
       --pull-t scrubs the laying of each thread; --pull-p moves the front that
       decides WHERE the web has been spun so far. */
    doc.style.setProperty('--pull-t', (p * BUILD_MS).toFixed(1) + 'ms');
    doc.style.setProperty('--pull-p', p.toFixed(3));
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
    body.style.transform = '';
    doc.style.removeProperty('--pull-t');
    doc.style.removeProperty('--pull-p');
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


  /* THE WEB SPINS ITSELF ONCE, ON ARRIVAL.

     The edge gesture was the only thing that ever drew the web, so almost
     nobody learned it was there: nothing on the page suggests the top edge
     gives. This spins it once, so the affordance has been shown rather than
     hidden, and then puts it away.

     It reuses the gesture's own path rather than adding a second one. Every
     animation in the stylesheet is paused and reads --pull-t; writing that from
     a clock produces exactly the frames a pull produces, in the same order,
     with no new keyframes and no second definition of what a half-spun web
     looks like.

     IT HAS TO OPEN THE PAGE, AND THAT WAS THE FIRST VERSION'S MISTAKE.
     This was written once without the translate, on the reasoning that an
     arrival which shoves the first paragraph down and pulls it back is a jolt
     dressed as an intention. Then it was rendered: the field is at top:-96px,
     entirely above the viewport, so with the body left alone there is nothing
     on screen to see. The web is only ever visible in the space the pull opens.
     So it opens it — 26px against the gesture's 64, which is enough to show the
     weave's lower band and little enough to read as a breath. It is a transform
     on the body, on the compositor, so nothing reflows and no layout shifts.

     TO is 0.72, not 1: the whole picture stays something the reader gets by
     pulling. An introduction that gives away all of what it introduces leaves
     nothing behind it.

     ONCE PER VISIT, NOT ONCE PER PAGE. A flourish on every internal click stops
     being a greeting and becomes a tic. The test is the referrer — the same one
     lang.js uses — with one correction that cost a render to find: lang.js
     redirects with location.replace(), so a reader who lands on /about/ and is
     sent to /it/about/ arrives with a SAME-ORIGIN referrer and looked, to the
     first version of this test, exactly like somebody clicking a link. Compared
     with the language prefix stripped from both, that redirect reads as what it
     is: still an arrival. Nothing is stored to decide this — the privacy notice
     says no storage and it stays true.

     A real gesture during it wins immediately: the frame loop checks whether the
     pull path has taken ownership and gets out of its way. */
  var GREET_IN = 1100, GREET_HOLD = 320, GREET_OUT = 780;
  var GREET_TO = 1, GREET_PX = 42;

  /* Smoothstep, not a cubic ease-out.

     The ease-out put 58% of the build into the first quarter of the opening —
     205ms of the 820 — so the mesh did not draw, it flashed, and then the
     remaining three quarters crawled through what was left. Smoothstep is
     nearly linear through the middle with soft ends, which is what a line being
     drawn wants: a start you can see begin and a finish you can see land.

     And TO is 1 rather than 0.72. At 0.72 the scrub stopped at 504ms of the
     stylesheet's 700ms timeline, so the last two groups never finished — the
     greeting always showed a half-built mesh and then took it away again. The
     whole picture stays worth pulling for because the pull opens 96px against
     this 42; the drawing is not the part to hold back. */
  function smooth(x) { return x * x * (3 - 2 * x); }

  /* The path with a leading /xx/ language segment removed, so the same page in
     two languages compares equal. */
  function bare(pathname) {
    /* Matched by shape rather than against the list of fifteen codes: that list
       lives in build.py and lang.js, and a third copy here would be the one
       that goes stale. No real path segment on this site is two letters, so the
       shape is unambiguous in practice. */
    var seg = pathname.split('/')[1] || '';
    return /^[a-z]{2}(-[A-Za-z]+)?$/.test(seg) ? pathname.slice(seg.length + 1) : pathname;
  }

  function arrivedFromInsideTheSite() {
    var r = document.referrer;
    if (!r || r.indexOf(location.origin + '/') !== 0) return false;
    var from;
    try { from = new URL(r).pathname; } catch (e) { return false; }
    /* Same page, different language prefix: that is lang.js, not a reader. */
    return bare(from) !== bare(location.pathname);
  }

  /* The greeting owns nothing permanently. Everything it writes, it writes
     through here, and cleanup is idempotent and guaranteed by three separate
     paths: the end of the run, a gesture taking over, and a deadline.

     The first version had one exit — `if (raw || release) return` — which left
     the transform, both custom properties and the class exactly where they
     were. Any stray wheel tick during the 1.7 seconds killed the loop and the
     page stayed pushed down with the field half open, permanently, until a
     reload. It shipped, and it is the reason this is now three paths instead
     of one clever check. */
  var greeting = 0;
  var greetDeadline = 0;

  function greetEnd() {
    if (!greeting) return;
    greeting = 0;
    window.clearTimeout(greetDeadline);
    greetDeadline = 0;
    /* Only ever removes what the greeting itself set. If a real gesture has
       taken over, its own paint() writes these again on the very next frame,
       so the worst case is one frame of rest — not a page left ajar. */
    body.style.transform = '';
    doc.style.removeProperty('--pull-t');
    doc.style.removeProperty('--pull-p');
    doc.classList.remove('is-pulling');
  }

  function greet() {
    /* Not at the top — a restored scroll position, or a link to an anchor. The
       field is not on screen and there is nothing to introduce. */
    if (window.scrollY > 0) return;
    if (arrivedFromInsideTheSite()) return;
    /* A gesture is already live: the reader found the edge on their own and is
       doing the thing this exists to demonstrate. */
    if (raw || release) return;

    var t0 = 0;
    var span = GREET_IN + GREET_HOLD + GREET_OUT;
    greeting = 1;

    /* Third path. requestAnimationFrame does not run in a background tab, and a
       frame callback that never fires cannot clean up after itself — the same
       reason settle() carries a rescue timer. */
    greetDeadline = window.setTimeout(greetEnd, span + 600);

    window.requestAnimationFrame(function step(now) {
      if (!greeting) return;
      /* The reader is pulling: hand over, and take our own writes with us. */
      if (raw || release) { greetEnd(); return; }

      if (!t0) t0 = now;
      var e = now - t0, p;

      if (e < GREET_IN) {
        p = smooth(e / GREET_IN);
      } else if (e < GREET_IN + GREET_HOLD) {
        p = 1;
      } else if (e < span) {
        /* Back through the same frames at the same pace: the mesh unbuilds
           rather than being taken away. */
        p = 1 - smooth((e - GREET_IN - GREET_HOLD) / GREET_OUT);
      } else {
        greetEnd();
        return;
      }

      body.style.transform = 'translate3d(0,' + (p * GREET_PX).toFixed(2) + 'px,0)';
      var t = p * GREET_TO;
      doc.style.setProperty('--pull-t', (t * BUILD_MS).toFixed(1) + 'ms');
      doc.style.setProperty('--pull-p', t.toFixed(3));
      doc.classList.add('is-pulling');
      window.requestAnimationFrame(step);
    });
  }

  /* After the first paint and after the fonts have had their moment: the web
     arriving in the same frame as the wordmark makes both look like a loader. */
  if (document.readyState === 'complete') window.setTimeout(greet, 260);
  else window.addEventListener('load', function () { window.setTimeout(greet, 260); });
})();
