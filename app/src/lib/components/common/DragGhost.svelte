<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	export let x;
	export let y;

	let popupElement = null;

	onMount(() => {
		document.body.appendChild(popupElement);
		document.body.style.overflow = 'hidden';
	});

	onDestroy(() => {
		document.body.removeChild(popupElement);
		document.body.style.overflow = 'unset';
	});
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->

<div
	bind:this={popupElement}
	style="--pos:fixed; --top:0; --left:0; --w:100vw; --h:100dvh; --z:50; touch-action:none; --pe:none"
>
	<div style="--pos:absolute; --c:#fff; --z:99999; top: {y + 10}px; left: {x + 10}px;">
		<slot></slot>
	</div>
</div>
