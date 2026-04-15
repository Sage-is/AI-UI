<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '../common/Modal.svelte';
	import Icon from '$lib/components/Icon.svelte';

	import Tooltip from '../common/Tooltip.svelte';
	const i18n = getContext('i18n');

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
	<div style="--c:var(--color-gray-700); --dark-c:var(--color-gray-100)">
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300); --px:1.2rem; --pt:1rem">
			<div style="--size:1.125rem; --weight:500; --as:center">{$i18n.t('Keyboard shortcuts')}</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<Icon name="x-mark" strokeWidth="2" className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --p:1.2rem; --p: 1rem 0;--bgc: var(--white); --br: 1rem">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<div style="--d:flex; --fd:column; --g:0.6rem; --w:100%; --as:flex-start">
					<!-- DRY: Use data structure to eliminate repetitive HTML -->
					{#each shortcuts as shortcut}
						<div style="--w:100%; --d:flex; --jc:space-between; --ai:center">
							<div style="--size:0.8rem">
								{#if shortcut.tooltip}
									<Tooltip content={$i18n.t(shortcut.tooltip)}>
										{$i18n.t(shortcut.label)}<span style="--size:0.6rem"> *</span>
									</Tooltip>
								{:else}
									{$i18n.t(shortcut.label)}
								{/if}
							</div>

							<div style="--d:flex; --g:0.2rem; --size:0.6rem">
								{#each shortcut.keys as key}
									<div
										style="--h:fit-content; --py:0.2rem; --px:0.5rem; --d:flex; --ai:center; --jc:center; --radius:0.125rem;  --bc:rgb(0 0 0 / 0.1); --tt:capitalize; --c:var(--color-gray-600); --dark-bc:rgb(255 255 255 / 0.1); --dark-c:var(--color-gray-300)"
									>
										{key}
									</div>
								{/each}
							</div>
						</div>
					{/each}
				</div>

				<!-- DRY: Second column using same pattern -->
				<div style="--d:flex; --fd:column; --g:0.6rem; --w:100%; --as:flex-start">
					{#each shortcutsColumn2 as shortcut}
						<div style="--w:100%; --d:flex; --jc:space-between; --ai:center">
							<div style="--size:0.8rem">
								{#if shortcut.tooltip}
									<Tooltip content={$i18n.t(shortcut.tooltip)}>
										{$i18n.t(shortcut.label)}<span style="--size:0.6rem"> *</span>
									</Tooltip>
								{:else}
									{$i18n.t(shortcut.label)}
								{/if}
							</div>

							<div style="--d:flex; --g:0.2rem; --size:0.6rem">
								{#each shortcut.keys as key}
									<div
										style="--h:fit-content; --py:0.2rem; --px:0.5rem; --d:flex; --ai:center; --jc:center; --radius:0.125rem;  --bc:rgb(0 0 0 / 0.1); --tt:capitalize; --c:var(--color-gray-600); --dark-bc:rgb(255 255 255 / 0.1); --dark-c:var(--color-gray-300)"
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

		<hr style="--bc:rgb(78 78 78 / 0.1); --dark-bc:rgb(205 205 205 / 0.3)" />

		<div style="--p:1.2rem">
			{$i18n.t(
				'Shortcuts are disabled while an input field is focused. Examples: chat input, search, etc.'
			)}
		</div>

		<hr style="--bc:rgb(78 78 78 / 0.1); --dark-bc:rgb(205 205 205 / 0.3)" />

		<div style="--p:1.2rem">
			<div style="--size:1.125rem; --weight:500; --as:center">{$i18n.t('Input commands')}</div>
			<div style="--mt:0.6rem; --d:flex; --fd:column; --g:0.6rem">
				<!-- DRY: Use data structure for input commands -->
				{#each inputCommands as command}
					<div style="--d:flex; --jc:space-between; --ai:center">
						<div style="--size:0.8rem; --c:var(--color-gray-500)">
							{$i18n.t(command.label)}
						</div>
						<div style="--c:var(--color-gray-600); --dark-c:var(--color-gray-300); --size:0.8rem; --weight:600">
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
