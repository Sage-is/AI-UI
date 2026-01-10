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
		class="max-w-full w-80 bg-gray-50 dark:bg-gray-850 rounded-lg z-9999 shadow-lg dark:text-white"
		sideOffset={8}
		{side}
		{align}
		transition={flyAndScale}
	>
		<div class="mb-1 px-3 pt-2 pb-2">
			<input
				type="text"
				class="w-full text-sm bg-transparent outline-hidden"
				placeholder="Search emojis by name or shortcode..."
				bind:value={search}
			/>
		</div>
		
		<!-- Virtualized Emoji List -->
		<div class="w-full flex justify-start h-96 overflow-y-auto px-3 pb-3 text-sm">
			{#if emojiRows.length === 0}
				<div class="text-center text-xs text-gray-500 dark:text-gray-400">No results</div>
			{:else}
				<div class="w-full flex ml-0.5">
					<VirtualList rowHeight={ROW_HEIGHT} items={emojiRows} height={384} let:item>
						<div class="w-full">
							{#if item.length === 1 && item[0].type === 'group'}
								<!-- Render group header -->
								<div class="text-xs font-medium mb-2 text-gray-500 dark:text-gray-400">
									{item[0].label}
								</div>
							{:else}
								<!-- Render emojis in a row -->
								<div class="flex items-center gap-1.5 w-full">
									{#each item as emojiItem}
										{#if emojiItem.supportsSkinTones}
											<!-- Emoji with skin tone support -->
											<DropdownMenu.Sub>
												<DropdownMenu.SubTrigger 
													class="p-1.5 rounded-lg cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 transition flex items-center justify-center emoji-font text-lg"
												>
													{emojiItem.emoji}
												</DropdownMenu.SubTrigger>
												<DropdownMenu.SubContent 
													class="bg-gray-50 dark:bg-gray-850 rounded-lg shadow-lg p-2 grid grid-cols-3 gap-1"
												>
													<!-- Base emoji (no skin tone) -->
													<DropdownMenu.Item 
														class="p-1.5 rounded cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 transition emoji-font text-lg flex items-center justify-center"
														on:click={() => selectEmoji(emojiItem.emoji)}
													>
														{emojiItem.emoji}
													</DropdownMenu.Item>
													<!-- Skin tone variants -->
													{#each SKIN_TONE_MODIFIERS as modifier}
														<DropdownMenu.Item 
															class="p-1.5 rounded cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 transition emoji-font text-lg flex items-center justify-center"
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
													class="p-1.5 rounded-lg cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 transition emoji-font text-lg flex items-center justify-center"
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
