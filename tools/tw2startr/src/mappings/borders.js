import { resolveSpacing, resolveArbitrary } from '../utils/css-value-resolver.js';
import { BORDER_RADIUS, SHADOWS } from '../utils/tailwind-values.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Resolve a border-radius token to its CSS value.
 */
function resolveRadius(val) {
	if (!val || val === 'DEFAULT') return BORDER_RADIUS['DEFAULT'];
	if (BORDER_RADIUS[val]) return BORDER_RADIUS[val];
	const arb = resolveArbitrary(val);
	if (arb) return arb;
	return null;
}

/**
 * Map from Tailwind shadow names to startr.style numeric levels.
 */
const SHADOW_MAP = { sm: '1', DEFAULT: '2', md: '3', lg: '4', xl: '5', '2xl': '6', none: '0' };

// ---------------------------------------------------------------------------
// Direction maps (reused across several rules)
// ---------------------------------------------------------------------------

const BORDER_DIR_PROPS = {
	t: 'border-top-width',
	r: 'border-right-width',
	b: 'border-bottom-width',
	l: 'border-left-width'
};

const RADIUS_DIR_MAP = {
	t:  ['--btlr', '--btrr'],
	b:  ['--bblr', '--bbrr'],
	l:  ['--btlr', '--bblr'],
	r:  ['--btrr', '--bbrr'],
	tl: ['--btlr'],
	tr: ['--btrr'],
	bl: ['--bblr'],
	br: ['--bbrr']
};

// ---------------------------------------------------------------------------
// Rules
// ---------------------------------------------------------------------------

