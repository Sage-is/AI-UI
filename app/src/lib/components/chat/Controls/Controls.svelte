<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import AdvancedParams from '../Settings/Advanced/AdvancedParams.svelte';
	import Valves from '$lib/components/chat/Controls/Valves.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	import { user, settings } from '$lib/stores';
	export let models = [];
	export let chatFiles = [];
	export let params = {};

	let showValves = false;
</script>

<div style="--dark-c:#fff">
	<div style="--d:flex; --ai:center; --jc:space-between; --dark-c:var(--color-gray-100); --mb:0.5rem">
		<div style="--size:1.125rem; --weight:500; --as:center"
	class="font-primary">{$i18n.t('Chat Controls')}</div>
		<button
			style="--as:center"
			on:click={() => {
				dispatch('close');
			}}
		>
			<XMark className="size-3.5" />
		</button>
	</div>

	<div style="--dark-c:var(--color-gray-200); --size:0.8rem; --py:0.125rem; --px:0.125rem"
	class="font-primary">
		{#if chatFiles.length > 0}
			<Collapsible title={$i18n.t('Files')} open={true} buttonClassName="w-full">
				<div style="--d:flex; --fd:column; --g:0.2rem; --mt:0.4rem" slot="content">
					{#each chatFiles as file, fileIdx}
						<FileItem
							className="w-full"
							item={file}
							edit={true}
							url={file?.url ? file.url : null}
							name={file.name}
							type={file.type}
							size={file?.size}
							dismissible={true}
							on:dismiss={() => {
								// Remove the file from the chatFiles array

								chatFiles.splice(fileIdx, 1);
								chatFiles = chatFiles;
							}}
							on:click={() => {
								console.log(file);
							}}
						/>
					{/each}
				</div>
			</Collapsible>

			<hr style="--my:0.5rem; --bc:var(--color-gray-50); --dark-bc:rgb(78 78 78 / 0.1)" />
		{/if}

		<Collapsible bind:open={showValves} title={$i18n.t('Valves')} buttonClassName="w-full">
			<div style="--size:0.8rem" slot="content">
				<Valves show={showValves} />
			</div>
		</Collapsible>

		{#if $user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true)}
			<hr style="--my:0.5rem; --bc:var(--color-gray-50); --dark-bc:rgb(78 78 78 / 0.1)" />

			<Collapsible title={$i18n.t('System Prompt')} open={true} buttonClassName="w-full">
				<div class="" slot="content">
					<textarea
						bind:value={params.system}
						style="--w:100%; --size:0.6rem; --oe:none"
	class="resize-vertical {$settings.highContrastMode
							? 'border-2 border-gray-300 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5'
							: 'py-1.5 bg-transparent'}"
						rows="4"
						placeholder={$i18n.t('Enter system prompt')}
					/>
				</div>
			</Collapsible>
		{/if}

		{#if $user?.role === 'admin' || ($user?.permissions.chat?.controls ?? true)}
			<hr style="--my:0.5rem; --bc:var(--color-gray-50); --dark-bc:rgb(78 78 78 / 0.1)" />

			<Collapsible title={$i18n.t('Advanced Params')} open={true} buttonClassName="w-full">
				<div style="--size:0.8rem; --mt:0.4rem" slot="content">
					<div>
						<AdvancedParams admin={$user?.role === 'admin'} custom={true} bind:params />
					</div>
				</div>
			</Collapsible>
		{/if}
	</div>
</div>
