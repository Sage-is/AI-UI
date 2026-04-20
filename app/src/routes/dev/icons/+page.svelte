<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import { ICON_NAMES, FILL_ONLY_ICONS, ICON_DEFAULT_STROKE } from '$lib/components/icons';

	let strokeWidth = '1.5';
	let iconColor = '#333333';
	let iconSize = 'size-6';

	const allIcons = Object.entries(ICON_NAMES).map(([pascal, kebab]) => ({
		pascal,
		kebab,
		isFill: FILL_ONLY_ICONS.has(kebab),
		defaultStroke: ICON_DEFAULT_STROKE[kebab] || '1.5'
	}));

	const strokeIcons = allIcons.filter((i) => !i.isFill);
	const fillIcons = allIcons.filter((i) => i.isFill);
</script>

<svelte:head>
	<title>Icon Sprite Test</title>
</svelte:head>

<div
	style="font-family: system-ui;  margin: 0 auto; padding: 2rem; max-height: 100vh; overflow-y: auto;"
>
	<article style="max-width: 1200px; margin: 0 auto;">
		<h1 style="font-size: 1.5rem; font-weight: 600; margin-bottom: 1rem;">
			Icon Sprite Sheet Test ({allIcons.length} icons)
		</h1>

		<div
			style="display: flex; gap: 1.5rem; align-items: center; margin-bottom: 2rem; padding: 1rem; background: #f5f5f5; border-radius: 8px;"
		>
			<label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem;">
				strokeWidth:
				<input type="range" min="0.5" max="4" step="0.5" bind:value={strokeWidth} />
				<span style="font-weight: 600; min-width: 2rem;">{strokeWidth}</span>
			</label>

			<label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem;">
				Color:
				<input type="color" bind:value={iconColor} />
			</label>

			<label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem;">
				Size:
				<select bind:value={iconSize}>
					<option value="size-3">size-3</option>
					<option value="size-4">size-4</option>
					<option value="size-5">size-5</option>
					<option value="size-6">size-6</option>
					<option value="size-8">size-8</option>
					<option value="size-10">size-10</option>
				</select>
			</label>
		</div>

		<h2 style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">
			Stroke Icons ({strokeIcons.length})
		</h2>
		<div
			style="display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 0.5rem; margin-bottom: 2rem;"
		>
			{#each strokeIcons as icon}
				<div
					style="display: flex; flex-direction: column; align-items: center; gap: 0.3rem; padding: 0.5rem; border: 1px solid #eee; border-radius: 6px; color: {iconColor};"
					title="{icon.pascal} ({icon.kebab}) — default stroke: {icon.defaultStroke}"
				>
					<Icon name={icon.kebab} className={iconSize} {strokeWidth} />
					<span style="font-size: 0.6rem; color: #999; text-align: center; word-break: break-all;">
						{icon.kebab}
					</span>
				</div>
			{/each}
		</div>

		<h2 style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">
			Fill Icons ({fillIcons.length})
		</h2>
		<div
			style="display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 0.5rem; margin-bottom: 2rem;"
		>
			{#each fillIcons as icon}
				<div
					style="display: flex; flex-direction: column; align-items: center; gap: 0.3rem; padding: 0.5rem; border: 1px solid #eee; border-radius: 6px; color: {iconColor};"
					title="{icon.pascal} ({icon.kebab})"
				>
					<Icon name={icon.kebab} className={iconSize} />
					<span style="font-size: 0.6rem; color: #999; text-align: center; word-break: break-all;">
						{icon.kebab}
					</span>
				</div>
			{/each}
		</div>

		<h2 style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">Edge Cases</h2>
		<div
			style="display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 1rem; margin-bottom: 2rem;"
		>
			<div style="padding: 1rem; border: 1px solid #ddd; border-radius: 8px; color: {iconColor};">
				<div style="font-size: 0.75rem; font-weight: 600; margin-bottom: 0.5rem;">
					photo (hardcoded sw:2)
				</div>
				<div style="display: flex; gap: 0.5rem; align-items: center;">
					<Icon name="photo" className="size-4" />
					<Icon name="photo" className="size-6" />
					<Icon name="photo" className="size-8" />
				</div>
			</div>

			<div style="padding: 1rem; border: 1px solid #ddd; border-radius: 8px; color: {iconColor};">
				<div style="font-size: 0.75rem; font-weight: 600; margin-bottom: 0.5rem;">
					check-box (hardcoded sw:1.5)
				</div>
				<div style="display: flex; gap: 0.5rem; align-items: center;">
					<Icon name="check-box" className="size-4" />
					<Icon name="check-box" className="size-6" />
					<Icon name="check-box" className="size-8" />
				</div>
			</div>

			<div style="padding: 1rem; border: 1px solid #ddd; border-radius: 8px; color: {iconColor};">
				<div style="font-size: 0.75rem; font-weight: 600; margin-bottom: 0.5rem;">
					link (viewBox 16x16)
				</div>
				<div style="display: flex; gap: 0.5rem; align-items: center;">
					<Icon name="link" className="size-4" />
					<Icon name="link" className="size-6" />
					<Icon name="link" className="size-8" />
				</div>
			</div>

			<div style="padding: 1rem; border: 1px solid #ddd; border-radius: 8px; color: {iconColor};">
				<div style="font-size: 0.75rem; font-weight: 600; margin-bottom: 0.5rem;">
					home (viewBox 22x22)
				</div>
				<div style="display: flex; gap: 0.5rem; align-items: center;">
					<Icon name="home" className="size-4" />
					<Icon name="home" className="size-6" />
					<Icon name="home" className="size-8" />
				</div>
			</div>

			<div style="padding: 1rem; border: 1px solid #ddd; border-radius: 8px; color: {iconColor};">
				<div style="font-size: 0.75rem; font-weight: 600; margin-bottom: 0.5rem;">
					xmark (dynamic strokeWidth)
				</div>
				<div style="display: flex; gap: 0.5rem; align-items: center;">
					<Icon name="xmark" className="size-6" strokeWidth="1" />
					<Icon name="xmark" className="size-6" strokeWidth="2" />
					<Icon name="xmark" className="size-6" strokeWidth="3" />
				</div>
			</div>

			<div style="padding: 1rem; border: 1px solid #ddd; border-radius: 8px;">
				<div style="font-size: 0.75rem; font-weight: 600; margin-bottom: 0.5rem;">
					currentColor inheritance
				</div>
				<div style="display: flex; gap: 0.5rem; align-items: center;">
					<span style="color: #ef4444"><Icon name="heart" className="size-6" /></span>
					<span style="color: #3b82f6"><Icon name="heart" className="size-6" /></span>
					<span style="color: #22c55e"><Icon name="heart" className="size-6" /></span>
				</div>
			</div>
		</div>
	</article>
</div>
