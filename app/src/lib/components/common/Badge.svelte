<script lang="ts">
	export let type = 'info';
	export let content = '';

	const colorStyles: Record<string, string> = {
		info: '--bgc:rgb(59 130 246 / 0.30); --c:#1e3a8a; --dark-bgc:rgb(96 165 250 / 0.25); --dark-c:#93c5fd',
		success: '--bgc:rgb(34 197 94 / 0.30); --c:#14532d; --dark-bgc:rgb(74 222 128 / 0.25); --dark-c:#86efac',
		warning: '--bgc:rgb(234 179 8 / 0.30); --c:#713f12; --dark-bgc:rgb(250 204 21 / 0.25); --dark-c:#fef08a',
		error: '--bgc:rgb(239 68 68 / 0.30); --c:#7f1d1d; --dark-bgc:rgb(248 113 113 / 0.25); --dark-c:#fecaca',
		muted: '--bgc:rgb(107 114 128 / 0.30); --c:#1f2937; --dark-bgc:rgb(156 163 175 / 0.25); --dark-c:#e5e7eb'
	};
</script>

<div
	style="--size:0.6rem; --weight:700; --w:fit-content; --px:0.5rem; --radius:0.125rem; --tt:uppercase; --line-clamp:1; --mr:0.125rem; {colorStyles[type] ?? colorStyles['info']}"
>
	{content}
</div>
