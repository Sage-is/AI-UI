<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import type { Branding } from '$lib/apis/configs';

	export let className = 'size-8';
	export let src = `${WEBUI_BASE_URL}/static/icons/favicon.png`;
	export let branding: Branding | null = null;

	$: defaultImage = branding?.logo_url ?? `${WEBUI_BASE_URL}/static/icons/favicon.png`;
</script>

<img
	crossorigin="anonymous"
	src={src === ''
		? defaultImage
		: src.startsWith(WEBUI_BASE_URL) ||
			  src.startsWith('https://www.gravatar.com/avatar/') ||
			  src.startsWith('data:') ||
			  src.startsWith('/')
			? src
			: `${WEBUI_BASE_URL}/static/user.png`}
	style="--objf:cover; --radius:9999px"
	class="{className}"
	alt="profile"
	draggable="false"
/>
