<script lang="ts">
	import { getAllTags } from '$lib/apis/chats';
	import { tags } from '$lib/stores';
	import { getContext, createEventDispatcher, onMount, onDestroy, tick } from 'svelte';
	import { fade } from 'svelte/transition';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let placeholder = '';
	export let value = '';
	export let showClearButton = false;
	export let onKeydown = (e) => {};

	let selectedIdx = 0;

	let lastWord = '';
	$: lastWord = value ? value.split(' ').at(-1) : value;

	let options = [
		{
			name: 'tag:',
			description: $i18n.t('search for tags')
		}
	];
	let focused = false;
	let loading = false;

	let filteredOptions = options;
	$: filteredOptions = options.filter((option) => {
		return option.name.startsWith(lastWord);
	});

	let filteredTags = [];
	$: filteredTags = lastWord.startsWith('tag:')
		? [
				...$tags,
				{
					id: 'none',
					name: $i18n.t('Untagged')
				}
			].filter((tag) => {
				const tagName = lastWord.slice(4);
				if (tagName) {
					const tagId = tagName.replace(' ', '_').toLowerCase();

					if (tag.id !== tagId) {
						return tag.id.startsWith(tagId);
					} else {
						return false;
					}
				} else {
					return true;
				}
			})
		: [];

	const initTags = async () => {
		loading = true;
		await tags.set(await getAllTags(localStorage.token));
		loading = false;
	};

	const clearSearchInput = () => {
		value = '';
		dispatch('input');
	};

	const documentClickHandler = (e) => {
		const searchContainer = document.getElementById('search-container');
		const chatSearch = document.getElementById('chat-search');

		if (!searchContainer.contains(e.target) && !chatSearch.contains(e.target)) {
			if (e.target.id.startsWith('search-tag-') || e.target.id.startsWith('search-option-')) {
				return;
			}
			focused = false;
		}
	};

	onMount(() => {
		document.addEventListener('click', documentClickHandler);
	});

	onDestroy(() => {
		document.removeEventListener('click', documentClickHandler);
	});
</script>

<div
	style="--px:0.2rem; --mb:0.2rem; --d:flex; --jc:center; --g:0.5rem; --pos:relative; --z:10"
	id="search-container"
>
	<div style="--d:flex; --w:100%; --radius:0.6rem" id="chat-search">
		<div
			style="--as:center; --py:0.5rem; --btlr:0.6rem; --bblr:0.6rem; --bgc:transparent; --dark-c:var(--color-gray-300)"
		>
			<Search />
		</div>

		<input
			id="search-input"
			style="--w:100%; --btrr:0.6rem; --bbrr:0.6rem; --p:0.625rem; --m:1rem; --size:0.8rem; --bgc:transparent; --dark-c:var(--color-gray-300); --oe:none"
			placeholder={placeholder ? placeholder : $i18n.t('Search')}
			bind:value
			on:input={() => {
				dispatch('input');
			}}
			on:focus={() => {
				focused = true;
				initTags();
			}}
			on:blur={() => {
				focused = false;
			}}
			on:keydown={(e) => {
				if (e.key === 'Enter') {
					if (filteredTags.length > 0) {
						const tagElement = document.getElementById(`search-tag-${selectedIdx}`);
						tagElement.click();
						return;
					}

					if (filteredOptions.length > 0) {
						const optionElement = document.getElementById(`search-option-${selectedIdx}`);
						optionElement.click();
						return;
					}
				}

				if (e.key === 'ArrowUp') {
					e.preventDefault();
					selectedIdx = Math.max(0, selectedIdx - 1);
				} else if (e.key === 'ArrowDown') {
					e.preventDefault();

					if (filteredTags.length > 0) {
						selectedIdx = Math.min(selectedIdx + 1, filteredTags.length - 1);
					} else {
						selectedIdx = Math.min(selectedIdx + 1, filteredOptions.length - 1);
					}
				} else {
					// if the user types something, reset to the top selection.
					selectedIdx = 0;
				}

				if (!document.getElementById('search-options-container')) {
					onKeydown(e);
				}
			}}
		/>

		{#if showClearButton && value}
			<div
				style="--as:center; --pl:0.4rem; --translatey:0.5px; --btlr:0.6rem; --bblr:0.6rem; --bgc:transparent"
			>
				<button
					style="--p:0.125rem; --radius:9999px; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-900); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={clearSearchInput}
				>
					<XMark className="size-3" strokeWidth="2" />
				</button>
			</div>
		{/if}
	</div>

	{#if focused && (filteredOptions.length > 0 || filteredTags.length > 0)}
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div
			style="--pos:absolute; --top:0; --mt:4rem; --left:0; --right:0.2rem; --bc:var(--color-gray-100); --dark-bc:var(--color-gray-900); --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-950); --radius:0.5rem; --z:10; --shadow:4"
			id="search-options-container"
			in:fade={{ duration: 50 }}
			on:mousedown|preventDefault
			on:mouseenter={() => {
				selectedIdx = null;
			}}
			on:mouseleave={() => {
				selectedIdx = 0;
			}}
		>
			<div style="--px:0.5rem; --py:0.5rem; --size:0.6rem" class="group">
				{#if filteredTags.length > 0}
					<div
						style="--px:0.2rem; --weight:500; --dark-c:var(--color-gray-300); --c:var(--color-gray-700); --mb:0.2rem"
					>
						Tags
					</div>

					<div style="--maxh:15rem; --of:auto">
						{#each filteredTags as tag, tagIdx}
							<button
								style="--px:0.4rem; --py:0.125rem; --d:flex; --g:0.2rem; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-900); --w:100%; --radius:0.2rem"
								class={selectedIdx === tagIdx ? 'bg-gray-100 dark:bg-gray-900' : ''}
								id="search-tag-{tagIdx}"
								on:click|stopPropagation={async () => {
									const words = value.split(' ');

									words.pop();
									words.push(`tag:${tag.id} `);

									value = words.join(' ');

									dispatch('input');
								}}
							>
								<div
									style="--dark-c:var(--color-gray-300); --c:var(--color-gray-700); --weight:500; --line-clamp:1; --fs:0"
								>
									{tag.name}
								</div>

								<div style="--c:var(--color-gray-500); --line-clamp:1">
									{tag.id}
								</div>
							</button>
						{/each}
					</div>
				{:else if filteredOptions.length > 0}
					<div
						style="--weight:500; --dark-c:var(--color-gray-300); --c:var(--color-gray-700); --mb:0.2rem"
					>
						{$i18n.t('Search options')}
					</div>

					<div style="--maxh:15rem; --of:auto">
						{#each filteredOptions as option, optionIdx}
							<button
								style="--px:0.4rem; --py:0.125rem; --d:flex; --g:0.2rem; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-900); --w:100%; --radius:0.2rem"
								class={selectedIdx === optionIdx ? 'bg-gray-100 dark:bg-gray-900' : ''}
								id="search-option-{optionIdx}"
								on:click|stopPropagation={async () => {
									const words = value.split(' ');

									words.pop();
									words.push('tag:');

									value = words.join(' ');

									dispatch('input');
								}}
							>
								<div
									style="--dark-c:var(--color-gray-300); --c:var(--color-gray-700); --weight:500"
								>
									{option.name}
								</div>

								<div style="--c:var(--color-gray-500); --line-clamp:1">
									{option.description}
								</div>
							</button>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
