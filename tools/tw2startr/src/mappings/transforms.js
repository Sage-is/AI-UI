import { resolveArbitrary, resolveSpacing } from '../utils/css-value-resolver.js';

/**
 * Transform & transition mapping rules for tw2startr converter.
 *
 * startr.style custom properties used:
 *   --t          transform
 *   --to         transform-origin
 *   --translate  transform: translate()
 *   --translatex transform: translateX()
 *   --translatey transform: translateY()
 *   --scale      transform: scale()
 *   --rotate     transform: rotate()
 *   --skew       transform: skew()
 *   --tn         transition
 *   --tdn        transition-duration
 *   --tp         transition-property
 *   --ttf        transition-timing-function
 *
 * Transition-delay uses the plain CSS property `transition-delay` to avoid
 * conflict with --td which startr.style maps to text-decoration.
 */

// ── Transition shorthand defaults ───────────────────────────────────────
const TRANSITION_DEFAULTS = {
	DEFAULT: 'color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)',
	none: 'none',
	all: 'all 150ms cubic-bezier(0.4, 0, 0.2, 1)',
	colors: 'color, background-color, border-color, text-decoration-color, fill, stroke 150ms cubic-bezier(0.4, 0, 0.2, 1)',
	opacity: 'opacity 150ms cubic-bezier(0.4, 0, 0.2, 1)',
	shadow: 'box-shadow 150ms cubic-bezier(0.4, 0, 0.2, 1)',
	transform: 'transform 150ms cubic-bezier(0.4, 0, 0.2, 1)',
};

