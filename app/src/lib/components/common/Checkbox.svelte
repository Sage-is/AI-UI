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
	style="outline-style:solid; outline-offset:-1px; outline-color:1.5px; outline-color:var(--color-gray-200, #e3e3e3); outline-color:var(--color-gray-600, #676767); --c:#fff; --tn:all 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.125rem; --d:inline-block; --w:0.875rem; --h:0.875rem; --pos:relative"
	class="{state !==
	'unchecked'
		? 'bg-black outline-black '
		: 'hover:outline-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800'} {disabled
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
	<div style="--top:0; --left:0; --pos:absolute; --w:100%; --d:flex; --jc:center">
		{#if _state === 'checked'}
			<svg
				style="--w:0.875rem; --h:0.875rem"
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
				style="--w:0.75rem; --h:0.875rem; --c:var(--color-gray-800, #333); --dark-c:#fff"
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
