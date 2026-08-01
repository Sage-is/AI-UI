// Development only. Reloads the page when the server comes back, and swaps the
// stylesheet in place when an asset changes.
//
// This file is served ONLY when PAGES_RELOAD_DIRS is set — `shell.py` decides,
// and the route it talks to is not registered at all otherwise. A production
// page never sees it.
//
// THE PYTHON HALF NEEDS NO FILE WATCHER. Uvicorn's reloader restarts the whole
// process when a `.py` file under the watched directories changes. That kills
// every open connection, including this one, and `EventSource` reconnects by
// itself — three seconds by default, per the HTML spec. So the restart IS the
// signal: a reconnect means the server went away and came back, which means the
// code changed. Nothing here watches anything.
//
// The FIRST open is skipped, because that one is just this page loading.
//
// THE ASSET HALF DOES need a watcher, and the server has it: `pages/assets/*`
// is served straight from disk by a StaticFiles mount, so changing a stylesheet
// restarts nothing and there is no dropped connection to notice. The server
// pushes an `assets` event instead, and this re-stamps the stylesheet href
// rather than reloading — so you can restyle a panel without losing your scroll
// position or closing the dialog you are looking at.
//
// A file rather than an inline handler, for the same reason changelog-pager.js
// is one: the diagnostics page tells operators to set a Content-Security-Policy
// and inline handlers are the first thing that breaks.
(function () {
	var SOURCE = '/pages/_dev/reload';
	var seenOpen = false;

	function restamp() {
		var links = document.querySelectorAll('link[rel="stylesheet"]');
		for (var i = 0; i < links.length; i++) {
			var link = links[i];
			var url;
			try {
				url = new URL(link.href, location.href);
			} catch (e) {
				continue;
			}
			// Same origin only. The framework stylesheet is loaded from
			// startr.style, and re-fetching a third-party CDN on every local
			// save would be rude and slow, and cannot have changed anyway.
			if (url.origin !== location.origin) continue;
			url.searchParams.set('_dev', String(Date.now()));
			link.href = url.toString();
		}
	}

	var source = new EventSource(SOURCE);

	source.addEventListener('open', function () {
		if (!seenOpen) {
			seenOpen = true;
			return;
		}
		location.reload();
	});

	source.addEventListener('assets', function () {
		restamp();
	});

	// Markup is the third case and it needs a reload, not a swap.
	//
	// A template edit restarts nothing — Jinja re-reads the file on the next
	// request — so there is no dropped connection to notice and no stylesheet to
	// re-stamp. The page has to ask for itself again. That costs the scroll
	// position, which is the honest trade: you cannot change the shape of a
	// document in place the way you can change its colour.
	source.addEventListener('markup', function () {
		location.reload();
	});
})();
