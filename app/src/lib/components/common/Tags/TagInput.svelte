<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { tags } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import Icon from '$lib/components/Icon.svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let label = '';
	let showTagInput = false;
	let tagName = '';

	const addTagHandler = async () => {
		tagName = tagName.trim();
		if (tagName !== '') {
			dispatch('add', tagName);
			tagName = '';
			showTagInput = false;
		} else {
			toast.error($i18n.t(`Invalid Tag`));
		}
	};
</script>

<div style="--px:0.125rem; --d:flex"
	class="{showTagInput ? 'flex-row-reverse' : ''}">
	{#if showTagInput}
		<div style="--d:flex; --ai:center">
			<input
				bind:value={tagName}
				style="--px:0.5rem; --cur:pointer; --as:center; --size:0.6rem; --h:fit-content; --bgc:transparent; --oe:none; --line-clamp:1; --w:6.5rem"
				placeholder={$i18n.t('Add a tag')}
				aria-label={$i18n.t('Add a tag')}
				list="tagOptions"
				on:keydown={(event) => {
					if (event.key === 'Enter') {
						addTagHandler();
					}
				}}
			/>
			<datalist id="tagOptions">
				{#each $tags as tag}
					<option value={tag.name} />
				{/each}
			</datalist>

			<button type="button" aria-label={$i18n.t('Save Tag')} on:click={addTagHandler}>
				<Icon name="check-fill-16" className="size-[0.6rem]" strokeWidth="2" />
			</button>
		</div>
	{/if}

	<button
		style="--cur:pointer; --as:center; --p:0.125rem; --d:flex; --h:fit-content; --ai:center; --hvr-dark-bgc:var(--color-gray-700); --radius:9999px; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1);  --dark-bc:var(--color-gray-600); ; --lh:0.4"
		type="button"
		aria-label={$i18n.t('Add Tag')}
		on:click={() => {
			showTagInput = !showTagInput;
		}}
	>
		<div style="--m:auto; --as:center">
			<Icon name="plus-fill-16" className="size-[0.6rem]" />
		</div>
	</button>

	{#if label && !showTagInput}
		<span style="--size:0.6rem; --pl:0.5rem; --as:center">{label}</span>
	{/if}
</div>
