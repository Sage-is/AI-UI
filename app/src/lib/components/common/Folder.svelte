<script lang="ts">
	import { getContext, createEventDispatcher, onMount, onDestroy } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import ChevronDown from '../icons/ChevronDown.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Collapsible from './Collapsible.svelte';
	import Tooltip from './Tooltip.svelte';
	import Plus from '../icons/Plus.svelte';

	export let open = true;

	export let id = '';
	export let name = '';
	export let collapsible = true;

	export let onAddLabel: string = '';
	export let onAdd: null | Function = null;

	export let dragAndDrop = true;

	export let className = '';

	let folderElement;

	let draggedOver = false;

	const onDragOver = (e) => {
		e.preventDefault();
		e.stopPropagation();
		draggedOver = true;
	};

	const onDrop = (e) => {
		e.preventDefault();
		e.stopPropagation();

		if (folderElement.contains(e.target)) {
			console.log('Dropped on the Button');

			if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
				// Iterate over all items in the DataTransferItemList use functional programming
				for (const item of Array.from(e.dataTransfer.items)) {
					// If dropped items aren't files, reject them
					if (item.kind === 'file') {
						const file = item.getAsFile();
						if (file && file.type === 'application/json') {
							console.log('Dropped file is a JSON file!');

							// Read the JSON file with FileReader
							const reader = new FileReader();
							reader.onload = async function (event) {
								try {
									const fileContent = JSON.parse(event.target.result);
									console.log('Parsed JSON Content: ', fileContent);
									open = true;
									dispatch('import', fileContent);
								} catch (error) {
									console.error('Error parsing JSON file:', error);
								}
							};

							// Start reading the file
							reader.readAsText(file);
						} else {
							console.error('Only JSON file types are supported.');
						}
					} else {
						open = true;
						try {
							const dataTransfer = e.dataTransfer.getData('text/plain');
							if (dataTransfer) {
								const data = JSON.parse(dataTransfer);
								console.log(data);
								dispatch('drop', data);
							} else {
								console.log('Dropped text data is empty or not text/plain.');
							}
						} catch (error) {
							console.log(
								'Dropped data is not valid JSON text or is empty. Ignoring drop event for this type of data.'
							);
						} finally {
							draggedOver = false;
						}
					}
				}
			}

			draggedOver = false;
		}
	};

	const onDragLeave = (e) => {
		e.preventDefault();
		e.stopPropagation();

		draggedOver = false;
	};

	onMount(() => {
		if (!dragAndDrop) {
			return;
		}
		folderElement.addEventListener('dragover', onDragOver);
		folderElement.addEventListener('drop', onDrop);
		folderElement.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		if (!dragAndDrop) {
			return;
		}
		folderElement.removeEventListener('dragover', onDragOver);
		folderElement.removeEventListener('drop', onDrop);
		folderElement.removeEventListener('dragleave', onDragLeave);
	});
</script>

<div bind:this={folderElement} style="--pos:relative" class={className}>
	{#if draggedOver}
		<div
			style="--pos:absolute; --top:0; --left:0; --w:100%; --h:100%; --bgc:rgb(236 236 236 / 0.5); --dark-bgc:rgb(78 78 78 / 0.2); --z:50; --pe:none; touch-action:none"
			class="rounded-xs bg-opacity-50 dark:bg-opacity-10"
		></div>
	{/if}

	{#if collapsible}
		<Collapsible
			bind:open
			className="w-full "
			buttonClassName="w-full"
			onChange={(state) => {
				dispatch('change', state);
			}}
		>
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<div
				style="--w:100%; 
					--of:hidden;
					--pos:relative; 
					--d:flex; 
					--ai:center; 
					--jc:space-between; 
					--hvr-bgc:var(--color-gray-100); 
					--hvr-dark-bgc:var(--color-gray-900); 
					--c:var(--color-gray-500); 
					--dark-c:var(--color-gray-500); 
					--tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1);
					--m:0;
					--radius:0.6rem;"
				class="group"
			>
				<button
					style="--w:100%; --py:0.375rem; --pl:0.5rem; --d:flex; --ai:center; --g:0.375rem; --size:0.75rem; --weight:500"
				>
					<div style="--c:var(--color-gray-300); --dark-c:var(--color-gray-600)">
						{#if open}
							<ChevronDown className=" size-3" strokeWidth="2.5" />
						{:else}
							<ChevronRight className=" size-3" strokeWidth="2.5" />
						{/if}
					</div>

					<div style="--translatey:0.5px">
						{name}
					</div>
				</button>

				{#if onAdd}
					<Tooltip content={onAddLabel}>
						<button
							id="{id}-add-button"
							style="--pos:absolute; 
								--z:10; 
								--right:0.5rem; 
								--as:center; --d:flex; 
								--ai:center; --jc:center; 
								--dark-c: var(--color-gray-300); 
								--p:0.25rem; --hvr-bgc:var(--color-gray-100); 
								--hvr-dark-bgc:var(--color-gray-850); 
								--radius:9999px; 
								--tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); 
								--touch-action:auto"
							class="group-hover:visible"
							on:pointerup={(e) => {
								e.stopPropagation();
							}}
							on:click={(e) => {
								e.stopPropagation();
								onAdd();
							}}
						>
							<Plus className=" size-3" strokeWidth="2.5" />
						</button>
					</Tooltip>
				{/if}
			</div>

			<div slot="content" style="--w:100%">
				<slot></slot>
			</div>
		</Collapsible>
	{:else}
		<slot></slot>
	{/if}
</div>
