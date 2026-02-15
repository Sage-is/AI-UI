<script>
	export let items = [];
</script>

<div class="flex flex-col md:flex-row gap-4 p-4 md:p-6 lg:p-8">
	{#each items as item}
		<div class="w-full md:w-1/2 lg:w-1/3 bg-white rounded-xl shadow-sm p-4">
			<h3 class="text-lg md:text-xl font-semibold text-gray-800">{item.title}</h3>
			<p class="text-sm text-gray-600 mt-2 line-clamp-2">{item.description}</p>
		</div>
	{/each}
</div>

<div class="hidden md:flex lg:hidden items-center justify-between px-4">
	<span class="text-xs text-gray-400">Responsive content</span>
</div>
