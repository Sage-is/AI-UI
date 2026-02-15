import { resolveSpacing, resolveArbitrary } from '../utils/css-value-resolver.js';
import { FONT_SIZES, FONT_WEIGHTS, LINE_HEIGHTS, TRACKING } from '../utils/tailwind-values.js';

// ---------------------------------------------------------------------------
// Font family stacks
// ---------------------------------------------------------------------------

const FONT_FAMILIES = {
	sans: 'ui-sans-serif, system-ui, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"',
	serif: 'ui-serif, Georgia, Cambria, "Times New Roman", Times, serif',
	mono: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace'
};

// ---------------------------------------------------------------------------
// Rules
// ---------------------------------------------------------------------------

const typographyRules = [
	// ---- Font Size (named sizes only; text-{color} is handled in colors.js) ----
	{
		pattern: /^text-(xs|sm|base|lg|xl|2xl|3xl|4xl|5xl|6xl|7xl|8xl|9xl)$/,
		convert: (match) => {
			const size = FONT_SIZES[match[1]];
			return size ? { prop: '--size', value: size } : null;
		}
	},

	// ---- Font Size (arbitrary) ----
	{
		pattern: /^text-(\[.+\])$/,
		convert: (match) => {
			const value = resolveArbitrary(match[1]);
			return value ? { prop: '--size', value } : null;
		}
	},

	// ---- Text Alignment ----
	{
		pattern: /^text-(left|center|right|justify|start|end)$/,
		convert: (match) => ({ prop: '--ta', value: match[1] })
	},

	// ---- Text Wrap ----
	{
		pattern: /^text-(wrap|nowrap|balance|pretty)$/,
		convert: (match) => ({ prop: 'text-wrap', value: match[1] })
	},

	// ---- Font Weight (named) ----
	{
		pattern: /^font-(thin|extralight|light|normal|medium|semibold|bold|extrabold|black)$/,
		convert: (match) => {
			const weight = FONT_WEIGHTS[match[1]];
			return weight ? { prop: '--weight', value: weight } : null;
		}
	},

	// ---- Font Weight (arbitrary) ----
	{
		pattern: /^font-(\[.+\])$/,
		convert: (match) => {
			const value = resolveArbitrary(match[1]);
			return value ? { prop: '--weight', value } : null;
		}
	},

	// ---- Font Family ----
	{
		pattern: /^font-(sans|serif|mono)$/,
		convert: (match) => ({ prop: '--ff', value: FONT_FAMILIES[match[1]] })
	},

	// ---- Font Style ----
	{
		pattern: /^(italic|not-italic)$/,
		convert: (match) => ({
			prop: 'font-style',
			value: match[1] === 'italic' ? 'italic' : 'normal'
		})
	},

	// ---- Text Transform ----
	{
		pattern: /^(uppercase|lowercase|capitalize|normal-case)$/,
		convert: (match) => ({
			prop: '--tt',
			value: match[1] === 'normal-case' ? 'none' : match[1]
		})
	},

	// ---- Text Decoration ----
	{
		pattern: /^(underline|overline|line-through|no-underline)$/,
		convert: (match) => ({
			prop: '--td',
			value: match[1] === 'no-underline' ? 'none' : match[1]
		})
	},

	// ---- Text Overflow: truncate ----
	{
		pattern: /^truncate$/,
		convert: () => [
			{ prop: 'overflow', value: 'hidden' },
			{ prop: 'text-overflow', value: 'ellipsis' },
			{ prop: '--ws', value: 'nowrap' }
		]
	},

	// ---- Text Overflow: ellipsis / clip ----
	{
		pattern: /^text-(ellipsis|clip)$/,
		convert: (match) => ({ prop: 'text-overflow', value: match[1] })
	},

	// ---- Whitespace ----
	{
		pattern: /^whitespace-(normal|nowrap|pre|pre-line|pre-wrap|break-spaces)$/,
		convert: (match) => ({ prop: '--ws', value: match[1] })
	},

	// ---- Word Break ----
	{
		pattern: /^break-(normal|words|all|keep)$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'normal') {
				return [
					{ prop: '--wb', value: 'normal' },
					{ prop: 'overflow-wrap', value: 'normal' }
				];
			}
			if (val === 'words') {
				return [
					{ prop: '--wb', value: 'break-word' },
					{ prop: 'overflow-wrap', value: 'break-word' }
				];
			}
			if (val === 'all') return { prop: '--wb', value: 'break-all' };
			if (val === 'keep') return { prop: '--wb', value: 'keep-all' };
			return null;
		}
	},

	// ---- Line Clamp (numeric 1-6) ----
	{
		pattern: /^line-clamp-([1-6])$/,
		convert: (match) => ({ prop: '--line-clamp', value: match[1] })
	},

	// ---- Line Clamp (arbitrary) ----
	{
		pattern: /^line-clamp-(\[.+\])$/,
		convert: (match) => {
			const value = resolveArbitrary(match[1]);
			return value ? { prop: '--line-clamp', value } : null;
		}
	},

	// ---- Line Clamp none ----
	{
		pattern: /^line-clamp-none$/,
		convert: () => ({ prop: '--line-clamp', value: 'unset' })
	},

	// ---- Line Height (named) ----
	{
		pattern: /^leading-(none|tight|snug|normal|relaxed|loose)$/,
		convert: (match) => {
			const lh = LINE_HEIGHTS[match[1]];
			return lh ? { prop: '--lh', value: lh } : null;
		}
	},

	// ---- Line Height (numeric) ----
	{
		pattern: /^leading-(\d+(?:\.\d+)?)$/,
		convert: (match) => {
			const n = parseFloat(match[1]);
			return { prop: '--lh', value: `${n * 0.25}rem` };
		}
	},

	// ---- Line Height (arbitrary) ----
	{
		pattern: /^leading-(\[.+\])$/,
		convert: (match) => {
			const value = resolveArbitrary(match[1]);
			return value ? { prop: '--lh', value } : null;
		}
	},

	// ---- Letter Spacing (named) ----
	{
		pattern: /^tracking-(tighter|tight|normal|wide|wider|widest)$/,
		convert: (match) => {
			const ls = TRACKING[match[1]];
			return ls ? { prop: '--ls', value: ls } : null;
		}
	},

	// ---- Letter Spacing (arbitrary) ----
	{
		pattern: /^tracking-(\[.+\])$/,
		convert: (match) => {
			const value = resolveArbitrary(match[1]);
			return value ? { prop: '--ls', value } : null;
		}
	},

	// ---- Vertical Align ----
	{
		pattern: /^align-(baseline|top|middle|bottom|text-top|text-bottom|sub|super)$/,
		convert: (match) => ({ prop: '--va', value: match[1] })
	},

	// ---- List Style Type ----
	{
		pattern: /^list-(none|disc|decimal)$/,
		convert: (match) => ({ prop: 'list-style-type', value: match[1] })
	},

	// ---- List Style Position ----
	{
		pattern: /^list-(inside|outside)$/,
		convert: (match) => ({ prop: 'list-style-position', value: match[1] })
	}
];

export default typographyRules;
