import { resolveSpacing, resolveArbitrary, resolveFraction } from '../utils/css-value-resolver.js';

/**
 * Layout mapping rules for tw2startr converter.
 * Handles: display, position, flex, grid, alignment, z-index,
 * positioning (top/right/bottom/left/inset), float, visibility, order, gap.
 */
const layoutRules = [

	// ── Display ──────────────────────────────────────────────────────────
	{
		pattern: /^(inline-flex|inline-block|inline-grid|inline|flex|block|grid|hidden|table-row|table-cell|table|contents|flow-root|list-item)$/,
		convert: (match) => {
			const displayMap = {
				'flex': 'flex',
				'inline-flex': 'inline-flex',
				'block': 'block',
				'inline-block': 'inline-block',
				'inline': 'inline',
				'grid': 'grid',
				'inline-grid': 'inline-grid',
				'hidden': 'none',
				'table': 'table',
				'table-row': 'table-row',
				'table-cell': 'table-cell',
				'contents': 'contents',
				'flow-root': 'flow-root',
				'list-item': 'list-item',
			};
			return { prop: '--d', value: displayMap[match[1]] };
		}
	},

	// ── Position ─────────────────────────────────────────────────────────
	{
		pattern: /^(relative|absolute|fixed|sticky|static)$/,
		convert: (match) => ({ prop: '--pos', value: match[1] })
	},

	// ── Flex Direction ───────────────────────────────────────────────────
	{
		pattern: /^flex-(row-reverse|row|col-reverse|col)$/,
		convert: (match) => {
			const dirMap = {
				'row': 'row',
				'row-reverse': 'row-reverse',
				'col': 'column',
				'col-reverse': 'column-reverse',
			};
			return { prop: '--fd', value: dirMap[match[1]] };
		}
	},

	// ── Flex Wrap ────────────────────────────────────────────────────────
	{
		pattern: /^flex-(wrap-reverse|wrap|nowrap)$/,
		convert: (match) => {
			const wrapMap = {
				'wrap': 'wrap',
				'wrap-reverse': 'wrap-reverse',
				'nowrap': 'nowrap',
			};
			return { prop: '--fw', value: wrapMap[match[1]] };
		}
	},

	// ── Flex Shorthand ───────────────────────────────────────────────────
	{
		pattern: /^flex-(1|auto|initial|none)$/,
		convert: (match) => {
			const flexMap = {
				'1': '1 1 0%',
				'auto': '1 1 auto',
				'initial': '0 1 auto',
				'none': 'none',
			};
			return { prop: '--fx', value: flexMap[match[1]] };
		}
	},

	// ── Flex Grow ────────────────────────────────────────────────────────
	{
		pattern: /^grow(-0)?$/,
		convert: (match) => ({ prop: '--fg', value: match[1] ? '0' : '1' })
	},

	// ── Flex Shrink ──────────────────────────────────────────────────────
	{
		pattern: /^shrink(-0)?$/,
		convert: (match) => ({ prop: '--fs', value: match[1] ? '0' : '1' })
	},

	// ── Flex Basis ───────────────────────────────────────────────────────
	{
		pattern: /^basis-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'auto') return { prop: '--fb', value: 'auto' };
			if (val === 'full') return { prop: '--fb', value: '100%' };
			// Fractions: 1/2 -> 50%
			const frac = resolveFraction(val);
			if (frac) return { prop: '--fb', value: frac };
			// Spacing scale or arbitrary
			const resolved = resolveSpacing(val);
			if (resolved) return { prop: '--fb', value: resolved };
			return null;
		}
	},

	// ── Align Items ──────────────────────────────────────────────────────
	{
		pattern: /^items-(start|end|center|baseline|stretch)$/,
		convert: (match) => {
			const map = {
				'start': 'flex-start',
				'end': 'flex-end',
				'center': 'center',
				'baseline': 'baseline',
				'stretch': 'stretch',
			};
			return { prop: '--ai', value: map[match[1]] };
		}
	},

	// ── Justify Content ──────────────────────────────────────────────────
	{
		pattern: /^justify-(start|end|center|between|around|evenly|normal|stretch)$/,
		convert: (match) => {
			const map = {
				'start': 'flex-start',
				'end': 'flex-end',
				'center': 'center',
				'between': 'space-between',
				'around': 'space-around',
				'evenly': 'space-evenly',
				'normal': 'normal',
				'stretch': 'stretch',
			};
			return { prop: '--jc', value: map[match[1]] };
		}
	},

	// ── Align Self ───────────────────────────────────────────────────────
	{
		pattern: /^self-(auto|start|end|center|stretch|baseline)$/,
		convert: (match) => {
			const map = {
				'auto': 'auto',
				'start': 'flex-start',
				'end': 'flex-end',
				'center': 'center',
				'stretch': 'stretch',
				'baseline': 'baseline',
			};
			return { prop: '--as', value: map[match[1]] };
		}
	},

	// ── Align Content ────────────────────────────────────────────────────
	{
		pattern: /^content-(start|end|center|between|around|evenly|stretch|normal)$/,
		convert: (match) => {
			const map = {
				'start': 'flex-start',
				'end': 'flex-end',
				'center': 'center',
				'between': 'space-between',
				'around': 'space-around',
				'evenly': 'space-evenly',
				'stretch': 'stretch',
				'normal': 'normal',
			};
			return { prop: '--ac', value: map[match[1]] };
		}
	},

	// ── Place Self ───────────────────────────────────────────────────────
	{
		pattern: /^place-self-(auto|start|end|center|stretch)$/,
		convert: (match) => ({ prop: '--ps', value: match[1] })
	},

	// ── Justify Items ────────────────────────────────────────────────────
	{
		pattern: /^justify-items-(start|end|center|stretch)$/,
		convert: (match) => ({ prop: '--ji', value: match[1] })
	},

	// ── Justify Self ─────────────────────────────────────────────────────
	{
		pattern: /^justify-self-(auto|start|end|center|stretch)$/,
		convert: (match) => ({ prop: '--js', value: match[1] })
	},

	// ── Z-Index ──────────────────────────────────────────────────────────
	{
		pattern: /^(-?)z-(.+)$/,
		convert: (match) => {
			const [, neg, val] = match;
			if (val === 'auto') return { prop: '--z', value: 'auto' };
			// Arbitrary value
			const arbitrary = resolveArbitrary(val);
			if (arbitrary) return { prop: '--z', value: neg ? `-${arbitrary}` : arbitrary };
			// Numeric values (0, 10, 20, 30, 40, 50, or any number)
			if (/^\d+$/.test(val)) return { prop: '--z', value: neg ? `-${val}` : val };
			return null;
		}
	},

	// ── Inset / Position Offsets ─────────────────────────────────────────
	{
		pattern: /^(-?)(top|right|bottom|left|inset-x|inset-y|inset)-(.+)$/,
		convert: (match) => {
			const [, neg, dir, val] = match;

			let resolved;
			if (val === 'auto') {
				resolved = 'auto';
			} else if (val === 'full') {
				resolved = '100%';
			} else {
				// Fractions
				const frac = resolveFraction(val);
				if (frac) {
					resolved = frac;
				} else {
					resolved = resolveSpacing(val);
				}
			}

			if (!resolved) return null;

			const finalValue = neg ? `-${resolved}` : resolved;

			const propMap = {
				'top': '--top',
				'right': '--right',
				'bottom': '--bottom',
				'left': '--left',
				'inset': '--inset',
			};

			if (dir === 'inset-x') {
				return [
					{ prop: '--left', value: finalValue },
					{ prop: '--right', value: finalValue },
				];
			}
			if (dir === 'inset-y') {
				return [
					{ prop: '--top', value: finalValue },
					{ prop: '--bottom', value: finalValue },
				];
			}

			return { prop: propMap[dir], value: finalValue };
		}
	},

	// ── Float ────────────────────────────────────────────────────────────
	{
		pattern: /^float-(left|right|none|start|end)$/,
		convert: (match) => {
			const map = {
				'left': 'left',
				'right': 'right',
				'none': 'none',
				'start': 'inline-start',
				'end': 'inline-end',
			};
			return { prop: '--ft', value: map[match[1]] };
		}
	},

	// ── Visibility ───────────────────────────────────────────────────────
	{
		pattern: /^(visible|invisible|collapse)$/,
		convert: (match) => {
			const map = {
				'visible': 'visible',
				'invisible': 'hidden',
				'collapse': 'collapse',
			};
			return { prop: '--v', value: map[match[1]] };
		}
	},

	// ── Order ────────────────────────────────────────────────────────────
	{
		pattern: /^(-?)order-(.+)$/,
		convert: (match) => {
			const [, neg, val] = match;
			const specialMap = {
				'first': '-9999',
				'last': '9999',
				'none': '0',
			};
			if (specialMap[val] !== undefined) return { prop: 'order', value: specialMap[val] };
			// Arbitrary
			const arbitrary = resolveArbitrary(val);
			if (arbitrary) return { prop: 'order', value: neg ? `-${arbitrary}` : arbitrary };
			// Numeric
			if (/^\d+$/.test(val)) return { prop: 'order', value: neg ? `-${val}` : val };
			return null;
		}
	},

	// ── Grid Template Columns ────────────────────────────────────────────
	{
		pattern: /^grid-cols-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'none') return { prop: '--gtc', value: 'none' };
			if (val === 'subgrid') return { prop: '--gtc', value: 'subgrid' };
			// Arbitrary
			const arbitrary = resolveArbitrary(val);
			if (arbitrary) return { prop: '--gtc', value: arbitrary };
			// Numeric
			if (/^\d+$/.test(val)) return { prop: '--gtc', value: `repeat(${val}, minmax(0, 1fr))` };
			return null;
		}
	},

	// ── Grid Template Rows ───────────────────────────────────────────────
	{
		pattern: /^grid-rows-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'none') return { prop: '--gtr', value: 'none' };
			if (val === 'subgrid') return { prop: '--gtr', value: 'subgrid' };
			// Arbitrary
			const arbitrary = resolveArbitrary(val);
			if (arbitrary) return { prop: '--gtr', value: arbitrary };
			// Numeric
			if (/^\d+$/.test(val)) return { prop: '--gtr', value: `repeat(${val}, minmax(0, 1fr))` };
			return null;
		}
	},

	// ── Column Span ──────────────────────────────────────────────────────
	{
		pattern: /^col-span-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'full') return { prop: '--gc', value: '1 / -1' };
			// Arbitrary
			const arbitrary = resolveArbitrary(val);
			if (arbitrary) return { prop: '--gc', value: arbitrary };
			// Numeric
			if (/^\d+$/.test(val)) return { prop: '--gc', value: `span ${val} / span ${val}` };
			return null;
		}
	},

	// ── Column Start ─────────────────────────────────────────────────────
	{
		pattern: /^col-start-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'auto') return { prop: 'grid-column-start', value: 'auto' };
			const arbitrary = resolveArbitrary(val);
			if (arbitrary) return { prop: 'grid-column-start', value: arbitrary };
			if (/^\d+$/.test(val)) return { prop: 'grid-column-start', value: val };
			return null;
		}
	},

	// ── Column End ───────────────────────────────────────────────────────
	{
		pattern: /^col-end-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'auto') return { prop: 'grid-column-end', value: 'auto' };
			const arbitrary = resolveArbitrary(val);
			if (arbitrary) return { prop: 'grid-column-end', value: arbitrary };
			if (/^\d+$/.test(val)) return { prop: 'grid-column-end', value: val };
			return null;
		}
	},

	// ── Row Span ─────────────────────────────────────────────────────────
	{
		pattern: /^row-span-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'full') return { prop: '--gr', value: '1 / -1' };
			const arbitrary = resolveArbitrary(val);
			if (arbitrary) return { prop: '--gr', value: arbitrary };
			if (/^\d+$/.test(val)) return { prop: '--gr', value: `span ${val} / span ${val}` };
			return null;
		}
	},

	// ── Row Start ────────────────────────────────────────────────────────
	{
		pattern: /^row-start-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'auto') return { prop: 'grid-row-start', value: 'auto' };
			const arbitrary = resolveArbitrary(val);
			if (arbitrary) return { prop: 'grid-row-start', value: arbitrary };
			if (/^\d+$/.test(val)) return { prop: 'grid-row-start', value: val };
			return null;
		}
	},

	// ── Row End ──────────────────────────────────────────────────────────
	{
		pattern: /^row-end-(.+)$/,
		convert: (match) => {
			const val = match[1];
			if (val === 'auto') return { prop: 'grid-row-end', value: 'auto' };
			const arbitrary = resolveArbitrary(val);
			if (arbitrary) return { prop: 'grid-row-end', value: arbitrary };
			if (/^\d+$/.test(val)) return { prop: 'grid-row-end', value: val };
			return null;
		}
	},

	// ── Auto Columns ─────────────────────────────────────────────────────
	{
		pattern: /^auto-cols-(auto|min|max|fr)$/,
		convert: (match) => {
			const map = {
				'auto': 'auto',
				'min': 'min-content',
				'max': 'max-content',
				'fr': 'minmax(0, 1fr)',
			};
			return { prop: '--gac', value: map[match[1]] };
		}
	},

	// ── Auto Rows ────────────────────────────────────────────────────────
	{
		pattern: /^auto-rows-(auto|min|max|fr)$/,
		convert: (match) => {
			const map = {
				'auto': 'auto',
				'min': 'min-content',
				'max': 'max-content',
				'fr': 'minmax(0, 1fr)',
			};
			return { prop: '--gar', value: map[match[1]] };
		}
	},

	// ── Gap ──────────────────────────────────────────────────────────────
	{
		pattern: /^gap-x-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			if (!resolved) return null;
			return { prop: 'column-gap', value: resolved };
		}
	},
	{
		pattern: /^gap-y-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			if (!resolved) return null;
			return { prop: 'row-gap', value: resolved };
		}
	},
	{
		pattern: /^gap-(.+)$/,
		convert: (match) => {
			const resolved = resolveSpacing(match[1]);
			if (!resolved) return null;
			return { prop: '--g', value: resolved };
		}
	},

];

export default layoutRules;
