// The welcome page's two rotations — SlideShow.svelte's background crossfade
// and Marquee.svelte's heading words — without the framework. One element in
// each group carries `on`; every five seconds it passes to the next, and CSS
// owns the transitions. Without JavaScript the first of each simply stays,
// which is a complete page, not a degraded one.
(function () {
	function cycle(selector) {
		var items = document.querySelectorAll(selector);
		if (items.length < 2) return;
		var idx = 0;
		setInterval(function () {
			items[idx].classList.remove('on');
			idx = (idx + 1) % items.length;
			items[idx].classList.add('on');
		}, 5000);
	}
	cycle('[data-slide]');
	cycle('[data-marquee-item]');
})();
