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

<div style="--w:100%; --h:100%; --d:flex; --fd:column">
	<!-- Header with test chat toggle -->
	<div style="--d:flex; --jc:space-between; --ai:center; --p:1rem; --bb:1px solid; --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)">
		<div style="--d:flex; --ai:center; --g:0.5rem">
			{#if onBack}
				<button
					style="--d:flex; --g:0.25rem"
					on:click={() => {
						onBack();
					}}
				>
					<div style="--as:center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							style="--h:1rem; --w:1rem"
						>
							<path
								fill-rule="evenodd"
								d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div style="--as:center; --size:0.875rem; --weight:500">{$i18n.t('Back')}</div>
				</button>
			{/if}
		</div>
		
		<div style="--d:flex; --ai:center; --g:0.5rem">
			<button
				style="--d:flex; --ai:center; --g:0.5rem; --px:0.75rem; --py:0.375rem; --size:0.875rem; --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{showChat 
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
				style="--d:flex; --ai:center; --g:0.5rem; --px:0.75rem; --py:0.375rem; --size:0.875rem; --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke 150ms cubic-bezier(0.4, 0, 0.2, 1); --bgc:var(--color-gray-100); --hvr-bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700)"
			>
				<span>{$i18n.t('Back to Models')}</span>
			</a>
		</div>
	</div>

	<!-- Split view content -->
	<div style="--fx:1 1 0%; --minh:0">
		<PaneGroup direction="horizontal" style="--w:100%; --h:100%">
			<Pane bind:pane={editorPane} defaultSize={60} style="--h:100%; --d:flex; --pos:relative; --maxw:100%; --fd:column">
				<div style="--h:100%; --of:auto">
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
			<PaneResizer style="--pos:relative; --d:flex; --w:0.5rem; --ai:center; --jc:center"
	class="bg-background group">
				<div style="--z:10; --d:flex; --h:1.75rem; --w:1.25rem; --ai:center; --jc:center"
	class="rounded-xs">
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
				style="--h:100%; --d:flex; --pos:relative; --maxw:100%; --fd:column; --bl:1px solid; --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
			>
				{#if showChat}
					<ModelTestChat {liveModelData} />
				{:else}
					<!-- Show a collapsed state when chat is hidden -->
					<div style="--d:flex; --ai:center; --jc:center; --h:100%; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-900)">
						<button
							style="--d:flex; --fd:column; --ai:center; --g:0.5rem; --p:1rem; --c:var(--color-gray-500); --hvr-c:var(--color-gray-700); --hvr-dark-c:var(--color-gray-300); --tn:color, background-color, border-color, text-decoration-color, fill, stroke 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							on:click={toggleChat}
						>
							<ChatBubbleOval className="size-6" />
							<span style="--size:0.875rem">{$i18n.t('Show Test Chat')}</span>
						</button>
					</div>
				{/if}
			</Pane>
		</PaneGroup>
	</div>
</div>
