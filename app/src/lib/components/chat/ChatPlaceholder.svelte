<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getBranding } from '$lib/apis/configs';
	import { marked } from 'marked';

	import { config, user, models as _models, temporaryChatEnabled } from '$lib/stores';
	import { onMount, getContext } from 'svelte';

	import { blur, fade } from 'svelte/transition';

	import Suggestions from './Suggestions.svelte';
	import { sanitizeResponseContent } from '$lib/utils';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';

	const i18n = getContext('i18n');

	export let modelIds = [];
	export let models = [];
	export let atSelectedModel;

	export let onSelect = (e) => {};

	let mounted = false;
	let selectedModelIdx = 0;
	let branding: { logo_url?: string; favicon_url?: string } = {};

	$: if (modelIds.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = modelIds.map((id) => $_models.find((m) => m.id === id));

	onMount(async () => {
		mounted = true;
		try {
			branding = await getBranding();
		} catch (err) {
			console.error('Failed to load branding:', err);
		}
	});
</script>

{#key mounted}
	<div style="--m:auto; --w:100%; --maxw:72rem; --px:2rem; --px-lg:5rem">
		<div style="--d:flex; --jc:flex-start">
			<div style="--d:flex; --g:-1rem; --mb:0.125rem" in:fade={{ duration: 200 }}>
				{#each models as model, modelIdx}
					<button
						on:click={() => {
							selectedModelIdx = modelIdx;
						}}
					>
						<Tooltip
							content={marked.parse(
								sanitizeResponseContent(
									models[selectedModelIdx]?.info?.meta?.description ?? ''
								).replaceAll('\n', '<br>')
							)}
							placement="right"
						>
							<img
								crossorigin="anonymous"
								src={model?.info?.meta?.profile_image_url ?? branding?.logo_url ?? `${WEBUI_BASE_URL}/static/icons/favicon.png`}
								style="--w:2.7rem; --h:2.7rem; --radius:9999px; --bc:1px; --bc:var(--color-gray-100, #ececec); --dark-bs:none"
								alt="logo"
								draggable="false"
							/>
						</Tooltip>
					</button>
				{/each}
			</div>
		</div>

		{#if $temporaryChatEnabled}
			<Tooltip
				content={$i18n.t("This chat won't appear in history and your messages will not be saved.")}
				className="w-full flex justify-start mb-0.5"
				placement="top"
			>
				<div style="--d:flex; --ai:center; --g:0.5rem; --c:var(--color-gray-500, #9b9b9b); --weight:500; --size:1.125rem; --mt:0.5rem; --w:fit-content">
					<EyeSlash strokeWidth="2.5" className="size-5" />{$i18n.t('Temporary Chat')}
				</div>
			</Tooltip>
		{/if}

		<div
			style="--mt:0.5rem; --mb:1rem; --size:1.875rem; --c:var(--color-gray-800, #333); --dark-c:var(--color-gray-100, #ececec); --weight:500; --ta:left; --d:flex; --ai:center; --g:1rem"
	class="font-primary"
		>
			<div>
				<div style="--tt:capitalize; --line-clamp:1" in:fade={{ duration: 200 }}>
					{#if models[selectedModelIdx]?.name}
						{models[selectedModelIdx]?.name}
					{:else}
						{$i18n.t('Hello, {{name}}', { name: $user?.name })}
					{/if}
				</div>

				<div in:fade={{ duration: 200, delay: 200 }}>
					{#if models[selectedModelIdx]?.info?.meta?.description ?? null}
						<div
							style="--mt:0.125rem; --size:1rem; --weight:400; --c:var(--color-gray-500, #9b9b9b); --dark-c:var(--color-gray-400, #b4b4b4); --line-clamp:3"
	class="markdown"
						>
							{@html marked.parse(
								sanitizeResponseContent(
									models[selectedModelIdx]?.info?.meta?.description
								).replaceAll('\n', '<br>')
							)}
						</div>
						{#if models[selectedModelIdx]?.info?.meta?.user}
							<div style="--mt:0.125rem; --size:0.875rem; --weight:400; --c:var(--color-gray-400, #b4b4b4); --dark-c:var(--color-gray-500, #9b9b9b)">
								By
								{#if models[selectedModelIdx]?.info?.meta?.user.community}
									<a href="https://sage.is/m/{models[selectedModelIdx]?.info?.meta?.user.username}"
										>{models[selectedModelIdx]?.info?.meta?.user.name
											? models[selectedModelIdx]?.info?.meta?.user.name
											: `@${models[selectedModelIdx]?.info?.meta?.user.username}`}</a
									>
								{:else}
									{models[selectedModelIdx]?.info?.meta?.user.name}
								{/if}
							</div>
						{/if}
					{:else}
						<div style="--weight:500; --c:var(--color-gray-400, #b4b4b4); --dark-c:var(--color-gray-500, #9b9b9b); --line-clamp:1"
	class="font-p">
							{$i18n.t('How can I help you today?')}
						</div>
					{/if}
				</div>
			</div>
		</div>

		<div style="--w:100%"
	class="font-primary" in:fade={{ duration: 200, delay: 300 }}>
			<Suggestions
				className="grid grid-cols-2"
				suggestionPrompts={atSelectedModel?.info?.meta?.suggestion_prompts ??
					models[selectedModelIdx]?.info?.meta?.suggestion_prompts ??
					$config?.default_prompt_suggestions ??
					[]}
				{onSelect}
			/>
		</div>
	</div>
{/key}