const borderRules = [

	// ── Border Width (standalone) ───────────────────────────────────────
	// `border` alone → shorthand 1px solid
	{
		pattern: /^border$/,
		convert: () => ({ prop: '--b', value: '1px solid' })
	},

	// ── Border Width (numeric / arbitrary) ──────────────────────────────
	// border-0, border-2, border-4, border-8, border-[3px]
	{
		pattern: /^border-([0248]|\[.+\])$/,
		convert: (match) => {
			const val = match[1];
			if (val.startsWith('[')) {
				const arb = resolveArbitrary(val);
				return arb ? { prop: '--bw', value: arb } : null;
			}
			return { prop: '--bw', value: val === '0' ? '0' : `${val}px` };
		}
	},

	// ── Directional Border Width ────────────────────────────────────────
	// border-t, border-t-0, border-t-2, border-r-[5px], border-x, border-y
	{
		pattern: /^border-([trblxy])(?:-([0248]|\[.+\]))?$/,
		convert: (match) => {
			const dir = match[1];
			const val = match[2];

			let width;
			if (!val) {
				// e.g. `border-t` → 1px solid
				width = '1px';
			} else if (val.startsWith('[')) {
				const arb = resolveArbitrary(val);
				if (!arb) return null;
				width = arb;
			} else {
				width = val === '0' ? '0' : `${val}px`;
			}

			// Axis shortcuts
			if (dir === 'x') {
				return [
					{ prop: 'border-left-width', value: width },
					{ prop: 'border-right-width', value: width }
				];
			}
			if (dir === 'y') {
				return [
					{ prop: 'border-top-width', value: width },
					{ prop: 'border-bottom-width', value: width }
				];
			}

			// Standalone directional (no value) gets shorthand
			if (!val) {
				const shorthandMap = { t: '--bt', r: '--br', b: '--bb', l: '--bl' };
				return { prop: shorthandMap[dir], value: '1px solid' };
			}

			return { prop: BORDER_DIR_PROPS[dir], value: width };
		}
	},

	// ── Border Style ────────────────────────────────────────────────────
	{
		pattern: /^border-(solid|dashed|dotted|double|hidden|none)$/,
		convert: (match) => ({ prop: '--bs', value: match[1] })
	},

	// ── Border Radius (standalone) ──────────────────────────────────────
	{
		pattern: /^rounded$/,
		convert: () => ({ prop: '--radius', value: BORDER_RADIUS['DEFAULT'] })
	},

	// ── Border Radius (named / arbitrary) ───────────────────────────────
	{
		pattern: /^rounded-(none|sm|md|lg|xl|2xl|3xl|full|button|\[.+\])$/,
		convert: (match) => {
			const val = resolveRadius(match[1]);
			return val ? { prop: '--radius', value: val } : null;
		}
	},

	// ── Border Radius (directional side) ────────────────────────────────
	// rounded-t-md, rounded-b-lg, rounded-l-none, rounded-r-full, etc.
	{
		pattern: /^rounded-([trbl])(?:-(none|sm|md|lg|xl|2xl|3xl|full|button|\[.+\]))?$/,
		convert: (match) => {
			const dir = match[1];
			const sizeToken = match[2] || 'DEFAULT';
			const val = resolveRadius(sizeToken);
			if (!val) return null;
			const props = RADIUS_DIR_MAP[dir];
			return props.map(prop => ({ prop, value: val }));
		}
	},

	// ── Border Radius (corner-specific) ─────────────────────────────────
	// rounded-tl-md, rounded-tr-lg, rounded-bl-none, rounded-br-full, etc.
	{
		pattern: /^rounded-(tl|tr|bl|br)(?:-(none|sm|md|lg|xl|2xl|3xl|full|button|\[.+\]))?$/,
		convert: (match) => {
			const corner = match[1];
			const sizeToken = match[2] || 'DEFAULT';
			const val = resolveRadius(sizeToken);
			if (!val) return null;
			const props = RADIUS_DIR_MAP[corner];
			return props.map(prop => ({ prop, value: val }));
		}
	},

	// ── Box Shadow ──────────────────────────────────────────────────────
	{
		pattern: /^shadow(?:-(sm|md|lg|xl|2xl|none|inner|\[.+\]))?$/,
		convert: (match) => {
			const val = match[1];
			// Just "shadow" → DEFAULT level 2
			if (!val) return { prop: '--shadow', value: '2' };
			if (val === 'inner') return { prop: '--shadow-inset', value: '2' };
			if (val.startsWith('[')) {
				const arb = resolveArbitrary(val);
				return arb ? { prop: '--boxs', value: arb } : null;
			}
			if (SHADOW_MAP[val] !== undefined) return { prop: '--shadow', value: SHADOW_MAP[val] };
			return null;
		}
	},

	// ── Outline Style ───────────────────────────────────────────────────
	{
		pattern: /^outline$/,
		convert: () => ({ prop: 'outline-style', value: 'solid' })
	},
	{
		pattern: /^outline-(dashed|dotted|double)$/,
		convert: (match) => ({ prop: 'outline-style', value: match[1] })
	},
	{
		pattern: /^outline-none$/,
		convert: () => ({ prop: '--oe', value: '2px solid transparent' })
	},
	{
		pattern: /^outline-hidden$/,
		convert: () => ({ prop: '--oe', value: 'none' })
	},

	// ── Outline Width ───────────────────────────────────────────────────
	{
		pattern: /^outline-([01248])$/,
		convert: (match) => {
			const val = match[1];
			return { prop: 'outline-width', value: val === '0' ? '0' : `${val}px` };
		}
	},

	// ── Outline Offset ──────────────────────────────────────────────────
	{
		pattern: /^outline-offset-(-?\d+|\[.+\])$/,
		convert: (match) => {
			const val = match[1];
			if (val.startsWith('[')) {
				const arb = resolveArbitrary(val);
				return arb ? { prop: 'outline-offset', value: arb } : null;
			}
			return { prop: 'outline-offset', value: `${val}px` };
		}
	},

	// ── Ring ────────────────────────────────────────────────────────────
	// Approximate conversion: ring to box-shadow with review flag
	{
		pattern: /^ring(?:-(0|1|2|4|8|\[.+\]))?$/,
		convert: (match) => {
			const val = match[1];
			const width = val
				? (val.startsWith('[') ? resolveArbitrary(val) : `${val}px`)
				: '3px';
			if (!width) return null;
			return {
				prop: 'box-shadow',
				value: `0 0 0 ${width} var(--tw-ring-color, rgb(59 130 246 / 0.5))`,
				review: 'ring converted to box-shadow; may need manual adjustment'
			};
		}
	},

	// ── Ring Inset ──────────────────────────────────────────────────────
	{
		pattern: /^ring-inset$/,
		convert: () => ({
			prop: '--tw-ring-inset',
			value: 'inset',
			review: 'ring-inset sets shadow inset flag; verify box-shadow usage'
		})
	},

	// ── Divide Width ────────────────────────────────────────────────────
	// divide-x, divide-y, divide-x-2, divide-y-[3px]
	{
		pattern: /^divide-([xy])(?:-(\d+|\[.+\]))?$/,
		convert: (match) => {
			const axis = match[1];
			const val = match[2];
			let width;
			if (!val) {
				width = '1px';
			} else if (val.startsWith('[')) {
				const arb = resolveArbitrary(val);
				if (!arb) return null;
				width = arb;
			} else {
				width = val === '0' ? '0' : `${val}px`;
			}
			const prop = axis === 'x' ? 'border-left-width' : 'border-top-width';
			return { prop, value: width, review: `divide-${axis} uses > * + * combinator; consider using gap instead` };
		}
	},

	// ── Divide Reverse ──────────────────────────────────────────────────
	{
		pattern: /^divide-([xy])-reverse$/,
		convert: (match) => ({
			prop: `--tw-divide-${match[1]}-reverse`,
			value: '1',
			review: 'divide-reverse requires special combinator handling'
		})
	},

	// ── Divide Style ────────────────────────────────────────────────────
	{
		pattern: /^divide-(solid|dashed|dotted|double|none)$/,
		convert: (match) => ({
			prop: 'border-style',
			value: match[1],
			review: 'divide-style uses > * + * combinator; apply border-style to children manually'
		})
	},

];

export default borderRules;
