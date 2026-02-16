<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import emojiData from '$lib/emoji-groups-clean.json';
	import emojiShortcodes from '$lib/emoji-shortcodes-clean.json';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import VirtualList from '@sveltejs/svelte-virtual-list';

	export let onClose = () => {};
	export let onSubmit = (emoji: string) => {};
	export let side = 'top';
	export let align = 'start';
	export let user = null;

	let show = false;
	let search = '';
	let filteredEmojis = [];
	let emojiRows = [];

	const SKIN_TONE_MODIFIERS = ['🏻', '🏼', '🏽', '🏾', '🏿'];

	// Create a segmenter once for reuse
	const segmenter = new Intl.Segmenter('en', { granularity: 'grapheme' });

	function getEmojisForCategory(category: string): string[] {
		const emojiString = emojiData[category] || '';
		return [...segmenter.segment(emojiString)].map(s => s.segment);
	}

	// Reactive statement to filter and organize emojis
	$: {
		filteredEmojis = [];
		
		Object.entries(emojiData).forEach(([category, emojiString]) => {
			const categoryEmojis = getEmojisForCategory(category);
			
			// Filter by search if search term exists
			const emojisToShow = search 
				? categoryEmojis.filter(emoji => {
					// Search in emoji itself, category name, or shortcodes
					const matchesEmoji = emoji.includes(search);
					const matchesCategory = category.toLowerCase().includes(search.toLowerCase());
					const matchesShortcode = emojiShortcodes[emoji] && 
						emojiShortcodes[emoji].some(shortcode => 
							shortcode.toLowerCase().includes(search.toLowerCase())
						);
					
					return matchesEmoji || matchesCategory || matchesShortcode;
				})
				: categoryEmojis;

			if (emojisToShow.length > 0) {
				filteredEmojis.push({ type: 'group', label: category });
				filteredEmojis.push(...emojisToShow.map(emoji => ({
					type: 'emoji',
					emoji,
					category,
					shortcodes: emojiShortcodes[emoji] || [],
					supportsSkinTones: category === 'People & Body'
				})));
			}
		});

		// Group into rows of 8 for virtual scrolling
		emojiRows = [];
		let currentRow = [];
		
		filteredEmojis.forEach((item) => {
			if (item.type === 'emoji') {
				currentRow.push(item);
				if (currentRow.length === 8) {
					emojiRows.push(currentRow);
					currentRow = [];
				}
			} else if (item.type === 'group') {
				// Push any remaining emojis in current row
				if (currentRow.length > 0) {
					emojiRows.push(currentRow);
					currentRow = [];
				}
				// Add group label as separate row
				emojiRows.push([item]);
			}
		});
		
		// Push final row if it has content
		if (currentRow.length > 0) {
			emojiRows.push(currentRow);
		}
	}

	const ROW_HEIGHT = 48; // Height for emoji rows

	// Handle emoji selection
	function selectEmoji(emoji: string) {
		onSubmit(emoji);
		show = false;
	}
</script>

