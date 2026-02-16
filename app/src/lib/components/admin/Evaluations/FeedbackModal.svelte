<script lang="ts">
	import Modal from '$lib/components/common/Modal.svelte';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');
	import XMark from '$lib/components/icons/XMark.svelte';
	import { getFeedbackById } from '$lib/apis/evaluations';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let show = false;
	export let selectedFeedback = null;

	export let onClose: () => void = () => {};

	let loaded = false;

	let feedbackData = null;

	const close = () => {
		show = false;
		onClose();
	};

	const init = async () => {
		loaded = false;
		feedbackData = null;
		if (selectedFeedback) {
			feedbackData = await getFeedbackById(localStorage.token, selectedFeedback.id).catch((err) => {
				return null;
			});

			console.log('Feedback Data:', selectedFeedback, feedbackData);
		}
		loaded = true;
	};

	$: if (show) {
		init();
	}
</script>

<Modal size="sm" bind:show>
	{#if selectedFeedback}
		<div>
			<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300, #cdcdcd); --px:1.25rem; --pt:1rem; --pb:0.5rem">
				<div style="--size:1.125rem; --weight:500; --as:center">
					{$i18n.t('Feedback Details')}
				</div>
				<button style="--as:center" on:click={close} aria-label="Close">
					<XMark className={'size-5'} />
				</button>
			</div>

			<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1.25rem; --pb:1rem; --g-md:1rem; --dark-c:var(--color-gray-200, #e3e3e3)">
				{#if loaded}
					<div style="--d:flex; --fd:column; --w:100%">
						{#if feedbackData}
							{@const messageId = feedbackData?.meta?.message_id}
							{@const messages = feedbackData?.snapshot?.chat?.chat?.history.messages}

							{#if messages[messages[messageId]?.parentId]}
								<div style="--d:flex; --fd:column; --w:100%; --mb:0.5rem">
									<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">{$i18n.t('Prompt')}</div>

									<div style="--fx:1 1 0%; --size:0.75rem; --ws:pre-line; --wb:break-word; overflow-wrap:break-word">
										<span>{messages[messages[messageId]?.parentId]?.content || '-'}</span>
									</div>
								</div>
							{/if}

							{#if messages[messageId]}
								<div style="--d:flex; --fd:column; --w:100%; --mb:0.5rem">
									<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">{$i18n.t('Response')}</div>
									<div
										style="--fx:1 1 0%; --size:0.75rem; --ws:pre-line; --wb:break-word; overflow-wrap:break-word; --maxh:8rem; --ofy:auto"
									>
										<span>{messages[messageId]?.content || '-'}</span>
									</div>
								</div>
							{/if}
						{/if}

						<div style="--d:flex; --fd:column; --w:100%; --mb:0.5rem">
							<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">{$i18n.t('Rating')}</div>

							<div style="--fx:1 1 0%; --size:0.75rem">
								<span>{selectedFeedback?.data?.details?.rating ?? '-'}</span>
							</div>
						</div>
						<div style="--d:flex; --fd:column; --w:100%; --mb:0.5rem">
							<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">{$i18n.t('Reason')}</div>

							<div style="--fx:1 1 0%; --size:0.75rem">
								<span>{selectedFeedback?.data?.reason || '-'}</span>
							</div>
						</div>

						<div style="--d:flex; --fd:column; --w:100%; --mb:0.5rem">
							<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">{$i18n.t('Comment')}</div>

							<div style="--fx:1 1 0%; --size:0.75rem">
								<span>{selectedFeedback?.data?.comment || '-'}</span>
							</div>
						</div>

						{#if selectedFeedback?.data?.tags && selectedFeedback?.data?.tags.length}
							<div style="--mb:0.5rem; --mx:-0.25rem">
								<div style="--d:flex; --fw:wrap; --g:0.25rem; --mt:0.25rem">
									{#each selectedFeedback?.data?.tags as tag}
										<span style="--px:0.5rem; --py:0.125rem; --radius:9999px; --bgc:var(--color-gray-100, #ececec); --dark-bgc:var(--color-gray-850, #262626); --size:9px"
											>{tag}</span
										>
									{/each}
								</div>
							</div>
						{/if}

						<div style="--d:flex; --jc:flex-end; --pt:0.5rem">
							<button
								style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900, #171717); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100, #ececec); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
								type="button"
								on:click={close}
							>
								{$i18n.t('Close')}
							</button>
						</div>
					</div>
				{:else}
					<div style="--d:flex; --ai:center; --jc:center; --w:100%; --h:8rem">
						<Spinner className={'size-5'} />
					</div>
				{/if}
			</div>
		</div>
	{/if}
</Modal>
