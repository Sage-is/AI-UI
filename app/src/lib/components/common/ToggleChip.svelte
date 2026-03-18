<script lang="ts">
	export let active = false;
	export let label = '';
</script>

<label style="--d:inline-flex; --ai:center; --g:0.4rem; --size:0.6rem; --cursor:pointer">
	<input
		type="checkbox"
		checked={active}
		on:change
		style="--cursor:pointer"
	/>
	{#if label}<span>{label}</span>{/if}
</label>
