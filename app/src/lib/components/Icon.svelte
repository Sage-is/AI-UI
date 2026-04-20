<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';

	export let name: string;
	export let className: string = 'size-4';
	export let strokeWidth: string = '1.5';
</script>

<svg
	class={className}
	aria-hidden="true"
	style="stroke-width: {strokeWidth}"
>
	<use href="{WEBUI_BASE_URL}/static/sprites/icons.svg#{name}" />
</svg>
