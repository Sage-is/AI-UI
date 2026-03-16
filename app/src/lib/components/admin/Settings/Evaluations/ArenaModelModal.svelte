<script>
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import { models } from '$lib/stores';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import PencilSolid from '$lib/components/icons/PencilSolid.svelte';
	import { toast } from 'svelte-sonner';
	import AccessControl from '$lib/components/workshop/common/AccessControl.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';

	export let show = false;
	export let edit = false;

	export let model = null;

	let name = '';
	let id = '';

	$: if (name) {
		generateId();
	}

	const generateId = () => {
		if (!edit) {
			id = name
				.toLowerCase()
				.replace(/[^a-z0-9]/g, '-')
				.replace(/-+/g, '-')
				.replace(/^-|-$/g, '');
		}
	};

	let profileImageUrl = `${WEBUI_BASE_URL}/favicon.png`;
	let description = '';

	let selectedModelId = '';
	let modelIds = [];
	let filterMode = 'include';

	let accessControl = {};

	let imageInputElement;
	let loading = false;
	let showDeleteConfirmDialog = false;

	const addModelHandler = () => {
		if (selectedModelId) {
			modelIds = [...modelIds, selectedModelId];
			selectedModelId = '';
		}
	};

	const submitHandler = () => {
		loading = true;

		if (!name || !id) {
			loading = false;
			toast.error('Name and ID are required, please fill them out');
			return;
		}

		if (!edit) {
			if ($models.find((model) => model.name === name)) {
				loading = false;
				name = '';
				toast.error('Model name already exists, please choose a different one');
				return;
			}
		}

		const model = {
			id: id,
			name: name,
			meta: {
				profile_image_url: profileImageUrl,
				description: description || null,
				model_ids: modelIds.length > 0 ? modelIds : null,
				filter_mode: modelIds.length > 0 ? (filterMode ? filterMode : null) : null,
				access_control: accessControl
			}
		};

		dispatch('submit', model);
		loading = false;
		show = false;

		name = '';
		id = '';
		profileImageUrl = `${WEBUI_BASE_URL}/favicon.png`;
		description = '';
		modelIds = [];
		selectedModelId = '';
	};

	const initModel = () => {
		if (model) {
			name = model.name;
			id = model.id;
			profileImageUrl = model.meta.profile_image_url;
			description = model.meta.description;
			modelIds = model.meta.model_ids || [];
			filterMode = model.meta?.filter_mode ?? 'include';
			accessControl = 'access_control' in model.meta ? model.meta.access_control : {};
		}
	};

	$: if (show) {
		initModel();
	}

	onMount(() => {
		initModel();
	});
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		dispatch('delete', model);
		show = false;
	}}
/>

