<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { tags } from '$lib/stores';
	import { toast } from 'svelte-sonner';
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
				style="--px:0.5rem; --cur:pointer; --as:center; --size:0.75rem; --h:fit-content; --bgc:transparent; --oe:none; --line-clamp:1; --w:6.5rem"
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
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					stroke-width="2"
					aria-hidden="true"
					style="--w:0.75rem; --h:0.75rem"
				>
					<path
						fill-rule="evenodd"
						d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		</div>
	{/if}

	<button
		style="--cur:pointer; --as:center; --p:0.125rem; --d:flex; --h:fit-content; --ai:center; --hvr-dark-bgc:var(--color-gray-700, #4e4e4e); --radius:9999px; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --b:1px solid; --dark-bc:var(--color-gray-600, #676767); --bs:dashed; --lh:0.4"
		type="button"
		aria-label={$i18n.t('Add Tag')}
		on:click={() => {
			showTagInput = !showTagInput;
		}}
	>
		<div style="--m:auto; --as:center">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 16 16"
				aria-hidden="true"
				fill="currentColor"
				style="--w:0.75rem; --h:0.75rem; --tn:all 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{showTagInput ? 'rotate-45' : ''} transform"
			>
				<path
					d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
				/>
			</svg>
		</div>
	</button>

	{#if label && !showTagInput}
		<span style="--size:0.75rem; --pl:0.5rem; --as:center">{label}</span>
	{/if}
</div>
