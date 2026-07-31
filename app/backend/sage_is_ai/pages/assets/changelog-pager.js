// Page through the changelog with the Continue button.
//
// The release notes are long: tens of thousands of words on a mature install,
// and a Continue button that advances on the first click means most readers
// never see past the first screen. So while there is more below, the button
// pages down. When the end is reached it moves to the other side of the row and
// becomes the advance action. The move is the signal: the same control now does
// something different, and a fast second click cannot skip the notes by
// accident, because the button is no longer under the cursor.
//
// Progressive enhancement, deliberately. Without this file the button is a
// plain submit that records the read and moves on, and the server renders it in
// its end position with its end label, so no-JS and pre-hydration both get a
// working control rather than one that lies about what it will do.
//
// A file rather than inline handlers because the diagnostics page tells
// operators to set a Content-Security-Policy, and an inline handler is the
// first thing a CSP breaks.
(function () {
	var BODY = '[data-cy="changelog-body"]';
	var BUTTON = '[data-cy="changelog-continue"]';
	var ROW = '[data-pager-row]';
	// Leave a sliver of the previous screen on each page, so a sentence split
	// across the boundary is still recoverable without scrolling back.
	var OVERLAP = 40;

	function atEnd(el) {
		// Sub-pixel scroll heights round inconsistently across browsers and zoom
		// levels, so "within 2px" rather than an equality that never quite holds.
		return el.scrollTop + el.clientHeight >= el.scrollHeight - 2;
	}

	function sync() {
		var body = document.querySelector(BODY);
		var button = document.querySelector(BUTTON);
		var row = document.querySelector(ROW);
		if (!body || !button || !row) return;
		var done = atEnd(body);
		// One attribute. pages.css does the moving with `margin-left: auto`, so
		// there is nothing here to measure and nothing to compute wrong. The
		// previous version measured the row and drove a transform, and moved
		// nothing in a real browser while passing headless.
		row.setAttribute('data-at-end', done ? 'true' : 'false');
		button.textContent = done
			? button.getAttribute('data-label-end')
			: button.getAttribute('data-label-more');
	}

	document.addEventListener('click', function (event) {
		var button = event.target.closest && event.target.closest(BUTTON);
		if (!button) return;
		var body = document.querySelector(BODY);
		// At the end, do nothing and let the form submit. Not preventing the
		// default here is the whole advance path.
		if (!body || atEnd(body)) return;
		event.preventDefault();
		// Smooth, unless the reader has asked for less motion. Checked at click
		// time rather than cached at load, so changing the OS setting takes
		// effect without a reload.
		var still =
			window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		var step = Math.max(body.clientHeight - OVERLAP, 80);
		if (body.scrollBy) {
			body.scrollBy({ top: step, behavior: still ? 'auto' : 'smooth' });
		} else {
			body.scrollTop += step;
		}
		// The scroll listener below syncs as the animation runs, which is what
		// keeps the label honest mid-glide. This call covers the reduced-motion
		// path, where there is no animation to listen to.
		sync();
	});

	// `scroll` does not bubble, so listen in the capture phase. Keeps the button
	// honest when the reader scrolls the notes themselves rather than paging.
	document.addEventListener(
		'scroll',
		function (event) {
			var target = event.target;
			if (target && target.matches && target.matches(BODY)) sync();
		},
		true
	);

	// The dialog host injects a panel without a page load, so there is no second
	// DOMContentLoaded to hang the first sync on. Everything else here is
	// delegated from `document` and survives the swap by itself; only the
	// starting label and side have to be recomputed, and this is that signal.
	document.addEventListener('pages:panel', sync);

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', sync);
	} else {
		sync();
	}
})();
