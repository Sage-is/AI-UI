/*!
 * Startr Swap — swap links and forms in place, with no build step.
 *
 * Drop it in, mark a region, and same-origin links stop reloading the page:
 *
 *   <script defer src="swap.js"></script>
 *   <main data-swap> … </main>
 *
 * Lineage: htmz (MIT, (c) Lean Rada), whose hash-names-the-target convention this
 * keeps. The hidden iframe does not survive: an iframe performs a REAL
 * navigation, so scripts in the response execute inside it — in the wrong
 * document, silently — and every swap re-requests the page's stylesheets.
 * `fetch` + `DOMParser` parses inert, and reports a redirect honestly.
 *
 * MARKUP
 *   data-swap          on a region   mark it swappable. A value narrows which
 *                                    links are taken over to a path prefix, and
 *                                    nested regions inherit it.
 *   data-swap-target   on a control  update THAT region, by selector, instead of
 *                                    the one this control lives in.
 *   data-swap-off      on a control  never swap this one.
 *
 * EVENTS — on the region, bubbling, cancelable.
 *   swap:before    cancel to abandon the swap; the browser navigates normally
 *   swap:navigate  cancel to own the address bar yourself
 *   swap:after     content is in
 *   swap:error     cancel to suppress the fallback navigation
 *
 * NOTHING HERE KNOWS WHAT APPLICATION IT IS IN. Every host-specific concern
 * leaves through an attribute value or an event listener. If that stops being
 * true this file has stopped being publishable.
 *
 * No [data-swap] in the document: it does nothing at all and every link
 * navigates. That is the correct answer, not a degraded one — see `region`.
 */
