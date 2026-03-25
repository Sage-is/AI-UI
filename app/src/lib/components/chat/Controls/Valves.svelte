<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { config, functions, models, settings, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	import {
		getUserValvesSpecById as getFunctionUserValvesSpecById,
		getUserValvesById as getFunctionUserValvesById,
		updateUserValvesById as updateFunctionUserValvesById,
		getFunctions
	} from '$lib/apis/functions';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Valves from '$lib/components/common/Valves.svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let show = false;

	let selectedId = '';

	let loading = false;

	let valvesSpec = null;
	let valves = {};

	let debounceTimer;

	const debounceSubmitHandler = async () => {
		if (debounceTimer) {
			clearTimeout(debounceTimer);
		}

		// Set a new timer
		debounceTimer = setTimeout(() => {
			submitHandler();
		}, 500); // 0.5 second debounce
	};

	const getUserValves = async () => {
		loading = true;
		valves = await getFunctionUserValvesById(localStorage.token, selectedId);
		valvesSpec = await getFunctionUserValvesSpecById(localStorage.token, selectedId);

		if (valvesSpec) {
			// Convert array to string
			for (const property in valvesSpec.properties) {
				if (valvesSpec.properties[property]?.type === 'array') {
					valves[property] = (valves[property] ?? []).join(',');
				}
			}
		}

		loading = false;
	};

	const submitHandler = async () => {
		if (valvesSpec) {
			// Convert string to array
			for (const property in valvesSpec.properties) {
				if (valvesSpec.properties[property]?.type === 'array') {
					valves[property] = (valves[property] ?? '').split(',').map((v) => v.trim());
				}
			}

			const res = await updateFunctionUserValvesById(
				localStorage.token,
				selectedId,
				valves
			).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				toast.success($i18n.t('Valves updated'));
				valves = res;
			}
		}
	};

	$: if (selectedId) {
		getUserValves();
	}

	$: if (show) {
		init();
	}

	const init = async () => {
		loading = true;

		if ($functions === null) {
			functions.set(await getFunctions(localStorage.token));
		}

		loading = false;
	};
</script>

{#if show && !loading}
	<form
		style="--d:flex; --fd:column; --h:100%; --jc:space-between; --g:0.6rem; --size:0.8rem"
		on:submit|preventDefault={() => {
			submitHandler();
			dispatch('save');
		}}
	>
		<div style="--d:flex; --fd:column">
			<div style="--g:0.2rem">
				<div style="--d:flex; --g:0.5rem">
					<div style="--fx:1 1 0%">
						<select
							style="--w:100%; --radius:0.125rem; --py:0.5rem; --px:0.2rem; --size:0.6rem; --bgc:transparent; --oe:none"
							bind:value={selectedId}
							on:change={async () => {
								await tick();
							}}
						>
							<option value="" selected disabled style="--bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800)"
								>{$i18n.t('Select a function')}</option
							>

							{#each $functions as func, funcIdx}
								<option value={func.id} style="--bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800)">{func.name}</option>
							{/each}
						</select>
					</div>
				</div>
			</div>

			{#if selectedId}
				<hr style="--bc:var(--color-gray-50); --dark-bc:var(--color-gray-800); --my:0.2rem; --w:100%" />

				<div style="--my:0.5rem; --size:0.6rem">
					{#if !loading}
						<Valves
							{valvesSpec}
							bind:valves
							on:change={() => {
								debounceSubmitHandler();
							}}
						/>
					{:else}
						<Spinner className="size-5" />
					{/if}
				</div>
			{/if}
		</div>
	</form>
{:else}
	<Spinner className="size-4" />
{/if}
