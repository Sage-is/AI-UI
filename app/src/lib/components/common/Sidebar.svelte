<script lang="ts">
	import { fade, slide } from 'svelte/transition';

	export let show = false;
	export let side = 'right';
	export let width = '200px';

	export let className = '';
	export let duration = 100;
</script>

{#if show}
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		style="--pos:absolute; --z:20; --top:0; --right:0; --left:0; --bottom:0; --bgc:rgb(255 255 255 / 0.2); --dark-bgc:rgb(0 0 0 / 0.05); --w:100%; --minh:100%; --h:100%; --d:flex; --jc:center; --of:hidden; overscroll-behavior:contain"
		on:mousedown={() => {
			show = false;
		}}
		transition:fade={{ duration: duration }}
	/>

	<div
		style="--pos:absolute; --z:30; --shadow:5; --top:0; --bottom:0"
	class="{side === 'right' ? 'right-0' : 'left-0'}"
		transition:slide={{ duration: duration, axis: side === 'right' ? 'x' : 'y' }}
	>
		<div class="{className}" style="--h:100%; width: {show ? width : '0px'}">
			<slot />
		</div>
	</div>
{/if}
