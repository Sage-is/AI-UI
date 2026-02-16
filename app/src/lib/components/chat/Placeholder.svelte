<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { marked } from 'marked';

	import { onMount, getContext, tick, createEventDispatcher } from 'svelte';
	import { blur, fade } from 'svelte/transition';

	const dispatch = createEventDispatcher();

	import {
		config,
		user,
		models as _models,
		temporaryChatEnabled,
		selectedFolder,
		chats,
		currentChatPage
	} from '$lib/stores';
	import { sanitizeResponseContent, extractCurlyBraceWords } from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getBranding } from '$lib/apis/configs';

	import Suggestions from './Suggestions.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import MessageInput from './MessageInput.svelte';
	import FolderPlaceholder from './Placeholder/FolderPlaceholder.svelte';
	import FolderTitle from './Placeholder/FolderTitle.svelte';
	import { getChatList } from '$lib/apis/chats';

	const i18n = getContext('i18n');

	export let transparentBackground = false;

	export let createMessagePair: Function;
	export let stopResponse: Function;

	export let autoScroll = false;

	export let atSelectedModel: Model | undefined;
	export let selectedModels: [''];

	export let history;

	export let prompt = '';
	export let files = [];
	export let messageInput = null;

	export let selectedToolIds = [];
	export let selectedFilterIds = [];

	export let showCommands = false;

	export let imageGenerationEnabled = false;
	export let codeInterpreterEnabled = false;
	export let webSearchEnabled = false;

	export let onSelect = (e) => {};

	export let toolServers = [];

	let models = [];

	let branding: { logo_url?: string; favicon_url?: string } = {};
	let selectedModelIdx = 0;

	$: if (selectedModels.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = selectedModels.map((id) => $_models.find((m) => m.id === id));

	onMount(async () => {
		try {
			branding = await getBranding();
		} catch (err) {
			console.error('Failed to load branding:', err);
		}
	});
</script>

<div style="--m:auto; --w:100%; --maxw:72rem; --px:0.5rem; --translatey:1.5rem; --py:6rem; --ta:center"
	class="@2xl:px-20">
	{#if $temporaryChatEnabled}
		<Tooltip
			content={$i18n.t("This chat won't appear in history and your messages will not be saved.")}
			className="w-full flex justify-center mb-0.5"
			placement="top"
		>
			<div style="--d:flex; --ai:center; --g:0.5rem; --c:var(--color-gray-500, #9b9b9b); --weight:500; --size:1.125rem; --my:0.5rem; --w:fit-content">
				<EyeSlash strokeWidth="2.5" className="size-5" />{$i18n.t('Temporary Chat')}
			</div>
		</Tooltip>
	{/if}

	<div
		style="--w:100%; --size:1.875rem; --c:var(--color-gray-800, #333); --dark-c:var(--color-gray-100, #ececec); --ta:center; --d:flex; --ai:center; --g:1rem"
	class="font-primary"
	>
		<div style="--w:100%; --d:flex; --fd:column; --jc:center; --ai:center">
			{#if $selectedFolder}
				<FolderTitle
					folder={$selectedFolder}
					onUpdate={async (folder) => {
						selectedFolder.set(folder);

						await chats.set(await getChatList(localStorage.token, $currentChatPage));
						currentChatPage.set(1);
					}}
					onDelete={async () => {
						await chats.set(await getChatList(localStorage.token, $currentChatPage));
						currentChatPage.set(1);

						selectedFolder.set(null);
					}}
				/>
			{:else}
				<div style="--d:flex; --fd:row; --jc:center; --g:0.75rem; --w:fit-content; --px:1.25rem; --maxw:36rem"
	class="@sm:gap-3.5">
					<div style="--d:flex; --fs:0; --jc:center">
						<div style="--d:flex; --g:-1rem; --mb:0.125rem" in:fade={{ duration: 100 }}>
							{#each models as model, modelIdx}
								<Tooltip
									content={(models[modelIdx]?.info?.meta?.tags ?? [])
										.map((tag) => tag.name.toUpperCase())
										.join(', ')}
									placement="top"
								>
									<button
										aria-hidden={models.length <= 1}
										aria-label={$i18n.t('Get information on {{name}} in the UI', {
											name: models[modelIdx]?.name
										})}
										on:click={() => {
											selectedModelIdx = modelIdx;
										}}
									>
										<img
											crossorigin="anonymous"
											src={model?.info?.meta?.profile_image_url ?? branding?.logo_url ?? `${WEBUI_BASE_URL}/static/icons/favicon.png`}
											style="--w:2.25rem; --h:2.25rem; --radius:9999px; --bc:1px; --bc:var(--color-gray-100, #ececec); --dark-bs:none"
	class="@sm:size-10"
											aria-hidden="true"
											draggable="false"
										/>
									</button>
								</Tooltip>
							{/each}
						</div>
					</div>

					<div
						style="--size:1.875rem; --line-clamp:1; --d:flex; --ai:center"
	class="@sm:text-3xl"
						in:fade={{ duration: 100 }}
					>
						{#if models[selectedModelIdx]?.name}
							<Tooltip
								content={models[selectedModelIdx]?.name}
								placement="top"
								className=" flex items-center "
							>
								<span style="--line-clamp:1">
									{models[selectedModelIdx]?.name}
								</span>
							</Tooltip>
						{:else}
							{$i18n.t('Hello, {{name}}', { name: $user?.name })}
						{/if}
					</div>
				</div>

				<div style="--d:flex; --mt:0.25rem; --mb:0.5rem">
					<div in:fade={{ duration: 100, delay: 50 }}>
						{#if models[selectedModelIdx]?.info?.meta?.description ?? null}
							<Tooltip
								className=" w-fit"
								content={marked.parse(
									sanitizeResponseContent(
										models[selectedModelIdx]?.info?.meta?.description ?? ''
									).replaceAll('\n', '<br>')
								)}
								placement="top"
							>
								<div
									style="--mt:0.125rem; --px:0.5rem; --size:0.875rem; --weight:400; --c:var(--color-gray-500, #9b9b9b); --dark-c:var(--color-gray-400, #b4b4b4); --line-clamp:2; --maxw:36rem"
	class="markdown"
								>
									{@html marked.parse(
										sanitizeResponseContent(
											models[selectedModelIdx]?.info?.meta?.description ?? ''
										).replaceAll('\n', '<br>')
									)}
								</div>
							</Tooltip>

							{#if models[selectedModelIdx]?.info?.meta?.user}
								<div style="--mt:0.125rem; --size:0.875rem; --weight:400; --c:var(--color-gray-400, #b4b4b4); --dark-c:var(--color-gray-500, #9b9b9b)">
									By
									{#if models[selectedModelIdx]?.info?.meta?.user.community}
										<a
											href="https://sage.is/m/{models[selectedModelIdx]?.info?.meta?.user
												.username}"
											>{models[selectedModelIdx]?.info?.meta?.user.name
												? models[selectedModelIdx]?.info?.meta?.user.name
												: `@${models[selectedModelIdx]?.info?.meta?.user.username}`}</a
										>
									{:else}
										{models[selectedModelIdx]?.info?.meta?.user.name}
									{/if}
								</div>
							{/if}
						{/if}
					</div>
				</div>
			{/if}

			<div style="--size:1rem; --weight:400; --w:100%; --py:0.75rem"
	class="@md:max-w-3xl {atSelectedModel ? 'mt-2' : ''}">
				<MessageInput
					bind:this={messageInput}
					{history}
					{selectedModels}
					bind:files
					bind:prompt
					bind:autoScroll
					bind:selectedToolIds
					bind:selectedFilterIds
					bind:imageGenerationEnabled
					bind:codeInterpreterEnabled
					bind:webSearchEnabled
					bind:atSelectedModel
					bind:showCommands
					{toolServers}
					{transparentBackground}
					{stopResponse}
					{createMessagePair}
					placeholder={$i18n.t('How can I help you today?')}
					onChange={(input) => {
						if (!$temporaryChatEnabled) {
							if (input.prompt !== null) {
								sessionStorage.setItem(`chat-input`, JSON.stringify(input));
							} else {
								sessionStorage.removeItem(`chat-input`);
							}
						}
					}}
					on:upload={(e) => {
						dispatch('upload', e.detail);
					}}
					on:submit={(e) => {
						dispatch('submit', e.detail);
					}}
				/>
			</div>
		</div>
	</div>

	{#if $selectedFolder}
		<div
			style="--mx:auto; --px:1rem; --maxw-md:48rem; --px-md:1.5rem; --minh:15.5rem"
	class="font-primary"
			in:fade={{ duration: 200, delay: 200 }}
		>
			<FolderPlaceholder folder={$selectedFolder} />
		</div>
	{:else}
		<div style="--mx:auto; --maxw:42rem; --mt:0.5rem"
	class="font-primary" in:fade={{ duration: 200, delay: 200 }}>
			<div style="--mx:1.25rem">
				<Suggestions
					suggestionPrompts={atSelectedModel?.info?.meta?.suggestion_prompts ??
						models[selectedModelIdx]?.info?.meta?.suggestion_prompts ??
						$config?.default_prompt_suggestions ??
						[]}
					inputValue={prompt}
					{onSelect}
				/>
			</div>
		</div>
	{/if}
</div>
