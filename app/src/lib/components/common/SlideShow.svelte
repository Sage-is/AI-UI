<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { onMount } from 'svelte';

	export let imageUrls = [
		`${WEBUI_BASE_URL}/static/assets/images/adam.jpg`,
		`${WEBUI_BASE_URL}/static/assets/images/galaxy.jpg`,
		`${WEBUI_BASE_URL}/static/assets/images/earth.jpg`,
		`${WEBUI_BASE_URL}/static/assets/images/space.jpg`
	];
	export let duration = 5000;
	let selectedImageIdx = 0;

	onMount(() => {
		setInterval(() => {
			selectedImageIdx = (selectedImageIdx + 1) % (imageUrls.length - 1);
		}, duration);
	});
</script>

{#each imageUrls as imageUrl, idx (idx)}
	<div
		class="image bg-cover bg-center"
		style="--w:100%; --h:100%; --pos:absolute; --top:0; --left:0; --tn:opacity 150ms cubic-bezier(0.4, 0, 0.2, 1); --tdn:1000ms; opacity: {selectedImageIdx === idx ? 1 : 0}; background-image: url('{imageUrl}')"
	></div>
{/each}

<style>
	.image {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background-size: cover;
		background-position: center; /* Center the background images */
		transition: opacity 1s ease-in-out; /* Smooth fade effect */
		opacity: 0; /* Make images initially not visible */
	}
</style>
