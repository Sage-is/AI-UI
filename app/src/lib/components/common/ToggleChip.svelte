<script lang="ts">
	export let active = false;
	export let label = '';
</script>

<label style="--d:inline-flex; --ai:center; --g:0.375rem; --size:0.75rem; --cursor:pointer">
	<input
		type="checkbox"
		checked={active}
		on:change
		style="--cursor:pointer"
	/>
	{#if label}<span>{label}</span>{/if}
</label>
