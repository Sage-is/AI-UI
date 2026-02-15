import { resolveSpacing, resolveArbitrary, resolveFraction } from '../utils/css-value-resolver.js';

// ---------------------------------------------------------------------------
// Named value maps
// ---------------------------------------------------------------------------

const NAMED_WIDTHS = {
	auto: 'auto',
	full: '100%',
	screen: '100vw',
	svw: '100svw',
	dvw: '100dvw',
	min: 'min-content',
	max: 'max-content',
	fit: 'fit-content'
};

const NAMED_HEIGHTS = {
	auto: 'auto',
	full: '100%',
	screen: '100vh',
	svh: '100svh',
	dvh: '100dvh',
	min: 'min-content',
	max: 'max-content',
	fit: 'fit-content'
};

const NAMED_MIN_WIDTHS = {
	'0': '0',
	full: '100%',
	min: 'min-content',
	max: 'max-content',
	fit: 'fit-content'
};

const NAMED_MAX_WIDTHS = {
	xs: '20rem',
	sm: '24rem',
	md: '28rem',
	lg: '32rem',
	xl: '36rem',
	'2xl': '42rem',
	'3xl': '48rem',
	'4xl': '56rem',
	'5xl': '64rem',
	'6xl': '72rem',
	'7xl': '80rem',
	full: '100%',
	none: 'none',
	prose: '65ch',
	'screen-sm': '640px',
	'screen-md': '768px',
	'screen-lg': '1024px',
	'screen-xl': '1280px',
	'screen-2xl': '1536px'
};

const NAMED_MIN_HEIGHTS = {
	'0': '0',
	full: '100%',
	screen: '100vh',
	svh: '100svh',
	dvh: '100dvh',
	min: 'min-content',
	max: 'max-content',
	fit: 'fit-content'
};

const NAMED_MAX_HEIGHTS = {
	none: 'none',
	full: '100%',
	screen: '100vh'
};

// ---------------------------------------------------------------------------
// Shared resolver: named map -> fraction -> spacing (includes arbitrary)
// ---------------------------------------------------------------------------

function resolveSizingValue(val, namedMap) {
	if (namedMap[val]) return namedMap[val];
	const fraction = resolveFraction(val);
	if (fraction) return fraction;
	const spacing = resolveSpacing(val);
	if (spacing) return spacing;
	return null;
}

// ---------------------------------------------------------------------------
// Rules
// ---------------------------------------------------------------------------

const sizingRules = [
	// ---- Width ----
	{
		pattern: /^w-(.+)$/,
		convert: (match) => {
			const resolved = resolveSizingValue(match[1], NAMED_WIDTHS);
			return resolved ? { prop: '--w', value: resolved } : null;
		}
	},

	// ---- Height ----
	{
		pattern: /^h-(.+)$/,
		convert: (match) => {
			const resolved = resolveSizingValue(match[1], NAMED_HEIGHTS);
			return resolved ? { prop: '--h', value: resolved } : null;
		}
	},

	// ---- Size (width + height shorthand) ----
	{
		pattern: /^size-(.+)$/,
		convert: (match) => {
			const resolved = resolveSizingValue(match[1], NAMED_WIDTHS);
			return resolved
				? [{ prop: '--w', value: resolved }, { prop: '--h', value: resolved }]
				: null;
		}
	},

	// ---- Min-Width ----
	{
		pattern: /^min-w-(.+)$/,
		convert: (match) => {
			const resolved = resolveSizingValue(match[1], NAMED_MIN_WIDTHS);
			return resolved ? { prop: '--minw', value: resolved } : null;
		}
	},

	// ---- Max-Width ----
	{
		pattern: /^max-w-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (NAMED_MAX_WIDTHS[val]) return { prop: '--maxw', value: NAMED_MAX_WIDTHS[val] };
			const spacing = resolveSpacing(val);
			if (spacing) return { prop: '--maxw', value: spacing };
			return null;
		}
	},

	// ---- Min-Height ----
	{
		pattern: /^min-h-(.+)$/,
		convert: (match) => {
			const resolved = resolveSizingValue(match[1], NAMED_MIN_HEIGHTS);
			return resolved ? { prop: '--minh', value: resolved } : null;
		}
	},

	// ---- Max-Height ----
	{
		pattern: /^max-h-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (NAMED_MAX_HEIGHTS[val]) return { prop: '--maxh', value: NAMED_MAX_HEIGHTS[val] };
			const spacing = resolveSpacing(val);
			if (spacing) return { prop: '--maxh', value: spacing };
			return null;
		}
	}
];

export default sizingRules;
