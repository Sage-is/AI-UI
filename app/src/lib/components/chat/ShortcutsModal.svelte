<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '../common/Modal.svelte';

	import Tooltip from '../common/Tooltip.svelte';
	const i18n = getContext('i18n');
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;

	// DRY: Define shortcuts data structure to eliminate repetitive HTML
	const shortcuts = [
		{
			label: 'Open new chat',
			keys: ['Ctrl/⌘', 'Shift', 'O']
		},
		{
			label: 'Focus chat input',
			keys: ['Shift', 'Esc']
		},
		{
			label: 'Stop Generating',
			keys: ['Esc'],
			tooltip: 'Only active when the chat input is in focus and an LLM is generating a response.'
		},
		{
			label: 'Copy last code block',
			keys: ['Ctrl/⌘', 'Shift', ';']
		},
		{
			label: 'Copy last response',
			keys: ['Ctrl/⌘', 'Shift', 'C']
		},
		{
			label: 'Prevent file creation',
			keys: ['Ctrl/⌘', 'Shift', 'V'],
			tooltip: 'Only active when "Paste Large Text as File" setting is toggled on.'
		}
	];

	const shortcutsColumn2 = [
		{
			label: 'Generate prompt pair',
			keys: ['Ctrl/⌘', 'Shift', 'Enter']
		},
		{
			label: 'Toggle search',
			keys: ['Ctrl/⌘', 'K']
		},
		{
			label: 'Toggle settings',
			keys: ['Ctrl/⌘', '.']
		},
		{
			label: 'Toggle sidebar',
			keys: ['Ctrl/⌘', 'Shift', 'S']
		},
		{
			label: 'Delete chat',
			keys: ['Ctrl/⌘', 'Shift', '⌫/Delete']
		},
		{
			label: 'Show shortcuts',
			keys: ['Ctrl/⌘', '/']
		}
	];

	const inputCommands = [
		{
			label: 'Attach file from knowledge',
			command: '#'
		},
		{
			label: 'Add custom prompt',
			command: '/'
		},
		{
			label: 'Talk to model',
			command: '@'
		},
		{
			label: 'Accept autocomplete generation / Jump to prompt variable',
			command: 'Tab'
		}
	];

	// DRY: Reusable shortcut component function
	function renderShortcut(shortcut) {
		return {
			label: shortcut.label,
			keys: shortcut.keys,
			tooltip: shortcut.tooltip
		};
	}
</script>

<Modal bind:show>
	<div class="text-gray-700 dark:text-gray-100">
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4">
			<div class=" text-lg font-medium self-center">{$i18n.t('Keyboard shortcuts')}</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full p-5 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<div class="flex flex-col space-y-3 w-full self-start">
					<!-- DRY: Use data structure to eliminate repetitive HTML -->
					{#each shortcuts as shortcut}
						<div class="w-full flex justify-between items-center">
							<div class="text-sm">
								{#if shortcut.tooltip}
									<Tooltip content={$i18n.t(shortcut.tooltip)}>
										{$i18n.t(shortcut.label)}<span class="text-xs"> *</span>
									</Tooltip>
								{:else}
									{$i18n.t(shortcut.label)}
								{/if}
							</div>

							<div class="flex space-x-1 text-xs">
								{#each shortcut.keys as key}
									<div
										class="h-fit py-1 px-2 flex items-center justify-center rounded-sm border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
									>
										{key}
									</div>
								{/each}
							</div>
						</div>
					{/each}
				</div>

				<!-- DRY: Second column using same pattern -->
				<div class="flex flex-col space-y-3 w-full self-start">
					{#each shortcutsColumn2 as shortcut}
						<div class="w-full flex justify-between items-center">
							<div class="text-sm">
								{#if shortcut.tooltip}
									<Tooltip content={$i18n.t(shortcut.tooltip)}>
										{$i18n.t(shortcut.label)}<span class="text-xs"> *</span>
									</Tooltip>
								{:else}
									{$i18n.t(shortcut.label)}
								{/if}
							</div>

							<div class="flex space-x-1 text-xs">
								{#each shortcut.keys as key}
									<div
										class="h-fit py-1 px-2 flex items-center justify-center rounded-sm border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
									>
										{key}
									</div>
								{/each}
							</div>
						</div>
					{/each}
				</div>
			</div>
		</div>

		<hr class=" border-gray-700/10 dark:border-gray-300/30" />

		<div class="p-5">
			{$i18n.t(
				'Shortcuts are disabled while an input field is focused. Examples: chat input, search, etc.'
			)}
		</div>

		<hr class="border-gray-700/10 dark:border-gray-300/30" />

		<div class="p-5">
			<div class=" text-lg font-medium self-center">{$i18n.t('Input commands')}</div>
			<div class=" mt-3 flex flex-col space-y-3">
				<!-- DRY: Use data structure for input commands -->
				{#each inputCommands as command}
					<div class="flex justify-between items-center">
						<div class=" text-sm text-gray-500">
							{$i18n.t(command.label)}
						</div>
						<div class="text-gray-600 dark:text-gray-300 text-sm font-semibold">
							{command.command}
						</div>
					</div>
				{/each}
			</div>
		</div>
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		/* display: none; <- Crashes Chrome on hover */
		-webkit-appearance: none;
		margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
	}

	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}

	input[type='number'] {
		-moz-appearance: textfield; /* Firefox */
	}
</style>
