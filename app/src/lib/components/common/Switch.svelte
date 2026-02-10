<script lang="ts">
	import { createEventDispatcher, tick } from 'svelte';
	import { Switch } from 'bits-ui';
	import { settings } from '$lib/stores';
	export let state = true;
	export let id = '';

	const dispatch = createEventDispatcher();

	$: dispatch('change', state);
</script>

<Switch.Root
	bind:checked={state}
	{id}
	style="--d:flex; --w: 1.8rem; --h:calc(var(--w) / 1.8); --cur: pointer; --shadow-inset:6;
		{($settings?.highContrastMode ?? false)
			? '--bg: #047857; --bg: #000; --b: 0.2em solid #666666;'
			: ''} {state ? '--bg: #10b981; --b: #10b981;' : '--bg: #e5e7eb;'}"
>
	<Switch.Thumb
	    style="--shadow: 4; {($settings?.highContrastMode ?? false) ? '--b: 0.2em solid #000;' : ''};"
		class="pointer-events-none block size-4 
			shrink-0 rounded-full bg-white 
			transition-transform 
			data-[state=checked]:translate-x-3.5 
			data-[state=unchecked]:translate-x-0 
			data-[state=unchecked]:shadow-mini "
	/>
</Switch.Root>
