<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import { models, config } from '$lib/stores';
	import Icon from '$lib/components/Icon.svelte';

	import { toast } from 'svelte-sonner';
	import { copyToClipboard } from '$lib/utils';

		import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import MapSelector from '$lib/components/common/Valves/MapSelector.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let variables = {};
	export let title = '';

	export let onSave = (e) => {};

	let loading = false;
	let variableValues = {};

	const submitHandler = async () => {
		onSave(variableValues);
		show = false;
	};

	const init = async () => {
		loading = true;
		variableValues = {};
		for (const variable of Object.keys(variables)) {
			if (variables[variable]?.default !== undefined) {
				variableValues[variable] = variables[variable].default;
			} else {
				variableValues[variable] = '';
			}
		}
		loading = false;

		await tick();

		const firstInputElement = document.getElementById('input-variable-0');
		if (firstInputElement) {
			console.log('Focusing first input element:', firstInputElement);
			firstInputElement.focus();
		}
	};

	$: if (show) {
		init();
	}
</script>

<Modal bind:show size="md">
	<div>
		<div style="--d:flex;
					--jc:space-between;
					--dark-c:var(--color-gray-300);
					--px:1.2rem; --pt:1rem; --pb:0.5rem">
			<div style="--size:1.125rem;
					--weight:500;
					--as:center">{title || $i18n.t('Input Variables')}</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<Icon name="x-mark" strokeWidth="2" className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%;--bgc: var(--white); --br: 1rem;">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<form
					style="--d:flex; --fd:column; --w:100%"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div style="--px:0.2rem">
						{#if !loading}
							<div style="--d:flex; --fd:column; --g:0.2rem">
								{#each Object.keys(variables) as variable, idx}
									{@const { type, ...variableAttributes } = variables[variable] ?? {}}

									<div style="--py:0.125rem; --w:100%; --jc:space-between">
										<div style="--d:flex; --w:100%; --jc:space-between; --mb:0.4rem">
											<div style="--as:center; --size:0.6rem; --weight:500">
												{variable}

												{#if variables[variable]?.required ?? true}
													<span style="--c:var(--color-gray-500)">*required</span>
												{/if}
											</div>
										</div>

										<div style="--d:flex; --mt:0.125rem; --mb:0.125rem; --g:0.5rem">
											<div style="--fx:1 1 0%">
												{#if variables[variable]?.type === 'select'}
													{@const options = variableAttributes?.options ?? []}
													{@const placeholder = variableAttributes?.placeholder ?? ''}

													<select
														style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
														bind:value={variableValues[variable]}
														id="input-variable-{idx}"
													>
														{#if placeholder}
															<option value="" disabled selected>
																{placeholder}
															</option>
														{/if}
														{#each options as option}
															<option value={option} selected={option === variableValues[variable]}>
																{option}
															</option>
														{/each}
													</select>
												{:else if variables[variable]?.type === 'checkbox'}
													<div style="--d:flex; --ai:center; --g:0.5rem">
														<div style="--pos:relative; --d:flex; --jc:center; --ai:center; --g:0.5rem">
															<input
																type="checkbox"
																bind:checked={variableValues[variable]}
																style="--w:0.8rem; --h:0.8rem; --radius:0.2rem; --cur:pointer;  --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700)"
																id="input-variable-{idx}"
																{...variableAttributes}
															/>

															<label for="input-variable-{idx}" style="--size:0.8rem"
																>{variables[variable]?.label ?? variable}</label
															>
														</div>

														<input
															type="text"
															style="--fx:1 1 0%; --py:0.2rem; --size:0.8rem; --dark-c:var(--color-gray-300); --bgc:transparent; --oe:none"
															placeholder="Enter value (true/false)"
															bind:value={variableValues[variable]}
															autocomplete="off"
															required
														/>
													</div>
												{:else if variables[variable]?.type === 'color'}
													<div style="--d:flex; --ai:center; --g:0.5rem">
														<div style="--pos:relative; --w:1.5rem; --h:1.5rem">
															<input
																type="color"
																style="--w:1.5rem; --h:1.5rem; --radius:0.2rem; --cur:pointer;  --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700)"
																value={variableValues[variable]}
																id="input-variable-{idx}"
																on:input={(e) => {
																	// Convert the color value to uppercase immediately
																	variableValues[variable] = e.target.value.toUpperCase();
																}}
																{...variableAttributes}
															/>
														</div>

														<input
															type="text"
															style="--fx:1 1 0%; --py:0.5rem; --size:0.8rem; --dark-c:var(--color-gray-300); --bgc:transparent; --oe:none"
															placeholder="Enter hex color (e.g. #FF0000)"
															bind:value={variableValues[variable]}
															autocomplete="off"
															required
														/>
													</div>
												{:else if variables[variable]?.type === 'date'}
													<input
														type="date"
														style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'datetime-local'}
													<input
														type="datetime-local"
														style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'email'}
													<input
														type="email"
														style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'month'}
													<input
														type="month"
														style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'number'}
													<input
														type="number"
														style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'range'}
													<div style="--d:flex; --ai:center; --g:0.5rem">
														<div style="--pos:relative; --d:flex; --jc:center; --ai:center; --g:0.5rem; --fx:1 1 0%">
															<input
																type="range"
																bind:value={variableValues[variable]}
																style="--w:100%; --radius:0.5rem; --py:0.2rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
																id="input-variable-{idx}"
																{...variableAttributes}
															/>
														</div>

														<input
															type="text"
															style="--py:0.2rem; --size:0.8rem; --dark-c:var(--color-gray-300); --bgc:transparent; --oe:none; --ta:right"
															placeholder="Enter value"
															bind:value={variableValues[variable]}
															autocomplete="off"
															required
														/>
													</div>

													<!-- <input
														type="range"
														style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
													/> -->
												{:else if variables[variable]?.type === 'tel'}
													<input
														type="tel"
														style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'text'}
													<input
														type="text"
														style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'time'}
													<input
														type="time"
														style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'url'}
													<input
														type="url"
														style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
														{...variableAttributes}
													/>
												{:else if variables[variable]?.type === 'map'}
													<!-- EXPERIMENTAL INPUT TYPE, DO NOT USE IN PRODUCTION -->
													<div style="--d:flex; --fd:column; --ai:center; --g:0.2rem">
														<MapSelector
															setViewLocation={((variableValues[variable] ?? '').includes(',') ??
															false)
																? variableValues[variable].split(',')
																: null}
															onClick={(value) => {
																variableValues[variable] = value;
															}}
														/>

														<input
															type="text"
															style="--w:100%; --py:0.2rem; --ta:left; --size:0.8rem; --dark-c:var(--color-gray-300); --bgc:transparent; --oe:none"
															placeholder="Enter coordinates (e.g. 51.505, -0.09)"
															bind:value={variableValues[variable]}
															autocomplete="off"
															required
														/>
													</div>
												{:else}
													<textarea
														style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
														placeholder={variables[variable]?.placeholder ?? ''}
														bind:value={variableValues[variable]}
														autocomplete="off"
														id="input-variable-{idx}"
														required
													/>
												{/if}
											</div>
										</div>

										<!-- {#if (valvesSpec.properties[property]?.description ?? null) !== null}
									<div style="--size:0.6rem; --c:var(--color-gray-500)">
										{valvesSpec.properties[property].description}
									</div>
								{/if} -->
									</div>
								{/each}
							</div>
						{:else}
							<Spinner className="size-5" />
						{/if}
					</div>

					<div style="--d:flex; --jc:flex-end; --pt:0.6rem; --size:0.8rem; --weight:500">
						<button
							style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#fff; --hvr-bgc:var(--color-gray-100); --c:#000; --dark-bgc:#000; --dark-c:#fff; --hvr-dark-bgc:var(--color-gray-900); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
							type="button"
							on:click={() => {
								show = false;
							}}
						>
							{$i18n.t('Cancel')}
						</button>

						<button
							style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
							type="submit"
						>
							{$i18n.t('Save')}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
