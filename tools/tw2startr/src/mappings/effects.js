import { resolveSpacing, resolveArbitrary } from '../utils/css-value-resolver.js';

// ---------------------------------------------------------------------------
// Local value maps
// ---------------------------------------------------------------------------

const BLUR_MAP = {
	none: '0', sm: '4px', DEFAULT: '8px', md: '12px',
	lg: '16px', xl: '24px', '2xl': '40px', '3xl': '64px'
};

const DROP_SHADOW_MAP = {
	sm:      'drop-shadow(0 1px 1px rgb(0 0 0 / 0.05))',
	DEFAULT: 'drop-shadow(0 1px 2px rgb(0 0 0 / 0.1)) drop-shadow(0 1px 1px rgb(0 0 0 / 0.06))',
	md:      'drop-shadow(0 4px 3px rgb(0 0 0 / 0.07)) drop-shadow(0 2px 2px rgb(0 0 0 / 0.06))',
	lg:      'drop-shadow(0 10px 8px rgb(0 0 0 / 0.04)) drop-shadow(0 4px 3px rgb(0 0 0 / 0.1))',
	xl:      'drop-shadow(0 20px 13px rgb(0 0 0 / 0.03)) drop-shadow(0 8px 5px rgb(0 0 0 / 0.08))',
	'2xl':   'drop-shadow(0 25px 25px rgb(0 0 0 / 0.15))',
	none:    'drop-shadow(0 0 #0000)'
};

const COLUMNS_NAMED = {
	'3xs': '16rem', '2xs': '18rem', xs: '20rem', sm: '24rem',
	md: '28rem', lg: '32rem', xl: '36rem', '2xl': '42rem',
	'3xl': '48rem', '4xl': '56rem', '5xl': '64rem', '6xl': '72rem', '7xl': '80rem'
};

// Valid cursor keywords (kept for reference / validation)
// auto, default, pointer, wait, text, move, help, not-allowed, none,
// context-menu, progress, cell, crosshair, vertical-text, alias, copy,
// no-drop, grab, grabbing, all-scroll, col-resize, row-resize,
// n-resize, e-resize, s-resize, w-resize, ne-resize, nw-resize,
// se-resize, sw-resize, ew-resize, ns-resize, nesw-resize, nwse-resize,
// zoom-in, zoom-out

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Resolve a filter percentage value (brightness, contrast, saturate).
 * Input: '75' → '0.75', '150' → '1.5', '[.8]' → '.8'
 */
function resolveFilterPercent(val) {
	if (val.startsWith('[')) return resolveArbitrary(val);
	const num = parseInt(val);
	if (isNaN(num)) return null;
	return String(num / 100);
}

// Scroll margin/padding directions are handled by individual pattern rules below.

// ---------------------------------------------------------------------------
// Rules
// ---------------------------------------------------------------------------

