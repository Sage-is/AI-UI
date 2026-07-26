<script lang="ts">
	export let name: string;
	export let className: string = 'size-4';
	export let strokeWidth: string = '1.5';
</script>

<svg
	class={className}
	aria-hidden="true"
	style="stroke-width: {strokeWidth}"
>
	<!-- Same-origin, relative on purpose: an SVG <use> href must match the frame's origin. In dev the frontend is :5173 and Vite proxies /static to the :8080 backend; prefixing WEBUI_BASE_URL (http://localhost:8080 in dev) made the ref cross-origin and the browser blocked it. In prod WEBUI_BASE_URL is '' so this is identical output. -->
	<use href="/static/sprites/icons.svg#{name}" />
</svg>
