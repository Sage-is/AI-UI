<script lang="ts">
	export let name: string;
	export let className: string = 'size-6';
</script>

<svg
	class={className}
	aria-hidden="true"
>
	<!-- Relative/same-origin on purpose — see Icon.svelte: an SVG <use> href must
	     match the frame origin, and Vite proxies /static to the backend in dev. -->
	<use href="/static/sprites/oauth.svg#{name}" />
</svg>
