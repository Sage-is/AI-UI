<script lang="ts">
	/**
	 * FormFieldRow - Reusable component for form field rows with consistent styling
	 * Replaces the repetitive pattern: div container + label + content area
	 */
	export let marginClass = 'mb-2.5'; // Allow customization of margin
	export let containerClass = 'flex w-full justify-between'; // Allow customization of container layout
</script>

<div class="{marginClass} {containerClass}">
	<div style="--as:center; --size:0.75rem; --weight:500">
		<slot name="label" />
	</div>
	<div style="--d:flex; --ai:center; --pos:relative">
		<slot name="content" />
	</div>
</div>
