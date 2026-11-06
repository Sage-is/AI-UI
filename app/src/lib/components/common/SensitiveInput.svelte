<script context="module" lang="ts">
	// One id per mounted field: a page with several (OAuth, Documents, Audio)
	// shared a literal id, so every label pointed at the first input.
	let mounted = 0;
</script>

<script lang="ts">
	import { getContext } from 'svelte';
	const i18n: any = getContext('i18n');
	import { settings } from '$lib/stores';
	import Icon from '$lib/components/Icon.svelte';
	export let value: string = '';
	export let id = `sensitive-input-${++mounted}`;
	export let placeholder = '';
	export let required = true;
	export let readOnly = false;
	export let outerClassName = 'flex flex-1 bg-transparent';
	export let inputClassName = 'w-full text-sm py-0.5 bg-transparent';
	export let showButtonClassName = 'pl-1.5  transition bg-transparent';

	let show = false;

	const toggleShow = (e: Event) => {
		e.preventDefault();
		show = !show;
	};
</script>

<div class={outerClassName}>
	<label class="sr-only" for={id}>{placeholder || $i18n.t('Password')}</label>
	<input
		class={`${inputClassName} ${show ? '' : 'password'} ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : ' outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
		{placeholder}
		{id}
		bind:value
		required={required && !readOnly}
		disabled={readOnly}
		autocomplete="off"
		type="text"
	/>
	<button
		class={showButtonClassName}
		type="button"
		style="--d:flex; --ai:center; --p:0.2rem"
		aria-pressed={show}
		aria-label={$i18n.t('Make password visible in the user interface')}
		on:click={toggleShow}
	>
		{#if show}
			<Icon name="eye-slash-fill-16" className="size-4" />
		{:else}
			<Icon name="eye-fill-16" className="size-4" />
		{/if}
	</button>
</div>
