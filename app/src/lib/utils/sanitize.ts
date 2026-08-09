import DOMPurify from 'dompurify';

// hyperscript's three attribute forms — `_`, `script`, `data-script` — are
// interpreted and CSP-invisible, so any that survive sanitization would run once
// hyperscript is loaded. `data-script` even survives DOMPurify's default
// ALLOW_DATA_ATTR. Strip all three from EVERY sanitize call via one global hook, so no call site (present or future) can leak them — DRY and unforgettable.
// Defense-in-depth: hyperscript isn't loaded yet, but the no-build strangler migration adopts it for author-controlled surfaces (see the plan's Content security note), and user content must never carry these attributes.
const HYPERSCRIPT_ATTRS = new Set(['_', 'script', 'data-script']);

let installed = false;

/**
 * Install the app-wide DOMPurify hook that drops hyperscript attribute forms.
 * Idempotent; call once, early, before any content is sanitized.
 */
export function configureSanitizer(): void {
	if (installed) return;
	installed = true;

	DOMPurify.addHook('uponSanitizeAttribute', (_node, data) => {
		if (HYPERSCRIPT_ATTRS.has(data.attrName)) {
			data.keepAttr = false;
		}
	});
}
