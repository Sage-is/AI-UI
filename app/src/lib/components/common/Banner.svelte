<script lang="ts">
	import type { Banner } from '$lib/types';
	import { onMount, createEventDispatcher } from 'svelte';
	import { fade } from 'svelte/transition';
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';
	import { WEBUI_BASE_URL } from '$lib/constants';

	const dispatch = createEventDispatcher();

	export let banner: Banner = {
		id: '',
		type: 'info',
		title: '',
		content: '',
		url: '',
		dismissable: true,
		timestamp: Math.floor(Date.now() / 1000)
	};
	export let className = 'mx-4';

	export let dismissed = false;

	let mounted = false;

	const classNames: Record<string, string> = {
		info: 'bg-blue-500/20 text-blue-700 dark:text-blue-200 ',
		success: 'bg-green-500/20 text-green-700 dark:text-green-200',
		warning: 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-200',
		error: 'bg-red-500/20 text-red-700 dark:text-red-200'
	};

	const dismiss = (id) => {
		dismissed = true;
		dispatch('dismiss', id);
	};

	onMount(() => {
		mounted = true;

		console.log('Banner mounted:', banner);
	});
</script>

{#if !dismissed}
	{#if mounted}
		<div
			style="--top:0; --left:0; --right:0; --p:0.5rem; --px:0.6rem; --d:flex; --jc:center; --ai:center; --pos:relative; --radius:0.6rem;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --c:var(--color-gray-800); --bgc:#fff; --dark-bgc:var(--color-gray-900); backdrop-filter:blur(24px); --z:30"
	class="{className} dark:text-gary-100"
			transition:fade={{ delay: 100, duration: 300 }}
		>
			<div style="--d:flex; --fd:column; --fd-md:row; --ai-md:center; --fx:1 1 0%; --size:0.875rem; --w:fit-content; --g:0.375rem">
				<div style="--d:flex; --jc:space-between; --as:flex-start">
					<div
						style="--size:0.6rem; --weight:700; --w:fit-content; --px:0.5rem; --radius:0.125rem; --tt:uppercase; --line-clamp:1; --mr:0.125rem"
	class="{classNames[banner.type] ??
							classNames['info']}"
					>
						{banner.type}
					</div>

					{#if banner.url}
						<div style="--d:flex; --d-md:none; --w:fit-content; --ai-md:center"
	class="group">
							<a
								style="--c:var(--color-gray-700); --dark-c:#fff; --size:0.6rem; --weight:600; --td:underline"
								href="{WEBUI_BASE_URL}/assets/files/whitepaper.pdf"
								target="_blank">Learn More</a
							>

							<div
								style="--ml:0.25rem; --c:var(--color-gray-400)"
	class="group-hover:text-gray-600 dark:group-hover:text-white"
							>
								<!--  -->
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									style="--w:1rem; --h:1rem"
								>
									<path
										fill-rule="evenodd"
										d="M4.22 11.78a.75.75 0 0 1 0-1.06L9.44 5.5H5.75a.75.75 0 0 1 0-1.5h5.5a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0V6.56l-5.22 5.22a.75.75 0 0 1-1.06 0Z"
										clip-rule="evenodd"
									/>
								</svg>
							</div>
						</div>
					{/if}
				</div>
				<div style="--fx:1 1 0%; --size:0.6rem; --c:var(--color-gray-700); --dark-c:#fff; --maxh:15rem; --ofy:auto">
					{@html marked.parse(DOMPurify.sanitize((banner?.content ?? '').replace(/\n/g, '<br>')))}
				</div>
			</div>

			{#if banner.url}
				<div style="--d:none; --d-md:flex; --w:fit-content; --ai-md:center"
	class="group">
					<a
						style="--c:var(--color-gray-700); --dark-c:#fff; --size:0.6rem; --weight:600; --td:underline"
						href="/"
						target="_blank">Learn More</a
					>

					<div style="--ml:0.25rem; --c:var(--color-gray-400)"
	class="group-hover:text-gray-600 dark:group-hover:text-white">
						<!--  -->
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							style="--w:1rem; --h:1rem"
						>
							<path
								fill-rule="evenodd"
								d="M4.22 11.78a.75.75 0 0 1 0-1.06L9.44 5.5H5.75a.75.75 0 0 1 0-1.5h5.5a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0V6.56l-5.22 5.22a.75.75 0 0 1-1.06 0Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
				</div>
			{/if}
			<div style="--d:flex; --as:flex-start">
				<button
					on:click={() => {
						dismiss(banner.id);
					}}
					style="--mt:-0.25rem; --mb:-0.5rem; --translatey:-1px; --ml:0.375rem; --mr:0.25rem; --c:var(--color-gray-400); --hvr-dark-c:#fff"
					>&times;</button
				>
			</div>
		</div>
	{/if}
{/if}
