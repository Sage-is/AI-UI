<script lang="ts">
	export let size = 'md';
</script>

<span style="--pos:relative; --d:flex; --mx:0.2rem"
	class="{size === 'md' ? 'size-3 my-2' : 'size-2 my-1'}">
	<span
		style="--pos:absolute; --d:inline-flex; --h:100%; --w:100%; animation:pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; --radius:9999px; --bgc:var(--color-gray-700); --dark-bgc:var(--color-gray-200); --op:0.75"
	></span>
	<span
		style="--pos:relative; --d:inline-flex; --radius:9999px; --bgc:#000; --dark-bgc:#fff"
	class="{size === 'md'
			? 'size-3'
			: 'size-2'} animate-size"
	></span>
</span>

<style>
	@keyframes size {
		0%,
		100% {
			transform: scale(1);
		}
		50% {
			transform: scale(1.25);
		}
	}

	.animate-size {
		animation: size 1.5s ease-in-out infinite;
	}
</style>