const transformRules = [

	// ═══════════════════════════════════════════════════════════════════════
	//  TRANSFORMS
	// ═══════════════════════════════════════════════════════════════════════

	// ── Scale ────────────────────────────────────────────────────────────
	// Matches: scale-50, scale-100, scale-x-75, scale-y-110, scale-[1.5]
	// Values divided by 100: scale-50 → 0.5, scale-150 → 1.5
	// Axis variants use --t (plain transform) because startr.style has
	// --scale but not --scalex / --scaley.
	{
		pattern: /^scale(?:-([xy]))?-(.+)$/,
		convert: (match) => {
			const axis = match[1];
			const val = match[2];
			const arb = resolveArbitrary(val);
			const resolved = arb || (!isNaN(parseInt(val)) ? String(parseInt(val) / 100) : null);
			if (!resolved) return null;
			if (!axis) return { prop: '--scale', value: resolved };
			if (axis === 'x') return { prop: '--t', value: `scaleX(${resolved})` };
			if (axis === 'y') return { prop: '--t', value: `scaleY(${resolved})` };
			return null;
		}
	},

	// ── Rotate ───────────────────────────────────────────────────────────
	// Matches: rotate-45, rotate-90, -rotate-12, rotate-[30deg]
	// Negative prefix arrives as part of the class string.
	{
		pattern: /^(-?)rotate-(.+)$/,
		convert: (match) => {
			const neg = match[1];
			const val = match[2];
			const arb = resolveArbitrary(val);
			if (arb) return { prop: '--rotate', value: `${neg}${arb}` };
			const num = parseInt(val);
			if (!isNaN(num)) return { prop: '--rotate', value: `${neg}${num}deg` };
			return null;
		}
	},

	// ── Translate ────────────────────────────────────────────────────────
	// Matches: translate-x-4, translate-y-8, -translate-x-1/2,
	//          translate-x-full, translate-y-[50vh]
	// Fractions: 1/2 → 50%, 1/3 → 33.333333%, etc.
	// "full" keyword → 100%.
	{
		pattern: /^(-?)translate-([xy])-(.+)$/,
		convert: (match) => {
			const neg = match[1];
			const axis = match[2];
			const val = match[3];
			const prop = axis === 'x' ? '--translatex' : '--translatey';

			// Arbitrary value
			const arb = resolveArbitrary(val);
			if (arb) return { prop, value: `${neg}${arb}` };

			// "full" keyword
			if (val === 'full') return { prop, value: `${neg}100%` };

			// Fraction: 1/2, 2/3, etc.
			const fracMatch = val.match(/^(\d+)\/(\d+)$/);
			if (fracMatch) {
				const pct = (parseInt(fracMatch[1]) / parseInt(fracMatch[2]) * 100);
				return { prop, value: `${neg}${pct.toFixed(6).replace(/\.?0+$/, '')}%` };
			}

			// Spacing scale
			const spacing = resolveSpacing(val);
			if (spacing) return { prop, value: neg ? `-${spacing}` : spacing };

			return null;
		}
	},

	// ── Skew ─────────────────────────────────────────────────────────────
	// Matches: skew-x-3, skew-y-12, -skew-x-6, skew-x-[17deg]
	// startr.style has --skew; we embed the axis function inside it.
	{
		pattern: /^(-?)skew-([xy])-(.+)$/,
		convert: (match) => {
			const neg = match[1];
			const axis = match[2];
			const val = match[3];
			const arb = resolveArbitrary(val);
			const degrees = arb || (!isNaN(parseInt(val)) ? `${val}deg` : null);
			if (!degrees) return null;
			const fn = axis === 'x' ? 'skewX' : 'skewY';
			return { prop: '--skew', value: `${fn}(${neg}${degrees})` };
		}
	},

	// ── Transform Origin ─────────────────────────────────────────────────
	// Matches: origin-center, origin-top-right, origin-bottom-left,
	//          origin-[33%_75%]
	// Compound keywords: hyphens become spaces (top-right → top right).
	{
		pattern: /^origin-(.+)$/,
		convert: (match) => {
			const val = match[1];
			const arb = resolveArbitrary(val);
			if (arb) return { prop: '--to', value: arb };
			return { prop: '--to', value: val.replace(/-/g, ' ') };
		}
	},

	// ═══════════════════════════════════════════════════════════════════════
	//  TRANSITIONS
	// ═══════════════════════════════════════════════════════════════════════

	// ── Transition Property ──────────────────────────────────────────────
	// Matches: transition, transition-none, transition-all,
	//          transition-colors, transition-opacity, transition-shadow,
	//          transition-transform
	{
		pattern: /^transition(?:-(none|all|colors|opacity|shadow|transform))?$/,
		convert: (match) => {
			const val = match[1] || 'DEFAULT';
			const resolved = TRANSITION_DEFAULTS[val];
			return resolved ? { prop: '--tn', value: resolved } : null;
		}
	},

	// ── Duration ─────────────────────────────────────────────────────────
	// Matches: duration-150, duration-300, duration-[400ms]
	{
		pattern: /^duration-(.+)$/,
		convert: (match) => {
			const val = match[1];
			const arb = resolveArbitrary(val);
			if (arb) return { prop: '--tdn', value: arb };
			const num = parseInt(val);
			if (!isNaN(num)) return { prop: '--tdn', value: `${num}ms` };
			return null;
		}
	},

	// ── Timing Function (Ease) ───────────────────────────────────────────
	// Matches: ease-linear, ease-in, ease-out, ease-in-out,
	//          ease-[cubic-bezier(0.1,0.7,1,0.1)]
	// Note: "in-out" must be listed before "in" and "out" in the
	// alternation so that the greedy engine matches correctly.
	{
		pattern: /^ease-(linear|in-out|in|out|\[.+\])$/,
		convert: (match) => {
			const val = match[1];
			const arb = resolveArbitrary(val);
			if (arb) return { prop: '--ttf', value: arb };
			const map = {
				linear: 'linear',
				in: 'cubic-bezier(0.4, 0, 1, 1)',
				out: 'cubic-bezier(0, 0, 0.2, 1)',
				'in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
			};
			return map[val] ? { prop: '--ttf', value: map[val] } : null;
		}
	},

	// ── Delay ────────────────────────────────────────────────────────────
	// Matches: delay-150, delay-300, delay-[400ms]
	// Uses plain CSS `transition-delay` to avoid conflict with --td
	// (which startr.style maps to text-decoration).
	{
		pattern: /^delay-(.+)$/,
		convert: (match) => {
			const val = match[1];
			const arb = resolveArbitrary(val);
			if (arb) return { prop: 'transition-delay', value: arb };
			const num = parseInt(val);
			if (!isNaN(num)) return { prop: 'transition-delay', value: `${num}ms` };
			return null;
		}
	},

	// ═══════════════════════════════════════════════════════════════════════
	//  ANIMATION
	// ═══════════════════════════════════════════════════════════════════════

	// ── Animate ──────────────────────────────────────────────────────────
	// Matches: animate-none, animate-spin, animate-ping, animate-pulse,
	//          animate-bounce, animate-[wiggle_1s_ease-in-out_infinite]
	// Named animations require corresponding @keyframes definitions.
	{
		pattern: /^animate-(none|spin|ping|pulse|bounce|\[.+\])$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'none') return { prop: 'animation', value: 'none' };
			const arb = resolveArbitrary(val);
			if (arb) return { prop: 'animation', value: arb };
			const animations = {
				spin: 'spin 1s linear infinite',
				ping: 'ping 1s cubic-bezier(0, 0, 0.2, 1) infinite',
				pulse: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
				bounce: 'bounce 1s infinite',
			};
			return { prop: 'animation', value: animations[val], review: `animate-${val} requires @keyframes definition` };
		}
	},

	// ═══════════════════════════════════════════════════════════════════════
	//  BACKFACE VISIBILITY
	// ═══════════════════════════════════════════════════════════════════════

	// ── Backface Visible / Hidden ────────────────────────────────────────
	// Matches: backface-visible, backface-hidden
	{
		pattern: /^backface-(visible|hidden)$/,
		convert: (match) => {
			return { prop: 'backface-visibility', value: match[1] };
		}
	},

	// ═══════════════════════════════════════════════════════════════════════
	//  PERSPECTIVE
	// ═══════════════════════════════════════════════════════════════════════

	// ── Perspective ──────────────────────────────────────────────────────
	// Matches: perspective-none, perspective-[800px]
	{
		pattern: /^perspective-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'none') return { prop: 'perspective', value: 'none' };
			const arb = resolveArbitrary(val);
			if (arb) return { prop: 'perspective', value: arb };
			return { prop: 'perspective', value: val };
		}
	},

];

export default transformRules;
