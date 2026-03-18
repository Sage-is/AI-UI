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
		style="--maxw:100%; --w:20rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --radius:0.5rem; --z:9999; --shadow:4; --dark-c:#fff"
		sideOffset={8}
		{side}
		{align}
		transition={flyAndScale}
	>
		<!-- Search Input -->
		<div style="--mb:0.25rem; --px:0.6rem; --pt:0.5rem; --pb:0.5rem">
			<input
				type="text"
				style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
				placeholder="Search emojis..."
				on:input={(e) => {
					// TODO: Implement search filtering
				}}
			/>
		</div>

		<div style="--h:20rem; --ofy:auto; --p:0.5rem">
			{#each Object.entries(emojiData) as [category, emojiString]}
				<div style="--size:0.6rem; --weight:500; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:0.5rem">{category}</div>
				<div style="--d:grid; --gtc:repeat(8, minmax(0, 1fr)); --g:0.25rem; --mb:0.6rem">
					{#each getEmojisForCategory(category) as emoji}
						<!-- LOGIC: Check if the category is the one that needs skin tone options -->
						{#if category === 'People & Body'}
							<DropdownMenu.Sub>
								<DropdownMenu.SubTrigger 
									style="--p:0.375rem; --radius:0.5rem; --cur:pointer; --hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-700); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --d:flex; --ai:center; --jc:center; --size:1.125rem"
								>
									<span class="emoji-font">{emoji}</span>
								</DropdownMenu.SubTrigger>
								<DropdownMenu.SubContent 
									style="--bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --radius:0.5rem; --shadow:4; --p:0.5rem"
								>
									<!-- Base emoji (no skin tone) -->
									<DropdownMenu.Item 
										style="--p:0.375rem; --radius:0.25rem; --cur:pointer; --hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-700); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
										on:click={() => selectEmoji(emoji)}
									>
										<span style="--size:1.125rem"
	class="emoji-font">{emoji}</span>
									</DropdownMenu.Item>
									<!-- Skin tone variants -->
									{#each SKIN_TONE_MODIFIERS as modifier}
										<DropdownMenu.Item 
											style="--p:0.375rem; --radius:0.25rem; --cur:pointer; --hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-700); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
											on:click={() => selectEmoji(emoji + modifier)}
										>
											<span style="--size:1.125rem"
	class="emoji-font">{emoji + modifier}</span>
										</DropdownMenu.Item>
									{/each}
								</DropdownMenu.SubContent>
							</DropdownMenu.Sub>
						{:else}
							<button 
								style="--p:0.375rem; --radius:0.5rem; --cur:pointer; --hvr-bgc:var(--color-gray-200); --hvr-dark-bgc:var(--color-gray-700); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --d:flex; --ai:center; --jc:center; --size:1.125rem"
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
