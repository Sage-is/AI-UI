<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';
	import { PaneGroup, Pane, PaneResizer } from 'paneforge';
	import { models, temporaryChatEnabled } from '$lib/stores';
	
	import ModelEditor from './ModelEditor.svelte';
	import ModelTestChat from './ModelTestChat.svelte';
	import EllipsisVertical from '$lib/components/icons/EllipsisVertical.svelte';
	import ChatBubbleOval from '$lib/components/icons/ChatBubbleOval.svelte';

	const i18n = getContext('i18n');

	export let onSubmit: Function;
	export let onBack: null | Function = null;
	export let model = null;
	export let edit = false;
	export let preset = true;

	let showChat = true; // Start with chat open by default
	let chatPane;
	let editorPane;
	
	// Reactive model data that updates as user edits
	let liveModelData = null;
	let modelEditor;

	// Initialize live model data
	$: if (model) {
		liveModelData = {
			...model,
			// Add temporary flag to indicate this is a test model
			_temporary: true,
			_test: true
		};
	}

	const toggleChat = () => {
		showChat = !showChat;
		// The pane is always visible now, we just show/hide the content
		// No need to resize the pane
	};

	const handleModelDataChange = (modelData) => {
		// Update live model data when editor changes
		liveModelData = {
			...modelData,
			_temporary: true,
			_test: true
		};
	};

	const handleSubmit = async (modelInfo) => {
		// Keep chat open after saving for continued testing
		// Don't close the chat anymore
		
		// Remove temporary flags before submitting
		const cleanModelInfo = { ...modelInfo };
		delete cleanModelInfo._temporary;
		delete cleanModelInfo._test;
		
		await onSubmit(cleanModelInfo);
		
		// Update live model data after successful save
		liveModelData = {
			...cleanModelInfo,
			_temporary: true,
			_test: true
		};
	};

	onMount(() => {
		// Initialize with chat open by default
		showChat = true;
	});
</script>

<div class="w-full h-full flex flex-col">
	<!-- Header with test chat toggle -->
	<div class="flex justify-between items-center p-4 border-b border-gray-100 dark:border-gray-850">
		<div class="flex items-center gap-2">
			{#if onBack}
				<button
					class="flex space-x-1"
					on:click={() => {
						onBack();
					}}
				>
					<div class="self-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="h-4 w-4"
						>
							<path
								fill-rule="evenodd"
								d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class="self-center text-sm font-medium">{$i18n.t('Back')}</div>
				</button>
			{/if}
		</div>
		
		<div class="flex items-center gap-2">
			<button
				class="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors
					{showChat 
						? 'bg-gray-900 text-white dark:bg-white dark:text-black' 
						: 'bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700'}"
				on:click={toggleChat}
			>
				<ChatBubbleOval className="size-4" />
				<span>{showChat ? $i18n.t('Hide Test Chat') : $i18n.t('Test Chat')}</span>
			</button>
			
			<!-- Add Back to Models button -->
			<a 
				href="/workshop/models"
				class="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700"
			>
				<span>{$i18n.t('Back to Models')}</span>
			</a>
		</div>
	</div>

	<!-- Split view content -->
	<div class="flex-1 min-h-0">
		<PaneGroup direction="horizontal" class="w-full h-full">
			<Pane bind:pane={editorPane} defaultSize={60} class="h-full flex relative max-w-full flex-col">
				<div class="h-full overflow-auto">
					<ModelEditor
						bind:this={modelEditor}
						{model}
						{edit}
						{preset}
						onSubmit={handleSubmit}
						onBack={null}
						on:dataChange={(e) => handleModelDataChange(e.detail)}
					/>
				</div>
			</Pane>

			<!-- Always show the chat pane (conditional removed) -->
			<PaneResizer class="relative flex w-2 items-center justify-center bg-background group">
				<div class="z-10 flex h-7 w-5 items-center justify-center rounded-xs">
					<EllipsisVertical className="size-4 invisible group-hover:visible" />
				</div>
			</PaneResizer>

			<Pane 
				bind:pane={chatPane} 
				defaultSize={40} 
				collapsible={true}
				onCollapse={() => {
					showChat = false;
				}}
				class="h-full flex relative max-w-full flex-col border-l border-gray-100 dark:border-gray-850"
			>
				{#if showChat}
					<ModelTestChat {liveModelData} />
				{:else}
					<!-- Show a collapsed state when chat is hidden -->
					<div class="flex items-center justify-center h-full bg-gray-50 dark:bg-gray-900">
						<button
							class="flex flex-col items-center gap-2 p-4 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
							on:click={toggleChat}
						>
							<ChatBubbleOval className="size-6" />
							<span class="text-sm">{$i18n.t('Show Test Chat')}</span>
						</button>
					</div>
				{/if}
			</Pane>
		</PaneGroup>
	</div>
</div>
