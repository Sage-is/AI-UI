<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';
	import { addUser } from '$lib/apis/auths';

	import Modal from '../../common/Modal.svelte';
	import {
		getFunctionValvesById,
		getFunctionValvesSpecById,
		updateFunctionValvesById
	} from '$lib/apis/functions';
	import { getToolValvesById, getToolValvesSpecById, updateToolValvesById } from '$lib/apis/tools';
	import Spinner from '../../common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Valves from '$lib/components/common/Valves.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	export let type = 'tool';
	export let id = null;

	let saving = false;
	let loading = false;

	let valvesSpec = null;
	let valves = {};

	const submitHandler = async () => {
		saving = true;

		if (valvesSpec) {
			// Convert string to array
			for (const property in valvesSpec.properties) {
				if (valvesSpec.properties[property]?.type === 'array') {
					valves[property] = (valves[property] ?? '').split(',').map((v) => v.trim());
				}
			}

			let res = null;

			if (type === 'tool') {
				res = await updateToolValvesById(localStorage.token, id, valves).catch((error) => {
					toast.error(`${error}`);
				});
			} else if (type === 'function') {
				res = await updateFunctionValvesById(localStorage.token, id, valves).catch((error) => {
					toast.error(`${error}`);
				});
			}

			if (res) {
				toast.success('Valves updated successfully');
				dispatch('save');
			}
		}

		saving = false;
	};

	const initHandler = async () => {
		loading = true;
		valves = {};
		valvesSpec = null;

		if (type === 'tool') {
			valves = await getToolValvesById(localStorage.token, id);
			valvesSpec = await getToolValvesSpecById(localStorage.token, id);
		} else if (type === 'function') {
			valves = await getFunctionValvesById(localStorage.token, id);
			valvesSpec = await getFunctionValvesSpecById(localStorage.token, id);
		}

		if (!valves) {
			valves = {};
		}

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

	$: if (show) {
		initHandler();
	}
</script>

<Modal size="sm" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300); --px:1.25rem; --pt:1rem; --pb:0.5rem">
			<div style="--size:1.125rem; --weight:500; --as:center">{$i18n.t('Valves')}</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1.25rem; --pb:1rem; --p: 1rem 0;--bgc: var(--white); --br: 1rem; --shadow: 6">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<form
					style="--d:flex; --fd:column; --w:100%"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div style="--px:0.25rem">
						{#if !loading}
							<Valves {valvesSpec} bind:valves />
						{:else}
							<Spinner className="size-5" />
						{/if}
					</div>

					<div style="--d:flex; --jc:flex-end; --pt:0.75rem; --size:0.875rem; --weight:500">
						<button
							style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
	class="{saving
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={saving}
						>
							{$i18n.t('Save')}

							{#if saving}
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
