/**
 * Apply admin branding colors as Startr.Style CSS variable overrides — the ONE
 * implementation, imported by +layout.svelte (boot) and admin Settings
 * Theme.svelte (live preview). The server-rendered shell (pages/shell.py)
 * emits the same prop set; change one, change both.
 *
 * Startr.Style cascades from --primary/--secondary (--links,
 * --background-alt, --focus, --button-hover). A theme Sprig sheet may set
 * --links/--button-hover as LITERALS at :root, which severs that cascade —
 * the brand color then never reaches links. Redeclaring the var() form
 * inline restores the cascade; the framework's own color-mix recipes
 * re-resolve. No color math belongs here.
 */
export type BrandingColors = {
	primary_color?: string;
	accent_color?: string;
	// Set by GET /configs/branding when a theme Sprig is grafted. The Sprig
	// owns the look while active — accents AND gray scale stay coherent — so
	// branding colors step back entirely instead of half-winning into a
	// mishmash. The branding surfaces warn and offer the prune.
	active_theme_sprig?: string | null;
	active_theme_label?: string | null;
};

export const applyBrandingColors = (b: BrandingColors | undefined | null) => {
	const root = document.documentElement;
	if (b?.active_theme_sprig) {
		root.style.removeProperty('--primary');
		root.style.removeProperty('--secondary');
		root.style.removeProperty('--links');
		root.style.removeProperty('--button-hover');
		return;
	}
	if (b?.primary_color) {
		root.style.setProperty('--primary', b.primary_color);
		root.style.setProperty('--links', 'var(--primary)');
		root.style.setProperty('--button-hover', 'var(--primary)');
	} else {
		root.style.removeProperty('--primary');
		root.style.removeProperty('--links');
		root.style.removeProperty('--button-hover');
	}
	if (b?.accent_color) {
		root.style.setProperty('--secondary', b.accent_color);
	} else {
		root.style.removeProperty('--secondary');
	}
};
