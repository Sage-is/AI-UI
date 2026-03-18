<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { getContext, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	import Modal from '$lib/components/common/Modal.svelte';
	import AddMemoryModal from './AddMemoryModal.svelte';
	import { deleteMemoriesByUserId, deleteMemoryById, getMemories } from '$lib/apis/memories';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { error } from '@sveltejs/kit';
	import EditMemoryModal from './EditMemoryModal.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	const i18n = getContext('i18n');
	dayjs.extend(localizedFormat);

	export let show = false;

	let memories = [];
	let loading = true;

	let showAddMemoryModal = false;
	let showEditMemoryModal = false;

	let selectedMemory = null;

	let showClearConfirmDialog = false;

	let onClearConfirmed = async () => {
		const res = await deleteMemoriesByUserId(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res && memories.length > 0) {
			toast.success($i18n.t('Memory cleared successfully'));
			memories = [];
		}
		showClearConfirmDialog = false;
	};

	$: if (show && memories.length === 0 && loading) {
		(async () => {
			memories = await getMemories(localStorage.token);
			loading = false;
		})();
	}
</script>

<Modal size="lg" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300); --px:1.25rem; --pt:1rem; --pb:0.25rem">
			<div style="--size:1.125rem; --weight:500; --as:center">{$i18n.t('Memory')}</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					style="--w:1.25rem; --h:1.25rem"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<div style="--d:flex; --fd:column; --w:100%; --px:1.25rem; --pb:1.25rem; --dark-c:var(--color-gray-200)">
			<div
				style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem; --h:28rem; --maxh:100vh; outline-style:solid; outline-width:1px; --radius:0.6rem; outline-color:var(--color-gray-100); outline-color:var(--color-gray-800); --mb:1rem; --mt:0.25rem"
			>
				{#if memories.length > 0}
					<div style="--ta:left; --size:0.875rem; --w:100%; --mb:1rem; --ofy:scroll">
						<div style="--pos:relative; --ofx:auto">
							<table style="--w:100%; --size:0.875rem; --ta:left; --c:var(--color-gray-600); --dark-c:var(--color-gray-400); table-layout:auto">
								<thead
									style="--size:0.6rem; --c:var(--color-gray-700); --tt:uppercase; --bgc:transparent; --dark-c:var(--color-gray-200); border-bottom-width:2px; --bc:var(--color-gray-50); --dark-bc:var(--color-gray-850)"
								>
									<tr>
										<th scope="col" style="--px:0.6rem; --py:0.5rem"> {$i18n.t('Name')} </th>
										<th scope="col" style="--px:0.6rem; --py:0.5rem; --d:none; --d-md:flex">
											{$i18n.t('Last Modified')}
										</th>
										<th scope="col" style="--px:0.6rem; --py:0.5rem; --ta:right" />
									</tr>
								</thead>
								<tbody style="--d:table">
									{#each memories as memory}
										<tr style=" --bc:var(--color-gray-50); --dark-bc:var(--color-gray-850); --ai:center">
											<td style="--d:table;--px:0.6rem; --py:0.25rem">
												<div style="--line-clamp:1">
													{memory.content}
												</div>
											</td>
											<td style="--d:table;--px:0.6rem; --py:0.25rem; --d:none; --d-md:flex; --h:2.5rem">
												<div style="--my:auto; --ws:nowrap">
													{dayjs(memory.updated_at * 1000).format('LLL')}
												</div>
											</td>
											<td style="--d:table;--px:0.6rem; --py:0.25rem">
												<div style="--d:flex; --jc:flex-end; --w:100%">
													<Tooltip content="Edit">
														<button
															style="--as:center; --w:fit-content; --size:0.875rem; --px:0.5rem; --py:0.5rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
															on:click={() => {
																selectedMemory = memory;
																showEditMemoryModal = true;
															}}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																fill="none"
																viewBox="0 0 24 24"
																stroke-width="1.5"
																stroke="currentColor"
																style="--w:1rem; --h:1rem"
	class="s-FoVA_WMOgxUD"
																><path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
																	class="s-FoVA_WMOgxUD"
																/></svg
															>
														</button>
													</Tooltip>

													<Tooltip content="Delete">
														<button
															style="--as:center; --w:fit-content; --size:0.875rem; --px:0.5rem; --py:0.5rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
															on:click={async () => {
																const res = await deleteMemoryById(
																	localStorage.token,
																	memory.id
																).catch((error) => {
																	toast.error(`${error}`);
																	return null;
																});

																if (res) {
																	toast.success($i18n.t('Memory deleted successfully'));
																	memories = await getMemories(localStorage.token);
																}
															}}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																fill="none"
																viewBox="0 0 24 24"
																stroke-width="1.5"
																stroke="currentColor"
																style="--w:1rem; --h:1rem"
															>
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
																/>
															</svg>
														</button>
													</Tooltip>
												</div>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>
				{:else}
					<div style="--ta:center; --d:flex; --h:100%; --size:0.875rem; --w:100%">
						<div style="--my:auto; --pb:2.5rem; --px:1rem; --w:100%; --c:var(--color-gray-500)">
							{$i18n.t('Memories accessible by LLMs will be shown here.')}
						</div>
					</div>
				{/if}
			</div>
			<div style="--d:flex; --size:0.875rem; --weight:500; --g:0.375rem">
				<button
					style="--px:0.875rem; --py:0.375rem; --weight:500; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); outline-style:solid; outline-width:1px; outline-color:var(--color-gray-300); outline-color:var(--color-gray-800); --radius:1.5rem"
					on:click={() => {
						showAddMemoryModal = true;
					}}>{$i18n.t('Add Memory')}</button
				>
				<button
					style="--px:0.875rem; --py:0.375rem; --weight:500; --c:#ef4444; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); outline-style:solid; outline-width:1px; outline-color:#fca5a5; outline-color:#991b1b; --radius:1.5rem"
					on:click={() => {
						if (memories.length > 0) {
							showClearConfirmDialog = true;
						} else {
							toast.error($i18n.t('No memories to clear'));
						}
					}}>{$i18n.t('Clear memory')}</button
				>
			</div>
		</div>
	</div>
</Modal>

<ConfirmDialog
	title={$i18n.t('Clear Memory')}
	message={$i18n.t('Are you sure you want to clear all memories? This action cannot be undone.')}
	show={showClearConfirmDialog}
	on:confirm={onClearConfirmed}
	on:cancel={() => {
		showClearConfirmDialog = false;
	}}
/>

<AddMemoryModal
	bind:show={showAddMemoryModal}
	on:save={async () => {
		memories = await getMemories(localStorage.token);
	}}
/>

<EditMemoryModal
	bind:show={showEditMemoryModal}
	memory={selectedMemory}
	on:save={async () => {
		memories = await getMemories(localStorage.token);
	}}
/>
