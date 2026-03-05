<script>
	export let isActive = false;
	export let variant = 'primary';
	export let size = 'md';
</script>

<button
	class="flex items-center gap-2 rounded-lg cursor-pointer text-sm font-medium
		{isActive ? 'bg-gray-100 dark:bg-gray-800' : ''}
		{size === 'lg' ? 'px-4 py-3 text-base' : 'px-3 py-2 text-sm'}
		hover:bg-gray-50 dark:hover:bg-gray-700 transition"
>
	<slot />
</button>

<div class="absolute top-0 right-0 z-50 {isActive ? 'visible' : 'invisible'}">
	<span class="text-xs text-gray-500 uppercase font-semibold">Label</span>
</div>
