// Keep a colour picker and its hex field in step.
//
// This is the only script these pages ship beyond htmx, and it exists because
// the pair genuinely cannot work without one. `<input type="color">` has no way
// to express "unset" — it submits #000000 when nobody has touched it — and unset
// is meaningful on this surface, since an empty colour means "use the theme's
// own". So the text field is what submits and this mirrors the two.
//
// It is a file rather than two `oninput` attributes on purpose: the diagnostics
// page tells operators to set a Content-Security-Policy, and inline handlers are
// the first thing a CSP stops. Shipping markup that breaks when an operator
// follows our own advice is not a trade worth ten characters.
//
// Delegated from the document, so it survives htmx swapping the panel out from
// under it — a save replaces the whole form, and listeners bound to the old
// inputs would go with it.
(function () {
	var linked = function (el) {
		if (!el || !el.dataset) return null;
		if (el.dataset.syncs) return document.getElementById(el.dataset.syncs);
		// The hex field's partner is the picker that names it.
		if (el.id) return document.querySelector('input[type="color"][data-syncs="' + el.id + '"]');
		return null;
	};

	document.addEventListener('input', function (ev) {
		var el = ev.target;
		if (!el || el.tagName !== 'INPUT') return;
		var other = linked(el);
		if (!other) return;

		if (el.type === 'color') {
			other.value = el.value;
			return;
		}
		// Typing into the hex field: only move the picker once the text is a
		// colour it can hold. Assigning an invalid value silently resets a
		// colour input to #000000, which would fight the operator mid-word.
		if (/^#[0-9a-fA-F]{6}$/.test(el.value)) other.value = el.value;
	});
})();
