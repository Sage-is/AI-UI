<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	import Icon from '$lib/components/Icon.svelte';
	const { saveAs } = fileSaver;

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { deleteFeedbackById, exportAllFeedbacks, getAllFeedbacks } from '$lib/apis/evaluations';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
		import Badge from '$lib/components/common/Badge.svelte';
		import Pagination from '$lib/components/common/Pagination.svelte';
	import FeedbackMenu from './FeedbackMenu.svelte';
	import FeedbackModal from './FeedbackModal.svelte';

			import { WEBUI_BASE_URL } from '$lib/constants';

	export let feedbacks = [];

	let page = 1;
	$: paginatedFeedbacks = sortedFeedbacks.slice((page - 1) * 10, page * 10);

	let orderBy: string = 'updated_at';
	let direction: 'asc' | 'desc' = 'desc';

	type Feedback = {
		id: string;
		data: {
			rating: number;
			model_id: string;
			sibling_model_ids: string[] | null;
			reason: string;
			comment: string;
			tags: string[];
		};
		user: {
			name: string;
			profile_image_url: string;
		};
		updated_at: number;
	};

	type ModelStats = {
		rating: number;
		won: number;
		lost: number;
	};

	function setSortKey(key: string) {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			if (key === 'user' || key === 'model_id') {
				direction = 'asc';
			} else {
				direction = 'desc';
			}
		}
		page = 1;
	}

	$: sortedFeedbacks = [...feedbacks].sort((a, b) => {
		let aVal, bVal;

		switch (orderBy) {
			case 'user':
				aVal = a.user?.name || '';
				bVal = b.user?.name || '';
				return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
			case 'model_id':
				aVal = a.data.model_id || '';
				bVal = b.data.model_id || '';
				return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
			case 'rating':
				aVal = a.data.rating;
				bVal = b.data.rating;
				return direction === 'asc' ? aVal - bVal : bVal - aVal;
			case 'updated_at':
				aVal = a.updated_at;
				bVal = b.updated_at;
				return direction === 'asc' ? aVal - bVal : bVal - aVal;
			default:
				return 0;
		}
	});

	let showFeedbackModal = false;
	let selectedFeedback = null;

	const openFeedbackModal = (feedback) => {
		showFeedbackModal = true;
		selectedFeedback = feedback;
	};

	const closeFeedbackModal = () => {
		showFeedbackModal = false;
		selectedFeedback = null;
	};

	//////////////////////
	//
	// CRUD operations
	//
	//////////////////////

	const deleteFeedbackHandler = async (feedbackId: string) => {
		const response = await deleteFeedbackById(localStorage.token, feedbackId).catch((err) => {
			toast.error(err);
			return null;
		});
		if (response) {
			feedbacks = feedbacks.filter((f) => f.id !== feedbackId);
		}
	};

	const shareHandler = async () => {
		toast.success($i18n.t('Redirecting you to Sage.is AI Community'));

		// remove snapshot from feedbacks
		const feedbacksToShare = feedbacks.map((f) => {
			const { snapshot, user, ...rest } = f;
			return rest;
		});
		console.log(feedbacksToShare);

		const url = 'https://sage.is';
		const tab = await window.open(`${url}/leaderboard`, '_blank');

		// Define the event handler function
		const messageHandler = (event) => {
			if (event.origin !== url) return;
			if (event.data === 'loaded') {
				tab.postMessage(JSON.stringify(feedbacksToShare), '*');

				// Remove the event listener after handling the message
				window.removeEventListener('message', messageHandler);
			}
		};

		window.addEventListener('message', messageHandler, false);
	};

	const exportHandler = async () => {
		const _feedbacks = await exportAllFeedbacks(localStorage.token).catch((err) => {
			toast.error(err);
			return null;
		});

		if (_feedbacks) {
			let blob = new Blob([JSON.stringify(_feedbacks)], {
				type: 'application/json'
			});
			saveAs(blob, `feedback-history-export-${Date.now()}.json`);
		}
	};
</script>

<FeedbackModal bind:show={showFeedbackModal} {selectedFeedback} onClose={closeFeedbackModal} />