(function () {
	var html = document.documentElement;
	// Two copies would bind two delegated listeners and swap everything twice.
	if (html.hasAttribute('data-swap-installed')) return;
	html.setAttribute('data-swap-installed', '');

	// Did WE push a history entry? If a host cancelled `swap:navigate` it owns
	// the address bar, so it owns `popstate` too and we must keep our hands off.
	var owned = false;
	var loaded = null;

	// ── Finding the region ──────────────────────────────────────────────────

	function root() {
		return document.querySelector('[data-swap]');
	}

	/**
	 * The region a control updates: what it names, else the one it lives in.
	 *
	 * `closest` is what makes sub-swaps free — a pager inside a region updates
	 * that region and leaves the rest of the page alone, declaring nothing.
	 * `data-swap-target` covers only what `closest` cannot reach: a control that
	 * lives OUTSIDE the region it updates, a search form above its own results.
	 *
	 * THERE IS NO FALLBACK TO <main>, and that is a decision rather than an
	 * omission. A one-word opt-in costs an author nothing and buys the property
	 * that matters: this file governs only what it was handed. Any document can
	 * end up running it — a host application that adopts a fetched page's
	 * scripts adopts this one too — and a version that claimed `<main>` by
	 * default would then take over every link in a document that never asked
	 * for it. That failure is silent and total.
	 */
	function region(el) {
		var named = el.getAttribute('data-swap-target');
		if (named) return document.querySelector(named);
		return el.closest('[data-swap]');
	}

	/**
	 * How to find this region again in the response.
	 *
	 * An id names one element in a document, so it is the only reliable answer
	 * for a sub-swap — which is the whole reason a sub-swap region needs one.
	 */
	function selectorFor(dest) {
		return dest.id ? '#' + CSS.escape(dest.id) : '[data-swap]';
	}

	/** The nearest prefix at or above this region. Empty regions inherit. */
	function scopeFor(dest) {
		for (var el = dest; el; el = el.parentElement) {
			var v = el.getAttribute && el.getAttribute('data-swap');
			if (v) return v;
		}
		return '';
	}

	function inScope(url, prefix) {
		if (url.origin !== location.origin) return false;
		return prefix ? url.pathname.indexOf(prefix) === 0 : true;
	}

	// ── Swapping ────────────────────────────────────────────────────────────

	function fire(el, name, detail) {
		return el.dispatchEvent(
			new CustomEvent(name, { detail: detail, bubbles: true, cancelable: true })
		);
	}

	function hardNav(url) {
		location.assign(url);
	}

	function transition(run) {
		var still =
			window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		if (still || !document.startViewTransition) return run();
		document.startViewTransition(run);
	}

	/**
	 * Run the scripts the response declared.
	 *
	 * A <script> that arrives through DOMParser NEVER executes — the spec says
	 * so, and there is no error. Re-creating the element is the only way.
	 *
	 * The set is seeded from what the document already has, which is what stops
	 * this file from adding a second copy of ITSELF on the first swap.
	 */
	function adoptScripts(doc) {
		if (!loaded) {
			loaded = {};
			Array.prototype.forEach.call(document.querySelectorAll('script[src]'), function (s) {
				loaded[s.src] = true;
			});
		}
		Array.prototype.forEach.call(doc.querySelectorAll('script[src]'), function (s) {
			var src = new URL(s.getAttribute('src'), location.href).href;
			if (loaded[src]) return;
			loaded[src] = true;
			var el = document.createElement('script');
			el.src = src;
			el.defer = true;
			document.head.appendChild(el);
		});
	}

	/**
	 * Upgrade a server-rendered confirmation into a real modal.
	 *
	 * Everything here is an UPGRADE: with this removed the dialog is still open,
	 * still centred by the browser, and both its controls still work.
	 */
	function raiseDialog(scope) {
		var d = scope.querySelector('dialog[open]');
		if (!d || !d.showModal || d.matches(':modal')) return;
		d.close(); // showModal() on an already-open dialog throws InvalidStateError
		d.showModal();
		// Escape fires `cancel`. Left alone the dialog would vanish while the
		// server still considers the row pending, so the picture and the state
		// would disagree and the next render would contradict what was just seen.
		d.addEventListener('cancel', function (e) {
			if (!d.dataset.cancel) return;
			e.preventDefault();
			location.href = d.dataset.cancel;
		});
	}

	function go(url, dest, body, push) {
		var sel = selectorFor(dest);
		var scope = scopeFor(dest);
		if (!fire(dest, 'swap:before', { url: url })) return;

		var init = { credentials: 'same-origin' };
		if (body) {
			init.method = 'POST';
			init.body = body;
		}

		fetch(url, init)
			.then(function (res) {
				// res.url is the FINAL url. Landing outside scope means the server
				// sent us somewhere else — a signed-out reader to a sign-in page.
				// That is an instruction to follow, not content to render, and it
				// is checked BEFORE the status because the redirect target answers
				// a perfectly good 200.
				var landed = new URL(res.url, location.href);
				if (!inScope(landed, scope)) {
					hardNav(landed.href);
					return null;
				}
				if (!res.ok) throw new Error(res.status + ' ' + res.statusText);
				// Not every address in scope answers with a page. A download does
				// not, and re-requesting it is what makes it download.
				if (!/text\/html/i.test(res.headers.get('content-type') || '')) {
					hardNav(url);
					return null;
				}
				return res.text().then(function (text) {
					return { text: text, url: landed.href, redirected: res.redirected };
				});
			})
			.then(function (got) {
				if (!got) return;
				var doc = new DOMParser().parseFromString(got.text, 'text/html');
				var next = doc.querySelector(sel);
				if (!next) throw new Error('no ' + sel + ' in the response');

				transition(function () {
					// Snapshot before moving: childNodes is LIVE, and moving out of
					// it while iterating skips every second node. Silent — you get
					// half a region and no error.
					dest.replaceChildren.apply(dest, Array.prototype.slice.call(next.childNodes));
					// Only a swap of the document's own main content changed the
					// page, so only that changes the title. A sub-swap did not.
					// Neither did a region hosted inside somebody else's page —
					// there the surrounding application owns the title, and taking
					// it would make the tab flicker between two brandings.
					if (dest === document.querySelector('main')) document.title = doc.title;
					raiseDialog(dest);
					// A POST that REDIRECTED is Post/Redirect/Get: it finished
					// somewhere else, and that somewhere is a plain address the
					// reader can reload and share, so it belongs in history. A POST
					// that answered in place does not — its address only accepts
					// POST, and putting it in history hands the reader a reload that
					// 405s.
					//
					// Getting this wrong is quiet in the worst way. The content
					// swaps to the page you asked for while the address stays on the
					// one you left, so every link and form on screen now belongs to
					// a document the address bar disagrees with.
					if ((push || got.redirected) && fire(dest, 'swap:navigate', { url: got.url })) {
						history.pushState(null, '', got.url);
						owned = true;
					}
				});
				adoptScripts(doc);
				fire(dest, 'swap:after', { url: got.url });
			})
			.catch(function (err) {
				// A swap that fails must never leave a dead page: fall back to what
				// the browser would have done without this script at all.
				if (fire(dest, 'swap:error', { url: url, error: err })) hardNav(url);
			});
	}

	// ── Taking over ─────────────────────────────────────────────────────────
	//
	// Delegated on the document, which is why there is no re-enhancement step.
	// Per-element wiring goes stale the moment a swap replaces the elements, and
	// the page then quietly falls back to full reloads — working, no longer
	// smooth, and nobody files it.

	document.addEventListener('click', function (e) {
		if (e.defaultPrevented || e.button !== 0) return;
		if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
		var a = e.target && e.target.closest && e.target.closest('a[href]');
		if (!a || a.hasAttribute('data-swap-off') || a.target || a.hasAttribute('download')) return;

		var dest = region(a);
		if (!dest) return;
		var url = new URL(a.href, location.href);
		if (!inScope(url, scopeFor(dest))) return;
		// A link to a place on THIS page is a jump, not a navigation. Swapping it
		// would refetch the page, replace the content and leave the reader exactly
		// where they were, having destroyed the thing they were aiming at.
		if (url.href.split('#')[0] === location.href.split('#')[0]) return;

		e.preventDefault();
		go(url.href, dest, null, true);
		// CAPTURE, and this is the difference between working and not.
		//
		// A single-page router binds its own document-level click listener when the
		// application boots — long before this file is loaded, and certainly before
		// it is loaded by being adopted from a fetched page. Listeners on the same
		// node fire in registration order, so in the bubble phase the router always
		// wins: it takes the click, finds the address is not one of its routes, and
		// falls back to a full page navigation. The region never sees it.
		//
		// Capture puts a declared region ahead of a generic router, which is the
		// right precedence — an author who wrote `data-swap` on an element said
		// what should happen to links inside it. Nothing is claimed that a region
		// does not match, and every early return above happens BEFORE
		// `preventDefault`, so a link this file declines is still the router's.
	}, true);

	// Bubble, deliberately, unlike the click above. Nothing here competes for
	// submits at the document level, while attribute-driven libraries bind them on
	// the FORM — and an element listener runs after a document capture. Capturing
	// would take their submits away from them.
	document.addEventListener('submit', function (e) {
		if (e.defaultPrevented) return;
		var f = e.target;
		if (f.hasAttribute('data-swap-off')) return;
		// A file upload is a multipart body this cannot rebuild from a URL, and
		// there is nothing to gain from intercepting it.
		if (f.enctype === 'multipart/form-data') return;

		var dest = region(f);
		if (!dest) return;
		var submitter = e.submitter;
		var action = (submitter && submitter.getAttribute('formaction')) || f.getAttribute('action');
		var url = new URL(action || location.href, location.href);
		if (!inScope(url, scopeFor(dest))) return;

		var data;
		try {
			data = new FormData(f, submitter);
		} catch (err) {
			data = new FormData(f); // older browsers ignore the submitter
		}
		var post = (f.method || 'get').toLowerCase() === 'post';
		if (!post) {
			url.search = new URLSearchParams(data).toString();
		}

		e.preventDefault();
		// A GET result is an address worth keeping. A POST result is not one you
		// can hand to anybody, so it does not go in the history.
		go(url.href, dest, post ? data : null, !post);
	});

	window.addEventListener('popstate', function () {
		if (!owned) return;
		var dest = root();
		// The ROOT, not whichever region was swapped last: a root swap replaces
		// the sub-regions inside it too, so it is always the right answer and
		// never needs a record of what happened.
		if (!dest || !inScope(new URL(location.href), scopeFor(dest))) return;
		go(location.href, dest, null, false);
	});
})();
