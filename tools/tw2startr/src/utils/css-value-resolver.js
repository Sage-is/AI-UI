import { SPACING_SCALE, COLOR_PALETTE, RAW_COLORS } from './tailwind-values.js';

/**
 * Resolve arbitrary value: [22rem] -> 22rem, [100%] -> 100%, [#ff0000] -> #ff0000
 */
export function resolveArbitrary(value) {
	if (!value) return null;
	const match = value.match(/^\[(.+)\]$/);
	if (!match) return null;
	// Handle CSS variable syntax: [var(--something)]
	let resolved = match[1];
	// Replace underscores with spaces (Tailwind convention for arbitrary values)
	resolved = resolved.replace(/_/g, ' ');
	return resolved;
}

/**
 * Resolve spacing value: '4' -> '1rem', '0.5' -> '0.125rem', 'px' -> '1px', '[22rem]' -> '22rem'
 */
export function resolveSpacing(value) {
	if (!value) return null;
	// Check arbitrary first
	const arbitrary = resolveArbitrary(value);
	if (arbitrary) return arbitrary;
	// Check spacing scale
	if (SPACING_SCALE[value] !== undefined) return SPACING_SCALE[value];
	// Check if it's a decimal not in scale
	const num = parseFloat(value);
	if (!isNaN(num)) return `${num * 0.25}rem`;
	return null;
}

/**
 * Resolve color: 'gray-700' -> 'var(--color-gray-700, #4e4e4e)', 'white' -> '#fff'
 * With opacity: 'white/50' -> 'rgb(255 255 255 / 0.5)'
 */
export function resolveColor(colorStr) {
	if (!colorStr) return null;

	// Check arbitrary first
	const arbitrary = resolveArbitrary(colorStr);
	if (arbitrary) return arbitrary;

	// Handle opacity modifier: color/opacity
	const slashIdx = colorStr.indexOf('/');
	let colorName = colorStr;
	let opacity = null;

	if (slashIdx !== -1) {
		colorName = colorStr.substring(0, slashIdx);
		opacity = parseInt(colorStr.substring(slashIdx + 1)) / 100;
	}

	// Look up color
	const colorValue = COLOR_PALETTE[colorName];
	if (!colorValue) return null;

	if (opacity !== null) {
		// Need raw hex to compute rgba
		const rawHex = RAW_COLORS[colorName];
		if (rawHex) {
			const rgb = hexToRgb(rawHex);
			if (rgb) return `rgb(${rgb.r} ${rgb.g} ${rgb.b} / ${opacity})`;
		}
		return null;
	}

	return colorValue;
}

/**
 * Convert hex to RGB components
 */
function hexToRgb(hex) {
	hex = hex.replace('#', '');
	if (hex.length === 3) hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
	const num = parseInt(hex, 16);
	return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
}

/**
 * Resolve fraction value: '1/2' -> '50%', '2/3' -> '66.666667%', '1/4' -> '25%'
 */
export function resolveFraction(value) {
	if (!value) return null;
	const match = value.match(/^(\d+)\/(\d+)$/);
	if (!match) return null;
	const num = parseInt(match[1]);
	const den = parseInt(match[2]);
	if (den === 0) return null;
	return `${(num / den * 100).toFixed(6).replace(/\.?0+$/, '')}%`;
}

/**
 * Resolve negative prefix: '-mt-4' -> negative spacing
 */
export function resolveNegative(value) {
	return `-${value}`;
}
