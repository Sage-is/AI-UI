<script>
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import Switch from './Switch.svelte';
	import MapSelector from './Valves/MapSelector.svelte';
	import { split } from 'postcss/lib/list';

	export let valvesSpec = null;
	export let valves = {};
</script>

{#if valvesSpec && Object.keys(valvesSpec?.properties ?? {}).length}
	{#each Object.keys(valvesSpec.properties) as property, idx}
		<div style="--py:0.125rem; --w:100%; --jc:space-between">
			<div style="--d:flex; --w:100%; --jc:space-between">
				<div style="--as:center; --size:0.6rem; --weight:500">
					{valvesSpec.properties[property].title}

					{#if (valvesSpec?.required ?? []).includes(property)}
						<span style="--c:var(--color-gray-500)">*required</span>
					{/if}
				</div>

				<button
					style="--p:0.25rem; --px:0.6rem; --size:0.6rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					type="button"
					on:click={() => {
						valves[property] =
							(valves[property] ?? null) === null
								? (valvesSpec.properties[property]?.default ?? '')
								: null;

						dispatch('change');
					}}
				>
					{#if (valves[property] ?? null) === null}
						<span style="--ml:0.5rem; --as:center">
							{#if (valvesSpec?.required ?? []).includes(property)}
								{$i18n.t('None')}
							{:else}
								{$i18n.t('Default')}
							{/if}
						</span>
					{:else}
						<span style="--ml:0.5rem; --as:center"> {$i18n.t('Custom')} </span>
					{/if}
				</button>
			</div>

			{#if (valves[property] ?? null) !== null}
				<!-- {valves[property]} -->
				<div style="--d:flex; --mt:0.125rem; --mb:0.125rem; --g:0.5rem">
					<div style="--fx:1 1 0%">
						{#if valvesSpec.properties[property]?.enum ?? null}
							<select
								style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
								bind:value={valves[property]}
								on:change={() => {
									dispatch('change');
								}}
							>
								{#each valvesSpec.properties[property].enum as option}
									<option value={option} selected={option === valves[property]}>
										{option}
									</option>
								{/each}
							</select>
						{:else if (valvesSpec.properties[property]?.type ?? null) === 'boolean'}
							<div style="--d:flex; --jc:space-between; --ai:center">
								<div style="--size:0.6rem; --c:var(--color-gray-500)">
									{valves[property] ? 'Enabled' : 'Disabled'}
								</div>

								<div style="--pr:0.5rem">
									<Switch
										bind:state={valves[property]}
										on:change={() => {
											dispatch('change');
										}}
									/>
								</div>
							</div>
						{:else if (valvesSpec.properties[property]?.type ?? null) !== 'string'}
							<input
								style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
								type="text"
								placeholder={valvesSpec.properties[property].title}
								bind:value={valves[property]}
								autocomplete="off"
								required
								on:change={() => {
									dispatch('change');
								}}
							/>
						{:else if valvesSpec.properties[property]?.input ?? null}
							{#if valvesSpec.properties[property]?.input?.type === 'color'}
								<div style="--d:flex; --ai:center; --g:0.5rem">
									<div style="--pos:relative; --w:1.5rem; --h:1.5rem">
										<input
											type="color"
											style="--w:1.5rem; --h:1.5rem; --radius:0.25rem; --cur:pointer;  --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700)"
											value={valves[property] ?? '#000000'}
											on:input={(e) => {
												// Convert the color value to uppercase immediately
												valves[property] = e.target.value.toUpperCase();
												dispatch('change');
											}}
										/>
									</div>

									<input
										type="text"
										style="--fx:1 1 0%; --radius:0.5rem; --py:0.5rem; --size:0.875rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
										placeholder="Enter hex color (e.g. #FF0000)"
										bind:value={valves[property]}
										autocomplete="off"
										disabled
										on:change={() => {
											dispatch('change');
										}}
									/>
								</div>
							{:else if valvesSpec.properties[property]?.input?.type === 'map'}
								<!-- EXPERIMENTAL INPUT TYPE, DO NOT USE IN PRODUCTION -->
								<div style="--d:flex; --fd:column; --ai:center; --g:0.25rem">
									<MapSelector
										setViewLocation={((valves[property] ?? '').includes(',') ?? false)
											? valves[property].split(',')
											: null}
										onClick={(value) => {
											valves[property] = value;
											dispatch('change');
										}}
									/>

									{#if valves[property]}
										<input
											type="text"
											style="--w:100%; --radius:0.5rem; --py:0.25rem; --ta:left; --size:0.875rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
											placeholder="Enter coordinates (e.g. 51.505, -0.09)"
											bind:value={valves[property]}
											autocomplete="off"
											on:change={() => {
												dispatch('change');
											}}
										/>
									{/if}
								</div>
							{/if}
						{:else}
							<textarea
								style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.875rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
								placeholder={valvesSpec.properties[property].title}
								bind:value={valves[property]}
								autocomplete="off"
								required
								on:change={() => {
									dispatch('change');
								}}
							/>
						{/if}
					</div>
				</div>
			{/if}

			{#if (valvesSpec.properties[property]?.description ?? null) !== null}
				<div style="--size:0.6rem; --c:var(--color-gray-500)">
					{valvesSpec.properties[property].description}
				</div>
			{/if}
		</div>
	{/each}
{:else}
	<div style="--size:0.6rem">No valves</div>
{/if}
