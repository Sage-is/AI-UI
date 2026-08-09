// Correct the time-of-day greeting to the READER's clock.
//
// The server renders one because it must — a page with no greeting until script
// runs would flash. But the server has no idea what time it is where the reader
// is, so an instance in UTC greets someone in the Azores with the wrong half of
// the day. This re-reads the hour locally and swaps the word.
//
// PROGRESSIVE ENHANCEMENT, and cheaply so. The three candidate words are
// rendered into data attributes by the server, already translated, so this file
// holds no copy and no locale logic. With script off, or if this never loads,
// the reader sees the server's guess — a real greeting, just occasionally the
// wrong one. It can never produce an empty or untranslated string, because
// every value it can write came from the markup.
//
// The same boundaries the wider no-build convention keeps: sentences belong in
// the backend, and the browser is never made to carry what the server knows.
(function () {
	var el = document.querySelector('[data-cy="home-greeting-word"]');
	if (!el) return;

	var hour = new Date().getHours();
	var word = el.dataset[hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening'];

	// Only ever swap one of the three the server supplied. A missing attribute
	// leaves the rendered word alone rather than blanking the line.
	if (word) el.textContent = word;
})();
