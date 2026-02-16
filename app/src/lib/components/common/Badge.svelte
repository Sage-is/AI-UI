<script lang="ts">
	export let type = 'info';
	export let content = '';

	const classNames: Record<string, string> = {
		info: 'bg-blue-500/20 text-blue-700 dark:text-blue-200 ',
		success: 'bg-green-500/20 text-green-700 dark:text-green-200',
		warning: 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-200',
		error: 'bg-red-500/20 text-red-700 dark:text-red-200',
		muted: 'bg-gray-500/20 text-gray-700 dark:text-gray-200'
	};
</script>

<div
	style="--size:0.75rem; --weight:700; --w:fit-content; --px:0.5rem; --radius:0.125rem; --tt:uppercase; --line-clamp:1; --mr:0.125rem"
	class="{classNames[type] ??
		classNames['info']}"
>
	{content}
</div>
