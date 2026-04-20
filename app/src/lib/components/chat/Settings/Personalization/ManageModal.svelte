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
	import Icon from '$lib/components/Icon.svelte';

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
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300); --px:1.2rem; --pt:1rem; --pb:0.2rem">
			<div style="--size:1.125rem; --weight:500; --as:center">{$i18n.t('Memory')}</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<Icon name="x-mark" className="size-[1.2rem]" />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --w:100%; --px:1.2rem; --pb:1.2rem; --dark-c:var(--color-gray-200)">
			<div
				style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem; --h:28rem; --maxh:100vh; outline-style:solid; outline-width:1px; --radius:0.6rem; outline-color:var(--color-gray-100); outline-color:var(--color-gray-800); --mb:1rem; --mt:0.2rem"
			>
				{#if memories.length > 0}
					<div style="--ta:left; --size:0.8rem; --w:100%; --mb:1rem; --ofy:scroll">
						<div style="--pos:relative; --ofx:auto">
							<table style="--w:100%; --size:0.8rem; --ta:left; --c:var(--color-gray-600); --dark-c:var(--color-gray-400); table-layout:auto">
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
											<td style="--d:table;--px:0.6rem; --py:0.2rem">
												<div style="--line-clamp:1">
													{memory.content}
												</div>
											</td>
											<td style="--d:table;--px:0.6rem; --py:0.2rem; --d:none; --d-md:flex; --h:2.5rem">
												<div style="--my:auto; --ws:nowrap">
													{dayjs(memory.updated_at * 1000).format('LLL')}
												</div>
											</td>
											<td style="--d:table;--px:0.6rem; --py:0.2rem">
												<div style="--d:flex; --jc:flex-end; --w:100%">
													<Tooltip content="Edit">
														<button
															style="--as:center; --w:fit-content; --size:0.8rem; --px:0.5rem; --py:0.5rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
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
															style="--as:center; --w:fit-content; --size:0.8rem; --px:0.5rem; --py:0.5rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
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
															<Icon name="trash-outline" className="size-4" />
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
					<div style="--ta:center; --d:flex; --h:100%; --size:0.8rem; --w:100%">
						<div style="--my:auto; --pb:2.5rem; --px:1rem; --w:100%; --c:var(--color-gray-500)">
							{$i18n.t('Memories accessible by LLMs will be shown here.')}
						</div>
					</div>
				{/if}
			</div>
			<div style="--d:flex; --size:0.8rem; --weight:500; --g:0.4rem">
				<button
					style="--px:0.8rem; --py:0.4rem; --weight:500; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); outline-style:solid; outline-width:1px; outline-color:var(--color-gray-300); outline-color:var(--color-gray-800); --radius:1.5rem"
					on:click={() => {
						showAddMemoryModal = true;
					}}>{$i18n.t('Add Memory')}</button
				>
				<button
					style="--px:0.8rem; --py:0.4rem; --weight:500; --c:#ef4444; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); outline-style:solid; outline-width:1px; outline-color:#fca5a5; outline-color:#991b1b; --radius:1.5rem"
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
