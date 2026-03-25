<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';

	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	dayjs.extend(localizedFormat);

	import { deleteChatById } from '$lib/apis/chats';

	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import Spinner from '../common/Spinner.svelte';
	import Loader from '../common/Loader.svelte';
	import XMark from '../icons/XMark.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	export let title = 'Chats';
	export let emptyPlaceholder = '';
	export let shareUrl = false;

	export let query = '';

	export let orderBy = 'updated_at';
	export let direction = 'desc'; // 'asc' or 'desc'

	export let chatList = null;
	export let allChatsLoaded = false;
	export let chatListLoading = false;

	let selectedChatId = null;
	let selectedIdx = 0;
	let showDeleteConfirmDialog = false;

	export let onUpdate = () => {};

	export let loadHandler: null | Function = null;
	export let unarchiveHandler: null | Function = null;

	const setSortKey = (key) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = 'asc';
		}
	};

	const deleteHandler = async (chatId) => {
		const res = await deleteChatById(localStorage.token, chatId).catch((error) => {
			toast.error(`${error}`);
		});

		onUpdate();
	};
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		if (selectedChatId) {
			deleteHandler(selectedChatId);
			selectedChatId = null;
		}
	}}
/>

<Modal size="lg" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300); --px:1.2rem; --pt:1rem; --pb:0.2rem">
			<div style="--size:1.125rem; --weight:500; --as:center">{title}</div>
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
					style="--w:1.2rem; --h:1.2rem"
				>
					<path
						fill-rule="evenodd"
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		</div>

		<div style="--d:flex; --fd:column; --w:100%; --px:1.2rem; --pb:1rem; --dark-c:var(--color-gray-200)">
			<div style="--d:flex; --w:100%; --g:0.5rem; --mb:0.125rem">
				<div style="--d:flex; --fx:1 1 0%">
					<div style="--as:center; --ml:0.2rem; --mr:0.6rem">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							style="--w:1rem; --h:1rem"
						>
							<path
								fill-rule="evenodd"
								d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<input
						style="--w:100%; --size:0.8rem; --pr:1rem; --py:0.2rem; --btrr:0.6rem; --bbrr:0.6rem; --oe:none; --bgc:transparent"
						bind:value={query}
						placeholder={$i18n.t('Search Chats')}
					/>

					{#if query}
						<div style="--as:center; --pl:0.4rem; --pr:0.2rem; --translatey:0.5px; --btlr:0.6rem; --bblr:0.6rem; --bgc:transparent">
							<button
								style="--p:0.125rem; --radius:9999px; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-900); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								on:click={() => {
									query = '';
									selectedIdx = 0;
								}}
							>
								<XMark className="size-3" strokeWidth="2" />
							</button>
						</div>
					{/if}
				</div>
			</div>

			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				{#if chatList}
					<div style="--w:100%">
						{#if chatList.length > 0}
							<div style="--d:flex; --size:0.6rem; --weight:500; --mb:0.4rem">
								<button
									style="--px:0.4rem; --py:0.2rem; --cur:pointer; --us:none; --fb:60%"
									on:click={() => setSortKey('title')}
								>
									<div style="--d:flex; --g:0.4rem; --ai:center">
										{$i18n.t('Title')}

										{#if orderBy === 'title'}
											<span style="--weight:400"
												>{#if direction === 'asc'}
													<ChevronUp className="size-2" />
												{:else}
													<ChevronDown className="size-2" />
												{/if}
											</span>
										{:else}
											<span style="--v:hidden">
												<ChevronUp className="size-2" />
											</span>
										{/if}
									</div>
								</button>
								<button
									style="--px:0.4rem; --py:0.2rem; --cur:pointer; --us:none; --d:none; --d-sm:flex; --fb-sm:40%; --jc:flex-end"
									on:click={() => setSortKey('updated_at')}
								>
									<div style="--d:flex; --g:0.4rem; --ai:center">
										{$i18n.t('Updated at')}

										{#if orderBy === 'updated_at'}
											<span style="--weight:400"
												>{#if direction === 'asc'}
													<ChevronUp className="size-2" />
												{:else}
													<ChevronDown className="size-2" />
												{/if}
											</span>
										{:else}
											<span style="--v:hidden">
												<ChevronUp className="size-2" />
											</span>
										{/if}
									</div>
								</button>
							</div>
						{/if}
						<div style="--ta:left; --size:0.8rem; --w:100%; --mb:0.6rem; --maxh:22rem; --ofy:scroll">
							{#if chatList.length === 0}
								<div
									style="--size:0.6rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --ta:center; --px:1.2rem; --minh:5rem; --w:100%; --h:100%; --d:flex; --jc:center; --ai:center"
								>
									{$i18n.t('No results found')}
								</div>
							{/if}

							{#each chatList as chat, idx (chat.id)}
								{#if (idx === 0 || (idx > 0 && chat.time_range !== chatList[idx - 1].time_range)) && chat?.time_range}
									<div
										style="--w:100%; --size:0.6rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-500); --weight:500;  --px:0.5rem"
	class="{idx === 0
											? ''
											: 'pt-5'}"
									>
										{$i18n.t(chat.time_range)}
										<!-- localisation keys for time_range to be recognized from the i18next parser (so they don't get automatically removed):
							{$i18n.t('Today')}
							{$i18n.t('Yesterday')}
							{$i18n.t('Previous 7 days')}
							{$i18n.t('Previous 30 days')}
							{$i18n.t('January')}
							{$i18n.t('February')}
							{$i18n.t('March')}
							{$i18n.t('April')}
							{$i18n.t('May')}
							{$i18n.t('June')}
							{$i18n.t('July')}
							{$i18n.t('August')}
							{$i18n.t('September')}
							{$i18n.t('October')}
							{$i18n.t('November')}
							{$i18n.t('December')}
							-->
									</div>
								{/if}

								<div
									style="--w:100%; --d:flex; --jc:space-between; --ai:center; --radius:0.5rem; --size:0.8rem; --py:0.5rem; --px:0.6rem; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-850)"
									draggable="false"
								>
									<a
										style="--fb:60%"
										href={shareUrl ? `/s/${chat.id}` : `/c/${chat.id}`}
										on:click={() => (show = false)}
									>
										<div style="text-overflow:ellipsis; --line-clamp:1; --w:100%">
											{chat?.title}
										</div>
									</a>

									<div style="--fb:40%; --d:flex; --ai:center; --jc:flex-end">
										<div style="--d:none; --d-sm:flex; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --size:0.6rem">
											{dayjs(chat?.updated_at * 1000).calendar()}
										</div>

										<div style="--d:flex; --jc:flex-end; --pl:0.625rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300)">
											{#if unarchiveHandler}
												<Tooltip content={$i18n.t('Unarchive Chat')}>
													<button
														style="--as:center; --w:fit-content; --px:0.2rem; --size:0.8rem; --radius:0.6rem"
														on:click={async (e) => {
															e.stopImmediatePropagation();
															e.stopPropagation();
															unarchiveHandler(chat.id);
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
																d="M9 8.25H7.5a2.25 2.25 0 0 0-2.25 2.25v9a2.25 2.25 0 0 0 2.25 2.25h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25H15m0-3-3-3m0 0-3 3m3-3V15"
															/>
														</svg>
													</button>
												</Tooltip>
											{/if}

											<Tooltip content={$i18n.t('Delete Chat')}>
												<button
													style="--as:center; --w:fit-content; --px:0.2rem; --size:0.8rem; --radius:0.6rem"
													on:click={async (e) => {
														e.stopImmediatePropagation();
														e.stopPropagation();
														selectedChatId = chat.id;
														showDeleteConfirmDialog = true;
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
									</div>
								</div>
							{/each}

							{#if !allChatsLoaded && loadHandler}
								<Loader
									on:visible={(e) => {
										if (!chatListLoading) {
											loadHandler();
										}
									}}
								>
									<div
										style="--w:100%; --d:flex; --jc:center; --py:0.2rem; --size:0.6rem; animation:pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; --ai:center; --g:0.5rem"
									>
										<Spinner className=" size-4" />
										<div class=" ">Loading...</div>
									</div>
								</Loader>
							{/if}
						</div>

						{#if query === ''}
							<slot name="footer"></slot>
						{/if}
					</div>
				{:else}
					<div style="--w:100%; --h:100%; --d:flex; --jc:center; --ai:center; --minh:5rem">
						<Spinner className="size-5" />
					</div>
				{/if}

				<!-- {#if chats !== null}
					{#if chats.length > 0}
						<div style="--w:100%">
							<div style="--ta:left; --size:0.8rem; --w:100%; --mb:0.6rem; --maxh:22rem; --ofy:scroll">
								<div style="--pos:relative; --ofx:auto">
									<table
										style="--w:100%; --size:0.8rem; --ta:left; --c:var(--color-gray-600); --dark-c:var(--color-gray-400); table-layout:auto"
									>
										<thead
											style="--size:0.6rem; --c:var(--color-gray-700); --tt:uppercase; --bgc:transparent; --dark-c:var(--color-gray-200); --bc:var(--color-gray-50); --dark-bc:var(--color-gray-850)"
	class="border-b-1"
										>
											<tr>
												<th scope="col" style="--px:0.6rem; --py:0.5rem"> {$i18n.t('Name')} </th>
												<th scope="col" style="--px:0.6rem; --py:0.5rem; --d:none; --d-md:flex">
													{$i18n.t('Created At')}
												</th>
												<th scope="col" style="--px:0.6rem; --py:0.5rem; --ta:right" />
											</tr>
										</thead>
										<tbody style="--d:table">
											{#each chats as chat, idx}
												<tr
													style="--bgc:transparent; --dark-bgc:var(--color-gray-900); --bc:var(--color-gray-50); --dark-bc:var(--color-gray-850); --size:0.6rem"
	class="{idx !== chats.length - 1 &&
														'border-b'}"
												>
													<td style="--d:table;--px:0.6rem; --py:0.2rem; --w:66.666667%">
														<a href="/c/{chat.id}" target="_blank">
															<div style="--hvr-td:underline; --line-clamp:1">
																{chat.title}
															</div>
														</a>
													</td>

													<td style="--d:table;--px:0.6rem; --py:0.2rem; --d:none; --d-md:flex; --h:2.5rem">
														<div style="--my:auto">
															{dayjs(chat.created_at * 1000).format('LLL')}
														</div>
													</td>

													<td style="--d:table;--px:0.6rem; --py:0.2rem; --ta:right">
														<div style="--d:flex; --jc:flex-end; --w:100%">
															{#if unarchiveHandler}
																<Tooltip content={$i18n.t('Unarchive Chat')}>
																	<button
																		style="--as:center; --w:fit-content; --size:0.8rem; --px:0.5rem; --py:0.5rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
																		on:click={async () => {
																			unarchiveHandler(chat.id);
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
																				d="M9 8.25H7.5a2.25 2.25 0 0 0-2.25 2.25v9a2.25 2.25 0 0 0 2.25 2.25h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25H15m0-3-3-3m0 0-3 3m3-3V15"
																			/>
																		</svg>
																	</button>
																</Tooltip>
															{/if}

															<Tooltip content={$i18n.t('Delete Chat')}>
																<button
																	style="--as:center; --w:fit-content; --size:0.8rem; --px:0.5rem; --py:0.5rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
																	on:click={async () => {
																		deleteHandler(chat.id);
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

							<slot name="footer"></slot>
						</div>
					{:else}
						<div style="--ta:left; --size:0.8rem; --w:100%; --mb:2rem">
							{emptyPlaceholder || $i18n.t('No chats found.')}
						</div>
					{/if}
				{:else}
					<div style="--w:100%; --h:100%">
						<Spinner />
					</div>
				{/if} -->
			</div>
		</div>
	</div>
</Modal>
