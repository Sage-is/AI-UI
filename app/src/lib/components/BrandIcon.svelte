<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';

	export let name: string;
	export let className: string = 'size-6';
</script>

<svg
	class={className}
	aria-hidden="true"
>
	<use href="{WEBUI_BASE_URL}/static/sprites/oauth.svg#{name}" />
</svg>
