<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';
	import { PaneGroup, Pane, PaneResizer } from 'paneforge';
	import { models, temporaryChatEnabled } from '$lib/stores';
	import Icon from '$lib/components/Icon.svelte';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import ModelEditor from './ModelEditor.svelte';
	import ModelTestChat from './ModelTestChat.svelte';

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
	<div style="--d:none; --d-md:flex; --jc:space-between; --ai:center; --p:0.2rem;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)">
		<div style="--d:flex; --ai:center; --g:0.5rem">
			<button
				style="--radius:0.5rem; --d:flex; --fs:0; --ai:center; --jc:center; --pos:relative; --w:2rem; --h:2rem; --minw:2rem; --m:0"
				class="{liveModelData?.meta?.profile_image_url &&
				liveModelData.meta.profile_image_url !== `${WEBUI_BASE_URL}/static/icons/favicon.png`
					? 'bg-transparent'
					: 'bg-white'} group"
				type="button"
				on:click={() => {
					modelEditor?.triggerImageUpload();
				}}
				title="Change profile image"
			>
				<img
					src={liveModelData?.meta?.profile_image_url || model?.meta?.profile_image_url || `${WEBUI_BASE_URL}/static/icons/favicon.png`}
					alt="model profile"
					style="--radius:0.5rem; --w:2rem; --h:2rem; --objf:cover; --fs:0"
				/>
				<div
					style="--pos:absolute; --top:0; --bottom:0; --left:0; --right:0; --bgc:#fff; --dark-bgc:#000; --radius:0.5rem; --op:0; --tn:opacity 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					class="group-hover:opacity-20"
				></div>
			</button>

			{#if onBack}
				<button
					style="--d:flex; --g:0.2rem"
					on:click={() => {
						onBack();
					}}
				>
					<div style="--as:center">
						<Icon name="arrow-left-fill-20" className="size-4" />
					</div>
					<div style="--as:center; --size:0.8rem; --weight:500">{$i18n.t('Back')}</div>
				</button>
			{/if}
		</div>

		<div style="--d:flex; --ai:center; --g:0.5rem">
			<button
				style="--d:flex; --ai:center; --g:0.5rem; --px:0.6rem; --py:0.4rem; --size:0.8rem; --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{showChat
						? 'bg-gray-900 text-white dark:bg-white dark:text-black'
						: 'bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700'}"
				on:click={toggleChat}
			>
				<Icon name="chat-bubble-oval" className="size-4" />
				<span>{showChat ? $i18n.t('Hide Test Chat') : $i18n.t('Test Chat')}</span>
			</button>

			<!-- Add Back to Models button -->
			<a
				href="/workshop/models"
				style="--d:flex; --ai:center; --g:0.5rem; --px:0.6rem; --py:0.4rem; --size:0.8rem; --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke 150ms cubic-bezier(0.4, 0, 0.2, 1); --bgc:var(--color-gray-100); --hvr-bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700)"
			>
				<span>{$i18n.t('Back to Models')}</span>
			</a>
		</div>
	</div>

	<!-- Split view content -->
	<div style="--fx-lg:1 1 0%; --minh:0">
		<PaneGroup direction="horizontal" style="--w:100%; --h:100%">
			<Pane bind:pane={editorPane} style="--h:100%; --d:flex; --pos:relative; --maxw:100%; --fd:column">
				<div class="fade-scrollbar" style="--h:100%; --of:auto; --p:0.2rem">
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
			<PaneResizer style="--d:none; --d-md:flex; --pos:relative; --w:0.5rem; --ai:center; --jc:center; --m:0"
	class="bg-background group">
				<div style="--z:10; --d:flex; --h:1.75rem; --w:1.2rem; --ai:center; --jc:center"
	class="rounded-xs">
					<Icon name="ellipsis-vertical" className="size-4 invisible group-hover:visible" />
				</div>
			</PaneResizer>

			<Pane
				bind:pane={chatPane}
				defaultSize={40}
				collapsible={true}
				onCollapse={() => {
					showChat = false;
				}}
				style="
					--h:100%;
					--d:none; --d-md:flex;
					--pos:relative;
					--maxw:100%;
					--fd:column;
					--bl:1px solid;
					--bc:var(--color-gray-100);
					--dark-bc:var(--color-gray-850)"
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
							<Icon name="chat-bubble-oval" className="size-6" />
							<span style="--size:0.8rem">{$i18n.t('Show Test Chat')}</span>
						</button>
					</div>
				{/if}
			</Pane>
		</PaneGroup>
	</div>
</div>

<style>
	.fade-scrollbar {
		scrollbar-width: thin;
		scrollbar-color: transparent transparent;
		transition: scrollbar-color 0.3s ease;
	}
	.fade-scrollbar:hover,
	.fade-scrollbar:active {
		scrollbar-color: rgba(0, 0, 0, 0.3) transparent;
	}
	/* WebKit */
	.fade-scrollbar::-webkit-scrollbar {
		width: 6px;
	}
	.fade-scrollbar::-webkit-scrollbar-track {
		background: transparent;
	}
	.fade-scrollbar::-webkit-scrollbar-thumb {
		background: transparent;
		border-radius: 3px;
		transition: background 0.3s ease;
	}
	.fade-scrollbar:hover::-webkit-scrollbar-thumb,
	.fade-scrollbar:active::-webkit-scrollbar-thumb {
		background: rgba(0, 0, 0, 0.3);
	}
</style>
