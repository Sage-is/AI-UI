import { resolveSpacing, resolveArbitrary } from '../utils/css-value-resolver.js';

/**
 * Spacing mapping rules for tw2startr converter.
 * Handles: padding (p, px, py, pt, pr, pb, pl) and
 *          margin  (m, mx, my, mt, mr, mb, ml), including negatives.
 * Also handles space-x / space-y (converted to gap with review flag).
 */
const spacingRules = [

	// ── Padding ──────────────────────────────────────────────────────────
	// Matches: p-4, px-2, py-[1.5rem], pt-0, pr-auto(?), pb-px, pl-0.5
	// Negative padding is not standard in Tailwind, but handle the prefix
	// gracefully just in case (e.g. from a custom config).
	{
		pattern: /^(-?)p([xytrbl]?)-(.+)$/,
		convert: (match) => {
			const [, neg, dir, val] = match;
			const dirMap = { '': '', 'x': 'x', 'y': 'y', 't': 't', 'r': 'r', 'b': 'b', 'l': 'l' };
			const resolved = resolveSpacing(val);
			if (!resolved) return null;
			return { prop: `--p${dirMap[dir]}`, value: neg ? `-${resolved}` : resolved };
		}
	},

	// ── Margin ───────────────────────────────────────────────────────────
	// Matches: m-4, mx-auto, -mt-4, my-[2rem], mb-0, ml-px
	// Negative margin: the full class arrives as e.g. "-mt-4", so the
	// leading `-` is captured by the first group.
	{
		pattern: /^(-?)m([xytrbl]?)-(.+)$/,
		convert: (match) => {
			const [, neg, dir, val] = match;
			const dirMap = { '': '', 'x': 'x', 'y': 'y', 't': 't', 'r': 'r', 'b': 'b', 'l': 'l' };
			if (val === 'auto') return { prop: `--m${dirMap[dir]}`, value: 'auto' };
			const resolved = resolveSpacing(val);
			if (!resolved) return null;
			return { prop: `--m${dirMap[dir]}`, value: neg ? `-${resolved}` : resolved };
		}
	},

	// ── Space Between (X) ────────────────────────────────────────────────
	// space-x-{value} uses the > * + * combinator in Tailwind, which has
	// no direct equivalent in startr.style. Convert to gap as best-effort.
	{
		pattern: /^space-x-reverse$/,
		convert: () => null
	},
	{
		pattern: /^space-x-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			if (!resolved) return null;
			return { prop: '--g', value: resolved, review: 'space-x uses > * + * combinator; converted to gap' };
		}
	},

	// ── Space Between (Y) ────────────────────────────────────────────────
	{
		pattern: /^space-y-reverse$/,
		convert: () => null
	},
	{
		pattern: /^space-y-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			if (!resolved) return null;
			return { prop: '--g', value: resolved, review: 'space-y uses > * + * combinator; converted to gap' };
		}
	},

];

export default spacingRules;
