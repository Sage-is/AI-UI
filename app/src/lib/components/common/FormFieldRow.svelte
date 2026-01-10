<script lang="ts">
	/**
	 * FormFieldRow - Reusable component for form field rows with consistent styling
	 * Replaces the repetitive pattern: div container + label + content area
	 */
	export let marginClass = 'mb-2.5'; // Allow customization of margin
	export let containerClass = 'flex w-full justify-between'; // Allow customization of container layout
</script>

<div class="{marginClass} {containerClass}">
	<div class="self-center text-xs font-medium">
		<slot name="label" />
	</div>
	<div class="flex items-center relative">
		<slot name="content" />
	</div>
</div>