<Modal size="sm" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-100); --px:1.25rem; --pt:1rem; --pb:0.5rem">
			<div style="--size:1.125rem; --weight:500; --as:center"
	class="font-primary">
				{#if edit}
					{$i18n.t('Edit Arena Model')}
				{:else}
					{$i18n.t('Add Arena Model')}
				{/if}
			</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1rem; --pb:1rem; --p: 1rem 0;--bgc: var(--white); --br: 1rem">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<form
					style="--d:flex; --fd:column; --w:100%"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div style="--px:0.25rem">
						<div style="--d:flex; --jc:center; --pb:0.75rem">
							<input
								bind:this={imageInputElement}
								type="file"
								hidden
								accept="image/*"
								on:change={(e) => {
									const files = e.target.files ?? [];
									let reader = new FileReader();
									reader.onload = (event) => {
										let originalImageUrl = `${event.target.result}`;

										const img = new Image();
										img.src = originalImageUrl;

										img.onload = function () {
											const canvas = document.createElement('canvas');
											const ctx = canvas.getContext('2d');

											// Calculate the aspect ratio of the image
											const aspectRatio = img.width / img.height;

											// Calculate the new width and height to fit within 250x250
											let newWidth, newHeight;
											if (aspectRatio > 1) {
												newWidth = 250 * aspectRatio;
												newHeight = 250;
											} else {
												newWidth = 250;
												newHeight = 250 / aspectRatio;
											}

											// Set the canvas size
											canvas.width = 250;
											canvas.height = 250;

											// Calculate the position to center the image
											const offsetX = (250 - newWidth) / 2;
											const offsetY = (250 - newHeight) / 2;

											// Draw the image on the canvas
											ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

											// Get the base64 representation of the compressed image
											const compressedSrc = canvas.toDataURL('image/jpeg');

											// Display the compressed image
											profileImageUrl = compressedSrc;

											e.target.files = null;
										};
									};

									if (
										files.length > 0 &&
										['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(
											files[0]['type']
										)
									) {
										reader.readAsDataURL(files[0]);
									}
								}}
							/>

							<button
								style="--pos:relative; --radius:9999px; --w:fit-content; --h:fit-content; --fs:0"
								type="button"
								on:click={() => {
									imageInputElement.click();
								}}
							>
								<img
									src={profileImageUrl}
									style="--w:4rem; --h:4rem; --radius:9999px; --objf:cover; --fs:0"
									alt="Profile"
								/>

								<div
									style="--pos:absolute; --d:flex; --jc:center; --radius:9999px; --bottom:0; --left:0; --right:0; --top:0; --h:100%; --w:100%; --of:hidden; --bgc:var(--color-gray-700); --op:0; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --tdn:300ms; --ttf:cubic-bezier(0.4, 0, 0.2, 1); --hvr-op:0.5"
	class="bg-fixed"
								>
									<div style="--my:auto; --c:#fff">
										<PencilSolid className="size-4" />
									</div>
								</div>
							</button>
						</div>
						<div style="--d:flex; --g:0.5rem">
							<div style="--d:flex; --fd:column; --w:100%">
								<div style="--mb:0.125rem; --size:0.75rem; --c:var(--color-gray-500)">{$i18n.t('Name')}</div>

								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
	class="placeholder:text-gray-300 dark:placeholder:text-gray-700"
										type="text"
										bind:value={name}
										placeholder={$i18n.t('Model Name')}
										autocomplete="off"
										required
									/>
								</div>
							</div>

							<div style="--d:flex; --fd:column; --w:100%">
								<div style="--mb:0.125rem; --size:0.75rem; --c:var(--color-gray-500)">{$i18n.t('ID')}</div>

								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
	class="placeholder:text-gray-300 dark:placeholder:text-gray-700"
										type="text"
										bind:value={id}
										placeholder={$i18n.t('Model ID')}
										autocomplete="off"
										required
										disabled={edit}
									/>
								</div>
							</div>
						</div>

						<div style="--d:flex; --fd:column; --w:100%; --mt:0.5rem">
							<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500)">{$i18n.t('Description')}</div>

							<div style="--fx:1 1 0%">
								<input
									style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
	class="placeholder:text-gray-300 dark:placeholder:text-gray-700"
									type="text"
									bind:value={description}
									placeholder={$i18n.t('Enter description')}
									autocomplete="off"
								/>
							</div>
						</div>

						<hr style="--bc:var(--color-gray-100); --dark-bc:rgb(78 78 78 / 0.1); --my:0.625rem; --w:100%" />

						<div style="--my:0.5rem; --mx:-0.5rem">
							<div style="--px:0.75rem; --py:0.5rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-950); --radius:0.5rem">
								<AccessControl bind:accessControl />
							</div>
						</div>

						<hr style="--bc:var(--color-gray-100); --dark-bc:rgb(78 78 78 / 0.1); --my:0.625rem; --w:100%" />

						<div style="--d:flex; --fd:column; --w:100%">
							<div style="--mb:0.25rem; --d:flex; --jc:space-between">
								<div style="--size:0.75rem; --c:var(--color-gray-500)">{$i18n.t('Models')}</div>

								<div>
									<button
										style="--size:0.75rem; --c:var(--color-gray-500)"
										type="button"
										on:click={() => {
											filterMode = filterMode === 'include' ? 'exclude' : 'include';
										}}
									>
										{#if filterMode === 'include'}
											{$i18n.t('Include')}
										{:else}
											{$i18n.t('Exclude')}
										{/if}
									</button>
								</div>
							</div>

							{#if modelIds.length > 0}
								<div style="--d:flex; --fd:column">
									{#each modelIds as modelId, modelIdx}
										<div style="--d:flex; --g:0.5rem; --w:100%; --jc:space-between; --ai:center">
											<div style="--size:0.875rem; --fx:1 1 0%; --py:0.25rem; --radius:0.5rem">
												{$models.find((model) => model.id === modelId)?.name}
											</div>
											<div style="--fs:0">
												<button
													type="button"
													on:click={() => {
														modelIds = modelIds.filter((_, idx) => idx !== modelIdx);
													}}
												>
													<Minus strokeWidth="2" className="size-3.5" />
												</button>
											</div>
										</div>
									{/each}
								</div>
							{:else}
								<div style="--c:var(--color-gray-500); --size:0.75rem; --ta:center; --py:0.5rem">
									{$i18n.t('Leave empty to include all models or select specific models')}
								</div>
							{/if}
						</div>

						<hr style="--bc:var(--color-gray-100); --dark-bc:rgb(78 78 78 / 0.1); --my:0.625rem; --w:100%" />

						<div style="--d:flex; --ai:center">
							<select
								style="--w:100%; --py:0.25rem; --size:0.875rem; --radius:0.5rem; --bgc:transparent; --oe:none"
	class="{selectedModelId
									? ''
									: 'text-gray-500'} placeholder:text-gray-300 dark:placeholder:text-gray-700"
								bind:value={selectedModelId}
							>
								<option value="">{$i18n.t('Select a model')}</option>
								{#each $models.filter((m) => m?.owned_by !== 'arena') as model}
									<option value={model.id} style="--bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-700)">{model.name}</option>
								{/each}
							</select>

							<div>
								<button
									type="button"
									on:click={() => {
										addModelHandler();
									}}
								>
									<Plus className="size-3.5" strokeWidth="2" />
								</button>
							</div>
						</div>
					</div>

					<div style="--d:flex; --jc:flex-end; --pt:0.75rem; --size:0.875rem; --weight:500; --g:0.375rem">
						{#if edit}
							<button
								style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --dark-bgc:#000; --hvr-dark-bgc:var(--color-gray-950); --dark-c:#fff; --bgc:#fff; --c:#000; --hvr-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.25rem; --ai:center"
								type="button"
								on:click={() => {
									showDeleteConfirmDialog = true;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}

						<button
							style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-950); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.25rem; --ai:center"
	class="{loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Save')}

							{#if loading}
								<div style="--ml:0.5rem; --as:center">
									<Spinner />
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
