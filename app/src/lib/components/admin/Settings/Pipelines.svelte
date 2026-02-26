<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';

	import { toast } from 'svelte-sonner';
	import { config, models, settings } from '$lib/stores';
	import { getContext, onMount, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import {
		getPipelineValves,
		getPipelineValvesSpec,
		updatePipelineValves,
		getPipelines,
		getModels,
		getPipelinesList,
		downloadPipeline,
		deletePipeline,
		uploadPipeline
	} from '$lib/apis';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let saveHandler: Function;

	let downloading = false;
	let uploading = false;

	let pipelineFiles;

	let PIPELINES_LIST = null;
	let selectedPipelinesUrlIdx = '';

	let pipelines = null;

	let valves = null;
	let valves_spec = null;
	let selectedPipelineIdx = null;

	let pipelineDownloadUrl = '';

	const updateHandler = async () => {
		const pipeline = pipelines[selectedPipelineIdx];

		if (pipeline && (pipeline?.valves ?? false)) {
			for (const property in valves_spec.properties) {
				if (valves_spec.properties[property]?.type === 'array') {
					valves[property] = valves[property].split(',').map((v) => v.trim());
				}
			}

			const res = await updatePipelineValves(
				localStorage.token,
				pipeline.id,
				valves,
				selectedPipelinesUrlIdx
			).catch((error) => {
				toast.error(`${error}`);
			});

			if (res) {
				toast.success($i18n.t('Valves updated successfully'));
				setPipelines();
				models.set(
					await getModels(
						localStorage.token,
						$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
					)
				);
				saveHandler();
			}
		} else {
			toast.error($i18n.t('No valves to update'));
		}
	};

	const getValves = async (idx) => {
		valves = null;
		valves_spec = null;

		valves_spec = await getPipelineValvesSpec(
			localStorage.token,
			pipelines[idx].id,
			selectedPipelinesUrlIdx
		);
		valves = await getPipelineValves(
			localStorage.token,
			pipelines[idx].id,
			selectedPipelinesUrlIdx
		);

		for (const property in valves_spec.properties) {
			if (valves_spec.properties[property]?.type === 'array') {
				valves[property] = valves[property].join(',');
			}
		}
	};

	const setPipelines = async () => {
		pipelines = null;
		valves = null;
		valves_spec = null;

		if (PIPELINES_LIST.length > 0) {
			console.debug(selectedPipelinesUrlIdx);
			pipelines = await getPipelines(localStorage.token, selectedPipelinesUrlIdx);

			if (pipelines.length > 0) {
				selectedPipelineIdx = 0;
				await getValves(selectedPipelineIdx);
			}
		} else {
			pipelines = [];
		}
	};

	const addPipelineHandler = async () => {
		downloading = true;
		const res = await downloadPipeline(
			localStorage.token,
			pipelineDownloadUrl,
			selectedPipelinesUrlIdx
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Pipeline downloaded successfully'));
			setPipelines();
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
		}

		downloading = false;
	};

	const uploadPipelineHandler = async () => {
		uploading = true;

		if (pipelineFiles && pipelineFiles.length !== 0) {
			const file = pipelineFiles[0];

			console.log(file);

			const res = await uploadPipeline(localStorage.token, file, selectedPipelinesUrlIdx).catch(
				(error) => {
					console.error(error);
					toast.error('Something went wrong :/');
					return null;
				}
			);

			if (res) {
				toast.success($i18n.t('Pipeline downloaded successfully'));
				setPipelines();
				models.set(
					await getModels(
						localStorage.token,
						$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
					)
				);
			}
		} else {
			toast.error($i18n.t('No file selected'));
		}

		pipelineFiles = null;
		const pipelineUploadInputElement = document.getElementById('pipelines-upload-input');

		if (pipelineUploadInputElement) {
			pipelineUploadInputElement.value = null;
		}

		uploading = false;
	};

	const deletePipelineHandler = async () => {
		const res = await deletePipeline(
			localStorage.token,
			pipelines[selectedPipelineIdx].id,
			selectedPipelinesUrlIdx
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Pipeline deleted successfully'));
			setPipelines();
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
		}
	};

	onMount(async () => {
		PIPELINES_LIST = await getPipelinesList(localStorage.token);
		console.log(PIPELINES_LIST);

		if (PIPELINES_LIST.length > 0) {
			selectedPipelinesUrlIdx = PIPELINES_LIST[0]['idx'].toString();
		}

		await setPipelines();
	});
</script>

<form
	style="--d:flex; --fd:column; --h:100%; --jc:space-between; --g:0.75rem; --size:0.875rem"
	on:submit|preventDefault={async () => {
		updateHandler();
	}}
>
	<div style="--ofy:scroll; --h:100%"
	class="scrollbar-hidden">
		{#if PIPELINES_LIST !== null}
			<div style="--d:flex; --w:100%; --jc:space-between; --mb:0.5rem">
				<div style="--as:center; --size:0.875rem; --weight:600">
					{$i18n.t('Manage Pipelines')}
				</div>
			</div>

			{#if PIPELINES_LIST.length > 0}
				<div style="--g:0.25rem">
					<div style="--d:flex; --g:0.5rem">
						<div style="--fx:1 1 0%">
							<select
								style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
								bind:value={selectedPipelinesUrlIdx}
								placeholder={$i18n.t('Select a pipeline url')}
								on:change={async () => {
									await tick();
									await setPipelines();
								}}
							>
								<option value="" selected disabled style="--bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-700)"
									>{$i18n.t('Select a pipeline url')}</option
								>

								{#each PIPELINES_LIST as pipelines, idx}
									<option value={pipelines.idx.toString()} style="--bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-700)"
										>{pipelines.url}</option
									>
								{/each}
							</select>
						</div>
					</div>
				</div>

				<div style="--my:0.5rem">
					<div style="--mb:0.5rem; --size:0.875rem; --weight:500">
						{$i18n.t('Upload Pipeline')}
					</div>
					<div style="--d:flex; --w:100%">
						<div style="--fx:1 1 0%; --mr:0.5rem">
							<input
								id="pipelines-upload-input"
								bind:files={pipelineFiles}
								type="file"
								accept=".py"
								hidden
							/>

							<button
								style="--w:100%; --size:0.875rem; --weight:500; --py:0.5rem; --bgc:transparent; --hvr-bgc:var(--color-gray-100); --b:1px solid; --bs:dashed; --dark-bc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-850); --ta:center; --radius:0.75rem"
								type="button"
								on:click={() => {
									document.getElementById('pipelines-upload-input')?.click();
								}}
							>
								{#if pipelineFiles}
									{pipelineFiles.length > 0 ? `${pipelineFiles.length}` : ''} pipeline(s) selected.
								{:else}
									{$i18n.t('Click here to select a py file.')}
								{/if}
							</button>
						</div>
						<button
							style="--px:0.625rem; --bgc:var(--color-gray-100); --hvr-bgc:var(--color-gray-200); --c:var(--color-gray-800); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --dark-c:var(--color-gray-100); --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							on:click={() => {
								uploadPipelineHandler();
							}}
							disabled={uploading}
							type="button"
						>
							{#if uploading}
								<div style="--as:center">
									<svg
										style="--w:1rem; --h:1rem"
										viewBox="0 0 24 24"
										fill="currentColor"
										xmlns="http://www.w3.org/2000/svg"
									>
										<style>
											.spinner_ajPY {
												transform-origin: center;
												animation: spinner_AtaB 0.75s infinite linear;
											}

											@keyframes spinner_AtaB {
												100% {
													transform: rotate(360deg);
												}
											}
										</style>
										<path
											d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
											opacity=".25"
										/>
										<path
											d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
											class="spinner_ajPY"
										/>
									</svg>
								</div>
							{:else}
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									style="--w:1rem; --h:1rem"
								>
									<path
										d="M7.25 10.25a.75.75 0 0 0 1.5 0V4.56l2.22 2.22a.75.75 0 1 0 1.06-1.06l-3.5-3.5a.75.75 0 0 0-1.06 0l-3.5 3.5a.75.75 0 0 0 1.06 1.06l2.22-2.22v5.69Z"
									/>
									<path
										d="M3.5 9.75a.75.75 0 0 0-1.5 0v1.5A2.75 2.75 0 0 0 4.75 14h6.5A2.75 2.75 0 0 0 14 11.25v-1.5a.75.75 0 0 0-1.5 0v1.5c0 .69-.56 1.25-1.25 1.25h-6.5c-.69 0-1.25-.56-1.25-1.25v-1.5Z"
									/>
								</svg>
							{/if}
						</button>
					</div>
				</div>

				<div style="--my:0.5rem">
					<div style="--mb:0.5rem; --size:0.875rem; --weight:500">
						{$i18n.t('Install from Github URL')}
					</div>
					<div style="--d:flex; --w:100%">
						<div style="--fx:1 1 0%; --mr:0.5rem">
							<input
								style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
								placeholder={$i18n.t('Enter Github Raw URL')}
								bind:value={pipelineDownloadUrl}
							/>
						</div>
						<button
							style="--px:0.625rem; --bgc:var(--color-gray-100); --hvr-bgc:var(--color-gray-200); --c:var(--color-gray-800); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --dark-c:var(--color-gray-100); --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							on:click={() => {
								addPipelineHandler();
							}}
							disabled={downloading}
							type="button"
						>
							{#if downloading}
								<div style="--as:center">
									<svg
										style="--w:1rem; --h:1rem"
										viewBox="0 0 24 24"
										fill="currentColor"
										xmlns="http://www.w3.org/2000/svg"
									>
										<style>
											.spinner_ajPY {
												transform-origin: center;
												animation: spinner_AtaB 0.75s infinite linear;
											}

											@keyframes spinner_AtaB {
												100% {
													transform: rotate(360deg);
												}
											}
										</style>
										<path
											d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
											opacity=".25"
										/>
										<path
											d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
											class="spinner_ajPY"
										/>
									</svg>
								</div>
							{:else}
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									style="--w:1rem; --h:1rem"
								>
									<path
										d="M8.75 2.75a.75.75 0 0 0-1.5 0v5.69L5.03 6.22a.75.75 0 0 0-1.06 1.06l3.5 3.5a.75.75 0 0 0 1.06 0l3.5-3.5a.75.75 0 0 0-1.06-1.06L8.75 8.44V2.75Z"
									/>
									<path
										d="M3.5 9.75a.75.75 0 0 0-1.5 0v1.5A2.75 2.75 0 0 0 4.75 14h6.5A2.75 2.75 0 0 0 14 11.25v-1.5a.75.75 0 0 0-1.5 0v1.5c0 .69-.56 1.25-1.25 1.25h-6.5c-.69 0-1.25-.56-1.25-1.25v-1.5Z"
									/>
								</svg>
							{/if}
						</button>
					</div>

					<div style="--mt:0.5rem; --size:0.75rem; --c:var(--color-gray-500)">
						<span style="--weight:600; --dark-c:var(--color-gray-200)">Warning:</span> Pipelines are a plugin
						system with arbitrary code execution —
						<span style="--weight:500; --dark-c:var(--color-gray-400)"
							>don't fetch random pipelines from sources you don't trust.</span
						>
					</div>
				</div>

				<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.75rem; --w:100%" />

				{#if pipelines !== null}
					{#if pipelines.length > 0}
						<div style="--d:flex; --w:100%; --jc:space-between; --mb:0.5rem">
							<div style="--as:center; --size:0.875rem; --weight:600">
								{$i18n.t('Pipelines Valves')}
							</div>
						</div>
						<div style="--g:0.25rem">
							{#if pipelines.length > 0}
								<div style="--d:flex; --g:0.5rem">
									<div style="--fx:1 1 0%">
										<select
											style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
											bind:value={selectedPipelineIdx}
											placeholder={$i18n.t('Select a pipeline')}
											on:change={async () => {
												await tick();
												await getValves(selectedPipelineIdx);
											}}
										>
											{#each pipelines as pipeline, idx}
												<option value={idx} style="--bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-700)"
													>{pipeline.name} ({pipeline.type ?? 'pipe'})</option
												>
											{/each}
										</select>
									</div>

									<button
										style="--px:0.625rem; --bgc:var(--color-gray-100); --hvr-bgc:var(--color-gray-200); --c:var(--color-gray-800); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --dark-c:var(--color-gray-100); --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
										on:click={() => {
											deletePipelineHandler();
										}}
										type="button"
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 16 16"
											fill="currentColor"
											style="--w:1rem; --h:1rem"
										>
											<path
												fill-rule="evenodd"
												d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
								</div>
							{/if}

							<div style="--g:0.25rem">
								{#if pipelines[selectedPipelineIdx].valves}
									{#if valves}
										{#each Object.keys(valves_spec.properties) as property, idx}
											<div style="--py:0.125rem; --w:100%; --jc:space-between">
												<div style="--d:flex; --w:100%; --jc:space-between">
													<div style="--as:center; --size:0.75rem; --weight:500">
														{valves_spec.properties[property].title}
													</div>

													<button
														style="--p:0.25rem; --px:0.75rem; --size:0.75rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
														type="button"
														on:click={() => {
															valves[property] = (valves[property] ?? null) === null ? '' : null;
														}}
													>
														{#if (valves[property] ?? null) === null}
															<span style="--ml:0.5rem; --as:center"> {$i18n.t('None')} </span>
														{:else}
															<span style="--ml:0.5rem; --as:center"> {$i18n.t('Custom')} </span>
														{/if}
													</button>
												</div>

												{#if (valves[property] ?? null) !== null}
													<!-- {valves[property]} -->
													<div style="--d:flex; --mt:0.125rem; --mb:0.375rem; --g:0.5rem">
														<div style="--fx:1 1 0%">
															{#if valves_spec.properties[property]?.enum ?? null}
																<select
																	style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
																	bind:value={valves[property]}
																>
																	{#each valves_spec.properties[property].enum as option}
																		<option value={option} selected={option === valves[property]}>
																			{option}
																		</option>
																	{/each}
																</select>
															{:else if (valves_spec.properties[property]?.type ?? null) === 'boolean'}
																<div style="--d:flex; --jc:space-between; --ai:center">
																	<div style="--size:0.75rem; --c:var(--color-gray-500)">
																		{valves[property] ? 'Enabled' : 'Disabled'}
																	</div>

																	<div style="--pr:0.5rem">
																		<Switch bind:state={valves[property]} />
																	</div>
																</div>
															{:else}
																<input
																	style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
																	type="text"
																	placeholder={valves_spec.properties[property].title}
																	bind:value={valves[property]}
																	autocomplete="off"
																	required
																/>
															{/if}
														</div>
													</div>
												{/if}
											</div>
										{/each}
									{:else}
										<Spinner className="size-5" />
									{/if}
								{:else}
									<div>No valves</div>
								{/if}
							</div>
						</div>
					{:else if pipelines.length === 0}
						<div>Pipelines Not Detected</div>
					{/if}
				{:else}
					<div style="--d:flex; --jc:center">
						<div style="--my:auto">
							<Spinner className="size-4" />
						</div>
					</div>
				{/if}
			{:else}
				<div>{$i18n.t('Pipelines Not Detected')}</div>
			{/if}
		{:else}
			<div style="--d:flex; --jc:center; --h:100%">
				<div style="--my:auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>

	{#if PIPELINES_LIST !== null && PIPELINES_LIST.length > 0}
		<div style="--d:flex; --jc:flex-end; --pt:0.75rem; --size:0.875rem; --weight:500">
			<button
				style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
				type="submit"
			>
				{$i18n.t('Save')}
			</button>
		</div>
	{/if}
</form>
