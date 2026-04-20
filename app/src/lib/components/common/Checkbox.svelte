<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';
	const dispatch = createEventDispatcher();

	export let state = 'unchecked';
	export let indeterminate = false;
	export let disabled = false;

	let _state = 'unchecked';

	$: _state = state;
</script>

<button
	style="--bw:1.5px; --bs:solid; --tn:all 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.2rem; --d:inline-block; --w:1rem; --h:1rem; --pos:relative; {state !== 'unchecked' ? '--bgc:#000; --bc:#000; --dark-bgc:#fff; --dark-bc:#fff; --dark-c:#000' : ''}"
	class="{disabled
		? 'opacity-50 cursor-not-allowed'
		: ''}"
	on:click={() => {
		if (disabled) return;

		if (_state === 'unchecked') {
			_state = 'checked';
			dispatch('change', _state);
		} else if (_state === 'checked') {
			_state = 'unchecked';
			if (!indeterminate) {
				dispatch('change', _state);
			}
		} else if (indeterminate) {
			_state = 'checked';
			dispatch('change', _state);
		}
	}}
	type="button"
	{disabled}
>
	<div style="--top:0; --left:0; --pos:absolute; --w:100%; --h:100%; --d:flex; --jc:center; --ai:center">
		{#if _state === 'checked'}
			<Icon name="checkbox-check" className="size-[0.6rem]" />
		{:else if indeterminate}
			<Icon name="minus" className="size-[0.6rem]" />
		{/if}
	</div>

	<!-- {checked} -->
</button>