const effectRules = [

	// ── Opacity ─────────────────────────────────────────────────────────
	{
		pattern: /^opacity-(.+)$/,
		convert: (match) => {
			const val = match[1];
			const arb = resolveArbitrary(val);
			if (arb) return { prop: '--op', value: arb };
			const num = parseInt(val);
			if (!isNaN(num)) return { prop: '--op', value: String(num / 100) };
			return null;
		}
	},

	// ── Cursor ──────────────────────────────────────────────────────────
	{
		pattern: /^cursor-(.+)$/,
		convert: (match) => {
			const val = match[1];
			const arb = resolveArbitrary(val);
			if (arb) return { prop: '--cur', value: arb };
			return { prop: '--cur', value: val };
		}
	},

	// ── Pointer Events ──────────────────────────────────────────────────
	{
		pattern: /^pointer-events-(none|auto)$/,
		convert: (match) => ({ prop: '--pe', value: match[1] })
	},

	// ── User Select ─────────────────────────────────────────────────────
	{
		pattern: /^select-(none|text|all|auto)$/,
		convert: (match) => ({ prop: '--us', value: match[1] })
	},

	// ── Object Fit ──────────────────────────────────────────────────────
	{
		pattern: /^object-(contain|cover|fill|none|scale-down)$/,
		convert: (match) => ({ prop: '--objf', value: match[1] })
	},

	// ── Object Position ─────────────────────────────────────────────────
	{
		pattern: /^object-(bottom|center|left|left-bottom|left-top|right|right-bottom|right-top|top)$/,
		convert: (match) => ({
			prop: '--objp',
			value: match[1].replace(/-/g, ' ')
		})
	},

	// ── Overflow ────────────────────────────────────────────────────────
	{
		pattern: /^overflow-(auto|hidden|clip|visible|scroll)$/,
		convert: (match) => ({ prop: '--of', value: match[1] })
	},
	{
		pattern: /^overflow-x-(auto|hidden|clip|visible|scroll)$/,
		convert: (match) => ({ prop: '--ofx', value: match[1] })
	},
	{
		pattern: /^overflow-y-(auto|hidden|clip|visible|scroll)$/,
		convert: (match) => ({ prop: '--ofy', value: match[1] })
	},

	// ── Overscroll ──────────────────────────────────────────────────────
	{
		pattern: /^overscroll-(auto|contain|none)$/,
		convert: (match) => ({ prop: 'overscroll-behavior', value: match[1] })
	},
	{
		pattern: /^overscroll-x-(auto|contain|none)$/,
		convert: (match) => ({ prop: 'overscroll-behavior-x', value: match[1] })
	},
	{
		pattern: /^overscroll-y-(auto|contain|none)$/,
		convert: (match) => ({ prop: 'overscroll-behavior-y', value: match[1] })
	},

	// ── Scroll Behavior ─────────────────────────────────────────────────
	{
		pattern: /^scroll-(auto|smooth)$/,
		convert: (match) => ({ prop: '--sb', value: match[1] })
	},

	// ── Appearance ──────────────────────────────────────────────────────
	{
		pattern: /^appearance-(none|auto)$/,
		convert: (match) => ({ prop: 'appearance', value: match[1] })
	},

	// ── Box Sizing ──────────────────────────────────────────────────────
	{
		pattern: /^box-(border|content)$/,
		convert: (match) => ({
			prop: '--bxs',
			value: `${match[1]}-box`
		})
	},

	// ── Isolation ───────────────────────────────────────────────────────
	{
		pattern: /^isolate$/,
		convert: () => ({ prop: 'isolation', value: 'isolate' })
	},
	{
		pattern: /^isolation-auto$/,
		convert: () => ({ prop: 'isolation', value: 'auto' })
	},

	// ── Mix Blend Mode ──────────────────────────────────────────────────
	{
		pattern: /^mix-blend-(normal|multiply|screen|overlay|darken|lighten|color-dodge|color-burn|hard-light|soft-light|difference|exclusion|hue|saturation|color|luminosity|plus-darker|plus-lighter)$/,
		convert: (match) => ({ prop: 'mix-blend-mode', value: match[1] })
	},

	// ── Background Blend Mode ───────────────────────────────────────────
	{
		pattern: /^bg-blend-(normal|multiply|screen|overlay|darken|lighten|color-dodge|color-burn|hard-light|soft-light|difference|exclusion|hue|saturation|color|luminosity)$/,
		convert: (match) => ({ prop: 'background-blend-mode', value: match[1] })
	},

	// ── Blur (filter) ───────────────────────────────────────────────────
	{
		pattern: /^blur(?:-(none|sm|md|lg|xl|2xl|3xl|\[.+\]))?$/,
		convert: (match) => {
			const val = match[1] || 'DEFAULT';
			if (val.startsWith('[')) {
				const arb = resolveArbitrary(val);
				return arb ? { prop: '--fr', value: `blur(${arb})` } : null;
			}
			const size = BLUR_MAP[val];
			return size != null
				? { prop: '--fr', value: `blur(${size})`, review: 'multiple filters must be combined manually into a single filter property' }
				: null;
		}
	},

	// ── Backdrop Blur ───────────────────────────────────────────────────
	{
		pattern: /^backdrop-blur(?:-(none|sm|md|lg|xl|2xl|3xl|\[.+\]))?$/,
		convert: (match) => {
			const val = match[1] || 'DEFAULT';
			if (val.startsWith('[')) {
				const arb = resolveArbitrary(val);
				return arb ? { prop: 'backdrop-filter', value: `blur(${arb})` } : null;
			}
			const size = BLUR_MAP[val];
			return size != null ? { prop: 'backdrop-filter', value: `blur(${size})` } : null;
		}
	},

	// ── Brightness (filter) ─────────────────────────────────────────────
	{
		pattern: /^brightness-(\d+|\[.+\])$/,
		convert: (match) => {
			const resolved = resolveFilterPercent(match[1]);
			return resolved != null
				? { prop: '--fr', value: `brightness(${resolved})`, review: 'multiple filters must be combined manually into a single filter property' }
				: null;
		}
	},

	// ── Contrast (filter) ───────────────────────────────────────────────
	{
		pattern: /^contrast-(\d+|\[.+\])$/,
		convert: (match) => {
			const resolved = resolveFilterPercent(match[1]);
			return resolved != null
				? { prop: '--fr', value: `contrast(${resolved})`, review: 'multiple filters must be combined manually into a single filter property' }
				: null;
		}
	},

	// ── Grayscale ───────────────────────────────────────────────────────
	{
		pattern: /^grayscale(?:-(0|\[.+\]))?$/,
		convert: (match) => {
			const val = match[1];
			if (!val) return { prop: '--fr', value: 'grayscale(100%)', review: 'multiple filters must be combined manually into a single filter property' };
			if (val === '0') return { prop: '--fr', value: 'grayscale(0)', review: 'multiple filters must be combined manually into a single filter property' };
			const arb = resolveArbitrary(val);
			return arb ? { prop: '--fr', value: `grayscale(${arb})`, review: 'multiple filters must be combined manually into a single filter property' } : null;
		}
	},

	// ── Invert ──────────────────────────────────────────────────────────
	{
		pattern: /^invert(?:-(0|\[.+\]))?$/,
		convert: (match) => {
			const val = match[1];
			if (!val) return { prop: '--fr', value: 'invert(100%)', review: 'multiple filters must be combined manually into a single filter property' };
			if (val === '0') return { prop: '--fr', value: 'invert(0)', review: 'multiple filters must be combined manually into a single filter property' };
			const arb = resolveArbitrary(val);
			return arb ? { prop: '--fr', value: `invert(${arb})`, review: 'multiple filters must be combined manually into a single filter property' } : null;
		}
	},

	// ── Saturate (filter) ───────────────────────────────────────────────
	{
		pattern: /^saturate-(\d+|\[.+\])$/,
		convert: (match) => {
			const resolved = resolveFilterPercent(match[1]);
			return resolved != null
				? { prop: '--fr', value: `saturate(${resolved})`, review: 'multiple filters must be combined manually into a single filter property' }
				: null;
		}
	},

	// ── Sepia ───────────────────────────────────────────────────────────
	{
		pattern: /^sepia(?:-(0|\[.+\]))?$/,
		convert: (match) => {
			const val = match[1];
			if (!val) return { prop: '--fr', value: 'sepia(100%)', review: 'multiple filters must be combined manually into a single filter property' };
			if (val === '0') return { prop: '--fr', value: 'sepia(0)', review: 'multiple filters must be combined manually into a single filter property' };
			const arb = resolveArbitrary(val);
			return arb ? { prop: '--fr', value: `sepia(${arb})`, review: 'multiple filters must be combined manually into a single filter property' } : null;
		}
	},

	// ── Hue Rotate (filter) ─────────────────────────────────────────────
	{
		pattern: /^hue-rotate-(\d+|\[.+\])$/,
		convert: (match) => {
			const val = match[1];
			if (val.startsWith('[')) {
				const arb = resolveArbitrary(val);
				return arb ? { prop: '--fr', value: `hue-rotate(${arb})`, review: 'multiple filters must be combined manually into a single filter property' } : null;
			}
			return { prop: '--fr', value: `hue-rotate(${val}deg)`, review: 'multiple filters must be combined manually into a single filter property' };
		}
	},

	// ── Drop Shadow (filter) ────────────────────────────────────────────
	{
		pattern: /^drop-shadow(?:-(sm|md|lg|xl|2xl|none|\[.+\]))?$/,
		convert: (match) => {
			const val = match[1] || 'DEFAULT';
			if (val.startsWith('[')) {
				const arb = resolveArbitrary(val);
				return arb ? { prop: '--fr', value: `drop-shadow(${arb})`, review: 'multiple filters must be combined manually into a single filter property' } : null;
			}
			const shadow = DROP_SHADOW_MAP[val];
			return shadow != null
				? { prop: '--fr', value: shadow, review: 'multiple filters must be combined manually into a single filter property' }
				: null;
		}
	},

	// ── Will Change ─────────────────────────────────────────────────────
	{
		pattern: /^will-change-(auto|scroll|contents|transform)$/,
		convert: (match) => {
			const map = {
				auto: 'auto',
				scroll: 'scroll-position',
				contents: 'contents',
				transform: 'transform'
			};
			return { prop: 'will-change', value: map[match[1]] };
		}
	},

	// ── Content ─────────────────────────────────────────────────────────
	{
		pattern: /^content-none$/,
		convert: () => ({ prop: '--ct', value: 'none' })
	},

	// ── Break Inside ────────────────────────────────────────────────────
	{
		pattern: /^break-inside-(auto|avoid|avoid-page|avoid-column)$/,
		convert: (match) => ({ prop: '--bi', value: match[1] })
	},

	// ── Columns ─────────────────────────────────────────────────────────
	{
		pattern: /^columns-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'auto') return { prop: '--cc', value: 'auto' };
			// Named sizes
			if (COLUMNS_NAMED[val]) return { prop: '--cc', value: COLUMNS_NAMED[val] };
			// Arbitrary
			const arb = resolveArbitrary(val);
			if (arb) return { prop: '--cc', value: arb };
			// Numeric (1-12)
			if (/^\d+$/.test(val)) return { prop: '--cc', value: val };
			return null;
		}
	},

	// ── Aspect Ratio ────────────────────────────────────────────────────
	{
		pattern: /^aspect-(auto|square|video|\[.+\])$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'auto') return { prop: 'aspect-ratio', value: 'auto' };
			if (val === 'square') return { prop: 'aspect-ratio', value: '1 / 1' };
			if (val === 'video') return { prop: 'aspect-ratio', value: '16 / 9' };
			if (val.startsWith('[')) {
				const arb = resolveArbitrary(val);
				return arb ? { prop: 'aspect-ratio', value: arb.replace(/\//g, ' / ') } : null;
			}
			return null;
		}
	},

	// ── Table Layout ────────────────────────────────────────────────────
	{
		pattern: /^table-(auto|fixed)$/,
		convert: (match) => ({ prop: 'table-layout', value: match[1] })
	},

	// ── Caption Side ────────────────────────────────────────────────────
	{
		pattern: /^caption-(top|bottom)$/,
		convert: (match) => ({ prop: 'caption-side', value: match[1] })
	},

	// ── Border Collapse ─────────────────────────────────────────────────
	{
		pattern: /^border-collapse$/,
		convert: () => ({ prop: 'border-collapse', value: 'collapse' })
	},
	{
		pattern: /^border-separate$/,
		convert: () => ({ prop: 'border-collapse', value: 'separate' })
	},

	// ── Resize ──────────────────────────────────────────────────────────
	{
		pattern: /^resize-none$/,
		convert: () => ({ prop: 'resize', value: 'none' })
	},
	{
		pattern: /^resize-y$/,
		convert: () => ({ prop: 'resize', value: 'vertical' })
	},
	{
		pattern: /^resize-x$/,
		convert: () => ({ prop: 'resize', value: 'horizontal' })
	},
	{
		pattern: /^resize$/,
		convert: () => ({ prop: 'resize', value: 'both' })
	},

	// ── Scroll Snap Type ────────────────────────────────────────────────
	{
		pattern: /^snap-none$/,
		convert: () => ({ prop: 'scroll-snap-type', value: 'none' })
	},
	{
		pattern: /^snap-(x|y|both)$/,
		convert: (match) => ({
			prop: 'scroll-snap-type',
			value: `${match[1]} var(--tw-scroll-snap-strictness, proximity)`
		})
	},
	{
		pattern: /^snap-mandatory$/,
		convert: () => ({
			prop: '--tw-scroll-snap-strictness',
			value: 'mandatory',
			review: 'snap-mandatory sets strictness variable; ensure snap-x/y/both is also set'
		})
	},
	{
		pattern: /^snap-proximity$/,
		convert: () => ({
			prop: '--tw-scroll-snap-strictness',
			value: 'proximity',
			review: 'snap-proximity sets strictness variable; ensure snap-x/y/both is also set'
		})
	},

	// ── Scroll Snap Align ───────────────────────────────────────────────
	{
		pattern: /^snap-(start|end|center)$/,
		convert: (match) => ({ prop: 'scroll-snap-align', value: match[1] })
	},
	{
		pattern: /^snap-align-none$/,
		convert: () => ({ prop: 'scroll-snap-align', value: 'none' })
	},

	// ── Touch Action ────────────────────────────────────────────────────
	{
		pattern: /^touch-(auto|none|manipulation)$/,
		convert: (match) => ({ prop: 'touch-action', value: match[1] })
	},
	{
		pattern: /^touch-(pan-x|pan-y|pinch-zoom)$/,
		convert: (match) => ({ prop: 'touch-action', value: match[1] })
	},

	// ── Scroll Margin ───────────────────────────────────────────────────
	{
		pattern: /^scroll-m-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			return resolved ? { prop: 'scroll-margin', value: resolved } : null;
		}
	},
	{
		pattern: /^scroll-mx-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			return resolved ? { prop: 'scroll-margin-inline', value: resolved } : null;
		}
	},
	{
		pattern: /^scroll-my-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			return resolved ? { prop: 'scroll-margin-block', value: resolved } : null;
		}
	},
	{
		pattern: /^scroll-mt-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			return resolved ? { prop: 'scroll-margin-top', value: resolved } : null;
		}
	},
	{
		pattern: /^scroll-mr-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			return resolved ? { prop: 'scroll-margin-right', value: resolved } : null;
		}
	},
	{
		pattern: /^scroll-mb-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			return resolved ? { prop: 'scroll-margin-bottom', value: resolved } : null;
		}
	},
	{
		pattern: /^scroll-ml-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			return resolved ? { prop: 'scroll-margin-left', value: resolved } : null;
		}
	},

	// ── Scroll Padding ──────────────────────────────────────────────────
	{
		pattern: /^scroll-p-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			return resolved ? { prop: 'scroll-padding', value: resolved } : null;
		}
	},
	{
		pattern: /^scroll-px-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			return resolved ? { prop: 'scroll-padding-inline', value: resolved } : null;
		}
	},
	{
		pattern: /^scroll-py-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			return resolved ? { prop: 'scroll-padding-block', value: resolved } : null;
		}
	},
	{
		pattern: /^scroll-pt-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			return resolved ? { prop: 'scroll-padding-top', value: resolved } : null;
		}
	},
	{
		pattern: /^scroll-pr-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			return resolved ? { prop: 'scroll-padding-right', value: resolved } : null;
		}
	},
	{
		pattern: /^scroll-pb-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			return resolved ? { prop: 'scroll-padding-bottom', value: resolved } : null;
		}
	},
	{
		pattern: /^scroll-pl-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			return resolved ? { prop: 'scroll-padding-left', value: resolved } : null;
		}
	},

];

export default effectRules;
