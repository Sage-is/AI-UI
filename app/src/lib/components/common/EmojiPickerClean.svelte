<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import emojiData from '$lib/emoji-groups-clean.json';

	export let onSubmit = (emoji: string) => {};
	export let side = 'top';
	export let align = 'start';

	let show = false;

	const SKIN_TONE_MODIFIERS = ['🏻', '🏼', '🏽', '🏾', '🏿'];

	// Create a segmenter once for reuse
	const segmenter = new Intl.Segmenter('en', { granularity: 'grapheme' });

	function getEmojisForCategory(category: string): string[] {
		const emojiString = emojiData[category] || '';
		return [...segmenter.segment(emojiString)].map(s => s.segment);
	}

	function selectEmoji(emoji: string) {
		onSubmit(emoji);
		show = false;
	}
</script>

<DropdownMenu.Root bind:open={show} closeFocus={false} typeahead={false}>
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
		<!-- Search Input -->
		<div class="mb-1 px-3 pt-2 pb-2">
			<input
				type="text"
				class="w-full text-sm bg-transparent outline-hidden"
				placeholder="Search emojis..."
				on:input={(e) => {
					// TODO: Implement search filtering
				}}
			/>
		</div>

		<div class="h-80 overflow-y-auto p-2">
			{#each Object.entries(emojiData) as [category, emojiString]}
				<div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">{category}</div>
				<div class="grid grid-cols-8 gap-1 mb-3">
					{#each getEmojisForCategory(category) as emoji}
						<!-- LOGIC: Check if the category is the one that needs skin tone options -->
						{#if category === 'People & Body'}
							<DropdownMenu.Sub>
								<DropdownMenu.SubTrigger 
									class="p-1.5 rounded-lg cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 transition flex items-center justify-center text-lg"
								>
									<span class="emoji-font">{emoji}</span>
								</DropdownMenu.SubTrigger>
								<DropdownMenu.SubContent 
									class="bg-gray-50 dark:bg-gray-850 rounded-lg shadow-lg p-2"
								>
									<!-- Base emoji (no skin tone) -->
									<DropdownMenu.Item 
										class="p-1.5 rounded cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 transition"
										on:click={() => selectEmoji(emoji)}
									>
										<span class="emoji-font text-lg">{emoji}</span>
									</DropdownMenu.Item>
									<!-- Skin tone variants -->
									{#each SKIN_TONE_MODIFIERS as modifier}
										<DropdownMenu.Item 
											class="p-1.5 rounded cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 transition"
											on:click={() => selectEmoji(emoji + modifier)}
										>
											<span class="emoji-font text-lg">{emoji + modifier}</span>
										</DropdownMenu.Item>
									{/each}
								</DropdownMenu.SubContent>
							</DropdownMenu.Sub>
						{:else}
							<button 
								class="p-1.5 rounded-lg cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 transition flex items-center justify-center text-lg"
								on:click={() => selectEmoji(emoji)}
							>
								<span class="emoji-font">{emoji}</span>
							</button>
						{/if}
					{/each}
				</div>
			{/each}
		</div>
	</DropdownMenu.Content>
</DropdownMenu.Root>

<style>
	.emoji-font {
		font-family: "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif;
	}
</style>
