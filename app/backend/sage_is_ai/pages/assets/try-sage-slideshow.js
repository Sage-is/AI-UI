// The welcome page's background cycler — the SlideShow.svelte behavior,
// without the framework. One slide carries `on`; every five seconds it
// passes to the next. CSS owns the crossfade. Without JavaScript the first
// slide simply stays, which is a complete page, not a degraded one.
(function () {
	var slides = document.querySelectorAll('[data-slide]');
	if (slides.length < 2) return;
	var idx = 0;
	setInterval(function () {
		slides[idx].classList.remove('on');
		idx = (idx + 1) % slides.length;
		slides[idx].classList.add('on');
	}, 5000);
})();