<div style="--mt:0.125rem; --mb:0.5rem; --g:0.2rem; --d:flex; --fd:row; --jc:space-between">
	<div style="--d:flex; --as-md:center; --size:1.125rem; --weight:500; --px:0.125rem">
		{$i18n.t('Feedback History')}

		<div style="--d:flex; --as:center; --w:1px; --h:1.5rem; --mx:0.625rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850)" />

		<span style="--size:1.125rem; --weight:500; --c:var(--color-gray-500); --dark-c:var(--color-gray-300)">{feedbacks.length}</span>
	</div>

	{#if feedbacks.length > 0}
		<div>
			<Tooltip content={$i18n.t('Export')}>
				<button
					style="--p:0.5rem; --radius:0.6rem; --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-900); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --size:0.8rem; --d:flex; --ai:center; --g:0.2rem"
					on:click={() => {
						exportHandler();
					}}
				>
					<Icon name="arrow-down-tray" className="size-3" />
				</button>
			</Tooltip>
		</div>
	{/if}
</div>

<div
	style="--pos:relative; --ws:nowrap; --ofx:auto; --maxw:100%; --radius:0.125rem; --pt:0.125rem"
	class="scrollbar-hidden"
>
	{#if (feedbacks ?? []).length === 0}
		<div style="--ta:center; --size:0.6rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --py:0.2rem">
			{$i18n.t('No feedbacks found')}
		</div>
	{:else}
		<table
			style="--w:100%; --size:0.8rem; --ta:left; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); table-layout:auto; --maxw:100%; --radius:0.125rem"
		>
			<thead
				style="--size:0.6rem; --c:var(--color-gray-700); --tt:uppercase; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --dark-c:var(--color-gray-400); --translatey:-0.125rem"
			>
				<tr class="">
					<th
						scope="col"
						style="--px:0.6rem; --py:0.4rem; --cur:pointer; --us:none; --w:0.6rem"
						on:click={() => setSortKey('user')}
					>
						<div style="--d:flex; --g:0.4rem; --ai:center; --jc:flex-end">
							{$i18n.t('User')}
							{#if orderBy === 'user'}
								<span style="--weight:400">
									{#if direction === 'asc'}
										<Icon name="chevron-up" className="size-2" />
									{:else}
										<Icon name="chevron-down" className="size-2" />
									{/if}
								</span>
							{:else}
								<span style="--v:hidden">
									<Icon name="chevron-up" className="size-2" />
								</span>
							{/if}
						</div>
					</th>

					<th
						scope="col"
						style="--px:0.6rem; --pr:0.4rem; --cur:pointer; --us:none"
						on:click={() => setSortKey('model_id')}
					>
						<div style="--d:flex; --g:0.4rem; --ai:center">
							{$i18n.t('Models')}
							{#if orderBy === 'model_id'}
								<span style="--weight:400">
									{#if direction === 'asc'}
										<Icon name="chevron-up" className="size-2" />
									{:else}
										<Icon name="chevron-down" className="size-2" />
									{/if}
								</span>
							{:else}
								<span style="--v:hidden">
									<Icon name="chevron-up" className="size-2" />
								</span>
							{/if}
						</div>
					</th>

					<th
						scope="col"
						style="--px:0.6rem; --py:0.4rem; --ta:right; --cur:pointer; --us:none; --w:fit-content"
						on:click={() => setSortKey('rating')}
					>
						<div style="--d:flex; --g:0.4rem; --ai:center; --jc:flex-end">
							{$i18n.t('Result')}
							{#if orderBy === 'rating'}
								<span style="--weight:400">
									{#if direction === 'asc'}
										<Icon name="chevron-up" className="size-2" />
									{:else}
										<Icon name="chevron-down" className="size-2" />
									{/if}
								</span>
							{:else}
								<span style="--v:hidden">
									<Icon name="chevron-up" className="size-2" />
								</span>
							{/if}
						</div>
					</th>

					<th
						scope="col"
						style="--px:0.6rem; --py:0.4rem; --ta:right; --cur:pointer; --us:none; --w:0"
						on:click={() => setSortKey('updated_at')}
					>
						<div style="--d:flex; --g:0.4rem; --ai:center; --jc:flex-end">
							{$i18n.t('Updated At')}
							{#if orderBy === 'updated_at'}
								<span style="--weight:400">
									{#if direction === 'asc'}
										<Icon name="chevron-up" className="size-2" />
									{:else}
										<Icon name="chevron-down" className="size-2" />
									{/if}
								</span>
							{:else}
								<span style="--v:hidden">
									<Icon name="chevron-up" className="size-2" />
								</span>
							{/if}
						</div>
					</th>

					<th scope="col" style="--px:0.6rem; --py:0.4rem; --ta:right; --cur:pointer; --us:none; --w:0"> </th>
				</tr>
			</thead>
			<tbody style="--d:table">
				{#each paginatedFeedbacks as feedback (feedback.id)}
					<tr
						style="--bgc:#fff; --dark-bgc:var(--color-gray-900); --dark-bc:var(--color-gray-850); --size:0.6rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:rgb(38 38 38 / 0.5); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={() => openFeedbackModal(feedback)}
					>
						<td style="--d:table;--py:0.125rem; --ta:right; --weight:600">
							<div style="--d:flex; --jc:center">
								<Tooltip content={feedback?.user?.name}>
									<div style="--fs:0">
										<img
											src={feedback?.user?.profile_image_url ?? `${WEBUI_BASE_URL}/static/user.png`}
											alt={feedback?.user?.name}
											style="--w:1.2rem; --h:1.2rem; --radius:9999px; --objf:cover; --fs:0"
										/>
									</div>
								</Tooltip>
							</div>
						</td>

						<td style="--d:table;--py:0.2rem; --pl:0.6rem; --d:flex; --fd:column">
							<div style="--d:flex; --fd:column; --ai:flex-start; --g:0.125rem; --h:100%">
								<div style="--d:flex; --fd:column; --h:100%">
									{#if feedback.data?.sibling_model_ids}
										<div style="--weight:600; --c:var(--color-gray-600); --dark-c:var(--color-gray-400); --fx:1 1 0%">
											{feedback.data?.model_id}
										</div>

										<Tooltip content={feedback.data.sibling_model_ids.join(', ')}>
											<div style="--size:0.65rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400); --line-clamp:1">
												{#if feedback.data.sibling_model_ids.length > 2}
													<!-- {$i18n.t('and {{COUNT}} more')} -->
													{feedback.data.sibling_model_ids.slice(0, 2).join(', ')}, {$i18n.t(
														'and {{COUNT}} more',
														{ COUNT: feedback.data.sibling_model_ids.length - 2 }
													)}
												{:else}
													{feedback.data.sibling_model_ids.join(', ')}
												{/if}
											</div>
										</Tooltip>
									{:else}
										<div
											style="--size:0.8rem; --weight:500; --c:var(--color-gray-600); --dark-c:var(--color-gray-400); --fx:1 1 0%; --py:0.4rem"
										>
											{feedback.data?.model_id}
										</div>
									{/if}
								</div>
							</div>
						</td>
						<td style="--d:table;--px:0.6rem; --py:0.2rem; --ta:right; --weight:500; --c:var(--color-gray-900); --dark-c:#fff; --w:max-content">
							<div style="--d:flex; --jc:flex-end">
								{#if feedback.data.rating.toString() === '1'}
									<Badge type="info" content={$i18n.t('Won')} />
								{:else if feedback.data.rating.toString() === '0'}
									<Badge type="muted" content={$i18n.t('Draw')} />
								{:else if feedback.data.rating.toString() === '-1'}
									<Badge type="error" content={$i18n.t('Lost')} />
								{/if}
							</div>
						</td>

						<td style="--d:table;--px:0.6rem; --py:0.2rem; --ta:right; --weight:500">
							{dayjs(feedback.updated_at * 1000).fromNow()}
						</td>

						<td style="--d:table;--px:0.6rem; --py:0.2rem; --ta:right; --weight:600" on:click={(e) => e.stopPropagation()}>
							<FeedbackMenu
								on:delete={(e) => {
									deleteFeedbackHandler(feedback.id);
								}}
							>
								<button
									style="--as:center; --w:fit-content; --size:0.8rem; --p:0.4rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
								>
									<Icon name="ellipsis-horizontal" />
								</button>
							</FeedbackMenu>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</div>

{#if feedbacks.length > 0}
	<div style="--d:flex; --fd:column; --jc:flex-end; --w:100%; --ta:right; --g:0.2rem">
		<div style="--line-clamp:1; --c:var(--color-gray-500); --size:0.6rem">
			{$i18n.t('Help us create the best community leaderboard by sharing your feedback history!')}
		</div>

		<div style="--d:flex; --g:0.2rem; --ml:auto">
			<Tooltip
				content={$i18n.t(
					'To protect your privacy, only ratings, model IDs, tags, and metadata are shared from your feedback—your chat logs remain private and are not included.'
				)}
			>
				<button
					style="--d:flex; --size:0.6rem; --ai:center; --px:0.6rem; --py:0.4rem; --radius:0.6rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					on:click={async () => {
						shareHandler();
					}}
				>
					<div style="--as:center; --mr:0.5rem; --weight:500; --line-clamp:1">
						{$i18n.t('Share to Sage.is AI Community')}
					</div>

					<div style="--as:center">
						<Icon name="cloud-arrow-up" className="size-3" strokeWidth="3" />
					</div>
				</button>
			</Tooltip>
		</div>
	</div>
{/if}

{#if feedbacks.length > 10}
	<Pagination bind:page count={feedbacks.length} perPage={10} />
{/if}
