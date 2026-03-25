import { resolveColor, resolveArbitrary } from '../utils/css-value-resolver.js';

/**
 * Color mapping rules for tw2startr converter.
 * Handles: bg-* (colors), text-* (colors), border-* (colors), divide-* (colors),
 * ring-*, outline-* (colors), accent-*, caret-*, fill-*, stroke-* (colors),
 * placeholder-* (colors), decoration-*, gradient directions, gradient stops.
 */
const colorRules = [

	// ── Background Color ────────────────────────────────────────────────
	{
		pattern: /^bg-(.+)$/,
		convert: (match) => {
			const val = match[1];
			// Skip non-color bg utilities (handled elsewhere or in effects)
			const nonColorPrefixes = ['gradient', 'linear', 'none', 'cover', 'contain', 'center', 'top', 'bottom', 'left', 'right', 'repeat', 'no-repeat', 'fixed', 'local', 'scroll', 'clip', 'origin'];
			if (nonColorPrefixes.some(p => val === p || val.startsWith(p + '-'))) return null;
			const color = resolveColor(val);
			if (!color) return null;
			return { prop: '--bgc', value: color };
		}
	},

	// ── Text Color ──────────────────────────────────────────────────────
	// IMPORTANT: text-{value} can be font-size OR color. Typography.js handles
	// named sizes (xs, sm, base, lg, xl, 2xl..9xl), alignment (left, center,
	// right, justify, start, end), wrap/nowrap/balance/pretty, and ellipsis/clip.
	// This module handles the color case only.
	{
		pattern: /^text-(.+)$/,
		convert: (match) => {
			const val = match[1];
			// Skip non-color text utilities (handled by typography.js)
			const nonColor = ['xs', 'sm', 'base', 'lg', 'xl', '2xl', '3xl', '4xl', '5xl', '6xl', '7xl', '8xl', '9xl', 'left', 'center', 'right', 'justify', 'start', 'end', 'wrap', 'nowrap', 'balance', 'pretty', 'ellipsis', 'clip'];
			if (nonColor.includes(val)) return null;
			const color = resolveColor(val);
			if (!color) return null;
			return { prop: '--c', value: color };
		}
	},

	// ── Border Color ────────────────────────────────────────────────────
	{
		pattern: /^border-(.+)$/,
		convert: (match) => {
			const val = match[1];
			// Skip non-color border utilities (handled by borders.js)
			const nonColor = ['0', '2', '4', '8', 'DEFAULT', 'solid', 'dashed', 'dotted', 'double', 'hidden', 'none', 'collapse', 'separate', 'spacing', 't', 'r', 'b', 'l', 'x', 'y'];
			// Also skip if it looks like border width: border-{number}
			if (nonColor.includes(val) || /^\d+$/.test(val)) return null;
			// Skip directional borders (border-t-*, border-b-*, etc.) - they start with single letters followed by dash
			if (/^[trblxy]-/.test(val)) {
				// This could be border-t-gray-500 (directional color) - extract the color part
				const dirMatch = val.match(/^([trblxy])-(.+)$/);
				if (dirMatch) {
					const color = resolveColor(dirMatch[2]);
					if (color) {
						// No startr.style property for directional border color, use plain CSS
						const dirMap = { t: 'border-top-color', r: 'border-right-color', b: 'border-bottom-color', l: 'border-left-color', x: 'border-inline-color', y: 'border-block-color' };
						return { prop: dirMap[dirMatch[1]] || '--bc', value: color };
					}
				}
				return null;
			}
			const color = resolveColor(val);
			if (!color) return null;
			return { prop: '--bc', value: color };
		}
	},

	// ── Divide Color ────────────────────────────────────────────────────
	{
		pattern: /^divide-(.+)$/,
		convert: (match) => {
			const val = match[1];
			// Skip non-color divide utilities
			if (['x', 'y', 'reverse', 'solid', 'dashed', 'dotted', 'double', 'none'].includes(val) || /^[xy]-/.test(val) || /^\d+$/.test(val)) return null;
			const color = resolveColor(val);
			if (!color) return null;
			return { prop: 'border-color', value: color };
		}
	},

	// ── Ring Color ───────────────────────────────────────────────────────
	{
		pattern: /^ring-(.+)$/,
		convert: (match) => {
			const val = match[1];
			// Skip ring width values
			if (['0', '1', '2', '4', '8', 'DEFAULT', 'inset'].includes(val) || /^\d+$/.test(val)) return null;
			const color = resolveColor(val);
			if (!color) return null;
			// Ring doesn't have a startr.style equiv, use box-shadow color approach
			return { prop: '--ring-color', value: color, review: 'ring-color has no direct startr.style equivalent' };
		}
	},

	// ── Outline Color ───────────────────────────────────────────────────
	{
		pattern: /^outline-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (['none', 'dashed', 'dotted', 'double', '0', '1', '2', '4', '8', 'offset', 'hidden'].includes(val) || /^offset-/.test(val) || /^\d+$/.test(val)) return null;
			const color = resolveColor(val);
			if (!color) return null;
			return { prop: 'outline-color', value: color };
		}
	},

	// ── Accent Color ────────────────────────────────────────────────────
	{
		pattern: /^accent-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'auto') return { prop: 'accent-color', value: 'auto' };
			const color = resolveColor(val);
			if (!color) return null;
			return { prop: 'accent-color', value: color };
		}
	},

	// ── Caret Color ─────────────────────────────────────────────────────
	{
		pattern: /^caret-(.+)$/,
		convert: (match) => {
			const val = match[1];
			const color = resolveColor(val);
			if (!color) return null;
			return { prop: 'caret-color', value: color };
		}
	},

	// ── Fill ────────────────────────────────────────────────────────────
	{
		pattern: /^fill-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'none') return { prop: 'fill', value: 'none' };
			const color = resolveColor(val);
			if (!color) return null;
			return { prop: 'fill', value: color };
		}
	},

	// ── Stroke Color (not width) ────────────────────────────────────────
	{
		pattern: /^stroke-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'none') return { prop: 'stroke', value: 'none' };
			// Skip stroke width values (0, 1, 2)
			if (/^\d+$/.test(val)) return null;
			const color = resolveColor(val);
			if (!color) return null;
			return { prop: 'stroke', value: color };
		}
	},

	// ── Text Decoration Color ───────────────────────────────────────────
	{
		pattern: /^decoration-(.+)$/,
		convert: (match) => {
			const val = match[1];
			// Skip decoration style/thickness values
			if (['solid', 'double', 'dotted', 'dashed', 'wavy', 'auto', 'from-font', '0', '1', '2', '4', '8'].includes(val) || /^\d+$/.test(val)) return null;
			const color = resolveColor(val);
			if (!color) return null;
			return { prop: 'text-decoration-color', value: color };
		}
	},

	// ── Background Gradient Direction ───────────────────────────────────
	{
		pattern: /^bg-linear-to-(t|tr|r|br|b|bl|l|tl)$/,
		convert: (match) => {
			const dirMap = { t: '0deg', tr: '45deg', r: '90deg', br: '135deg', b: '180deg', bl: '225deg', l: '270deg', tl: '315deg' };
			return { prop: '--bgi', value: `linear-gradient(${dirMap[match[1]]}, var(--tw-gradient-stops))`, review: 'gradient needs from-*/via-*/to-* color stops set manually' };
		}
	},

	// ── Gradient Color Stops ────────────────────────────────────────────
	{
		pattern: /^from-(.+)$/,
		convert: (match) => {
			const color = resolveColor(match[1]);
			if (!color) return null;
			return { prop: '--tw-gradient-from', value: color, review: 'gradient stop - verify gradient setup' };
		}
	},
	{
		pattern: /^via-(.+)$/,
		convert: (match) => {
			const color = resolveColor(match[1]);
			if (!color) return null;
			return { prop: '--tw-gradient-via', value: color, review: 'gradient stop - verify gradient setup' };
		}
	},
	{
		pattern: /^to-(.+)$/,
		convert: (match) => {
			const color = resolveColor(match[1]);
			if (!color) return null;
			return { prop: '--tw-gradient-to', value: color, review: 'gradient stop - verify gradient setup' };
		}
	},

];

export default colorRules;