<DropdownMenu.Root
	bind:open={show}
	closeFocus={false}
	onOpenChange={(state) => {
		if (!state) {
			search = '';
			onClose();
		}
	}}
	typeahead={false}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>
	<DropdownMenu.Content
		style="--maxw:100%; --w:20rem; --bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-850, #262626); --radius:0.5rem; --z:9999; --shadow:4; --dark-c:#fff"
		sideOffset={8}
		{side}
		{align}
		transition={flyAndScale}
	>
		<div style="--mb:0.25rem; --px:0.75rem; --pt:0.5rem; --pb:0.5rem">
			<input
				type="text"
				style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
				placeholder="Search emojis by name or shortcode..."
				bind:value={search}
			/>
		</div>
		
		<!-- Virtualized Emoji List -->
		<div style="--w:100%; --d:flex; --jc:flex-start; --h:24rem; --ofy:auto; --px:0.75rem; --pb:0.75rem; --size:0.875rem">
			{#if emojiRows.length === 0}
				<div style="--ta:center; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b); --dark-c:var(--color-gray-400, #b4b4b4)">No results</div>
			{:else}
				<div style="--w:100%; --d:flex; --ml:0.125rem">
					<VirtualList rowHeight={ROW_HEIGHT} items={emojiRows} height={384} let:item>
						<div style="--w:100%">
							{#if item.length === 1 && item[0].type === 'group'}
								<!-- Render group header -->
								<div style="--size:0.75rem; --weight:500; --mb:0.5rem; --c:var(--color-gray-500, #9b9b9b); --dark-c:var(--color-gray-400, #b4b4b4)">
									{item[0].label}
								</div>
							{:else}
								<!-- Render emojis in a row -->
								<div style="--d:flex; --ai:center; --g:0.375rem; --w:100%">
									{#each item as emojiItem}
										{#if emojiItem.supportsSkinTones}
											<!-- Emoji with skin tone support -->
											<DropdownMenu.Sub>
												<DropdownMenu.SubTrigger 
													style="--p:0.375rem; --radius:0.5rem; --cur:pointer; --hvr-bgc:var(--color-gray-200, #e3e3e3); --hvr-dark-bgc:var(--color-gray-700, #4e4e4e); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --d:flex; --ai:center; --jc:center; --size:1.125rem"
	class="emoji-font"
												>
													{emojiItem.emoji}
												</DropdownMenu.SubTrigger>
												<DropdownMenu.SubContent 
													style="--bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-850, #262626); --radius:0.5rem; --shadow:4; --p:0.5rem; --d:grid; --gtc:repeat(3, minmax(0, 1fr)); --g:0.25rem"
												>
													<!-- Base emoji (no skin tone) -->
													<DropdownMenu.Item 
														style="--p:0.375rem; --radius:0.25rem; --cur:pointer; --hvr-bgc:var(--color-gray-200, #e3e3e3); --hvr-dark-bgc:var(--color-gray-700, #4e4e4e); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --size:1.125rem; --d:flex; --ai:center; --jc:center"
	class="emoji-font"
														on:click={() => selectEmoji(emojiItem.emoji)}
													>
														{emojiItem.emoji}
													</DropdownMenu.Item>
													<!-- Skin tone variants -->
													{#each SKIN_TONE_MODIFIERS as modifier}
														<DropdownMenu.Item 
															style="--p:0.375rem; --radius:0.25rem; --cur:pointer; --hvr-bgc:var(--color-gray-200, #e3e3e3); --hvr-dark-bgc:var(--color-gray-700, #4e4e4e); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --size:1.125rem; --d:flex; --ai:center; --jc:center"
	class="emoji-font"
															on:click={() => selectEmoji(emojiItem.emoji + modifier)}
														>
															{emojiItem.emoji + modifier}
														</DropdownMenu.Item>
													{/each}
												</DropdownMenu.SubContent>
											</DropdownMenu.Sub>
										{:else}
											<!-- Regular emoji without skin tone support -->
											<Tooltip 
												content={emojiItem.shortcodes.length > 0 
													? emojiItem.shortcodes.map(code => `:${code}:`).join(', ')
													: emojiItem.emoji
												} 
												placement="top"
											>
												<button
													style="--p:0.375rem; --radius:0.5rem; --cur:pointer; --hvr-bgc:var(--color-gray-200, #e3e3e3); --hvr-dark-bgc:var(--color-gray-700, #4e4e4e); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --size:1.125rem; --d:flex; --ai:center; --jc:center"
	class="emoji-font"
													on:click={() => selectEmoji(emojiItem.emoji)}
												>
													{emojiItem.emoji}
												</button>
											</Tooltip>
										{/if}
									{/each}
								</div>
							{/if}
						</div>
					</VirtualList>
				</div>
			{/if}
		</div>
	</DropdownMenu.Content>
</DropdownMenu.Root>

<style>
	.emoji-font {
		font-family: "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif;
	}
</style>
