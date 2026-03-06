<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	export let state = 'unchecked';
	export let indeterminate = false;
	export let disabled = false;

	let _state = 'unchecked';

	$: _state = state;
</script>

<button
	style="--bw:1.5px; --bs:solid; --bc:var(--color-gray-300); --dark-bc:var(--color-gray-600); --c:#fff; --tn:all 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.25rem; --d:inline-block; --w:1rem; --h:1rem; --pos:relative; {state !== 'unchecked' ? '--bgc:#000; --bc:#000; --dark-bgc:#fff; --dark-bc:#fff; --dark-c:#000' : ''}"
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
			<svg
				style="--w:0.75rem; --h:0.75rem"
				aria-hidden="true"
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
			>
				<path
					stroke="currentColor"
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="3"
					d="m5 12 4.7 4.5 9.3-9"
				/>
			</svg>
		{:else if indeterminate}
			<svg
				style="--w:0.75rem; --h:0.875rem; --c:var(--color-gray-800); --dark-c:#fff"
				aria-hidden="true"
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
			>
				<path
					stroke="currentColor"
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="3"
					d="M5 12h14"
				/>
			</svg>
		{/if}
	</div>

	<!-- {checked} -->
</button>
