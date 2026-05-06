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
 * Resolve color: 'gray-700' -> 'var(--color-gray-700, hsl(0 0% 31%))', 'white' -> 'hsl(0 0% 100%)'
 * With opacity: 'white/50' -> 'hsl(0 0% 100% / 0.5)'
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
		const rawHex = RAW_COLORS[colorName];
		if (rawHex) {
			const hsl = hexToHsl(rawHex);
			if (hsl) return `hsl(${hsl.h} ${hsl.s}% ${hsl.l}% / ${opacity})`;
		}
		return null;
	}

	// Convert palette value (hex or var(--x, #hex)) to use hsl
	return hexColorToHsl(colorValue);
}

/**
 * Convert a hex color string to HSL components.
 */
function hexToHsl(hex) {
	hex = hex.replace('#', '');
	if (hex.length === 3) hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
	const num = parseInt(hex, 16);
	let r = ((num >> 16) & 255) / 255;
	let g = ((num >> 8) & 255) / 255;
	let b = (num & 255) / 255;
	const max = Math.max(r, g, b), min = Math.min(r, g, b);
	let h = 0, s = 0;
	const l = (max + min) / 2;
	if (max !== min) {
		const d = max - min;
		s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
		switch (max) {
			case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
			case g: h = ((b - r) / d + 2) / 6; break;
			case b: h = ((r - g) / d + 4) / 6; break;
		}
	}
	return { h: Math.round(h * 360), s: Math.round(s * 100), l: Math.round(l * 100) };
}

/**
 * Convert a COLOR_PALETTE value (plain hex or var(--x, #hex)) to its HSL equivalent.
 * '#15803d' -> 'hsl(142 72% 29%)'
 * 'var(--color-gray-100, #ececec)' -> 'var(--color-gray-100, hsl(0 0% 93%))'
 */
function hexColorToHsl(colorValue) {
	// var(--token, #hex) form
	const varMatch = colorValue.match(/^(var\([^,]+,\s*)(#[0-9a-fA-F]{3,6})(\))$/);
	if (varMatch) {
		const hsl = hexToHsl(varMatch[2]);
		if (hsl) return `${varMatch[1]}hsl(${hsl.h} ${hsl.s}% ${hsl.l}%)${varMatch[3]}`;
		return colorValue;
	}
	// Plain #hex
	if (/^#[0-9a-fA-F]{3,6}$/.test(colorValue)) {
		const hsl = hexToHsl(colorValue);
		if (hsl) return `hsl(${hsl.h} ${hsl.s}% ${hsl.l}%)`;
	}
	return colorValue;
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
