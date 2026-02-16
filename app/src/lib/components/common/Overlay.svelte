<script>
	import Spinner from './Spinner.svelte';

	export let show = false;
	export let content = '';

	export let opacity = 1;
</script>

<div style="--pos:relative">
	{#if show}
		<div style="--pos:absolute; --w:100%; --h:100%; --d:flex">
			<div
				style="--pos:absolute; --radius:0.125rem; inset: -10px; opacity: {opacity}; backdrop-filter: blur(5px);"
			/>

			<div style="--d:flex; --w:100%; --fd:column; --jc:center">
				<div style="--py:0.75rem">
					<Spinner className="ml-2" />
				</div>

				{#if content !== ''}
					<div style="--ta:center; --c:var(--color-gray-100, #ececec); --size:0.75rem; --weight:500; --z:50">
						{content}
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<slot />
</div>
