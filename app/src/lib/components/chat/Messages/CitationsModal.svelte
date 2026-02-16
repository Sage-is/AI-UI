<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let citation;
	export let showPercentage = false;
	export let showRelevance = true;

	let mergedDocuments = [];

	function calculatePercentage(distance: number) {
		if (typeof distance !== 'number') return null;
		if (distance < 0) return 0;
		if (distance > 1) return 100;
		return Math.round(distance * 10000) / 100;
	}

	function getRelevanceColor(percentage: number) {
		if (percentage >= 80)
			return 'bg-green-200 dark:bg-green-800 text-green-800 dark:text-green-200';
		if (percentage >= 60)
			return 'bg-yellow-200 dark:bg-yellow-800 text-yellow-800 dark:text-yellow-200';
		if (percentage >= 40)
			return 'bg-orange-200 dark:bg-orange-800 text-orange-800 dark:text-orange-200';
		return 'bg-red-200 dark:bg-red-800 text-red-800 dark:text-red-200';
	}

	$: if (citation) {
		mergedDocuments = citation.document?.map((c, i) => {
			return {
				source: citation.source,
				document: c,
				metadata: citation.metadata?.[i],
				distance: citation.distances?.[i]
			};
		});
		if (mergedDocuments.every((doc) => doc.distance !== undefined)) {
			mergedDocuments = mergedDocuments.sort(
				(a, b) => (b.distance ?? Infinity) - (a.distance ?? Infinity)
			);
		}
	}

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};
</script>

<Modal size="lg" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300, #cdcdcd); --px:1.25rem; --pt:1rem; --pb:0.5rem">
			<div style="--size:1.125rem; --weight:500; --as:center; --tt:capitalize">
				{$i18n.t('Citation')}
			</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1.5rem; --pb:1.25rem; --g-md:1rem">
			<div
				style="--d:flex; --fd:column; --w:100%; --dark-c:var(--color-gray-200, #e3e3e3); --ofy:scroll; --maxh:22rem"
	class="scrollbar-hidden"
			>
				{#each mergedDocuments as document, documentIdx}
					<div style="--d:flex; --fd:column; --w:100%">
						<div style="--size:0.875rem; --weight:500; --dark-c:var(--color-gray-300, #cdcdcd)">
							{$i18n.t('Source')}
						</div>

						{#if document.source?.name}
							<Tooltip
								className="w-fit"
								content={$i18n.t('Open file')}
								placement="top-start"
								tippyOptions={{ duration: [500, 0] }}
							>
								<div style="--size:0.875rem; --dark-c:var(--color-gray-400, #b4b4b4); --d:flex; --ai:center; --g:0.5rem; --w:fit-content">
									<a
										style="--hvr-c:var(--color-gray-500, #9b9b9b); --hvr-dark-c:var(--color-gray-100, #ececec); --td:underline; --fg:1"
										href={document?.metadata?.file_id
											? `${WEBUI_API_BASE_URL}/files/${document?.metadata?.file_id}/content${document?.metadata?.page !== undefined ? `#page=${document.metadata.page + 1}` : ''}`
											: document.source?.url?.includes('http')
												? document.source.url
												: `#`}
										target="_blank"
									>
										{decodeString(document?.metadata?.name ?? document.source.name)}
									</a>
									{#if Number.isInteger(document?.metadata?.page)}
										<span style="--size:0.75rem; --c:var(--color-gray-500, #9b9b9b); --dark-c:var(--color-gray-400, #b4b4b4)">
											({$i18n.t('page')}
											{document.metadata.page + 1})
										</span>
									{/if}
								</div>
							</Tooltip>
							{#if document.metadata?.parameters}
								<div style="--size:0.875rem; --weight:500; --dark-c:var(--color-gray-300, #cdcdcd); --mt:0.5rem">
									{$i18n.t('Parameters')}
								</div>
								<pre
									style="--size:0.875rem; --dark-c:var(--color-gray-400, #b4b4b4); --bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-800, #333); --p:0.5rem; --radius:0.375rem; --of:auto; --maxh:10rem">{JSON.stringify(
										document.metadata.parameters,
										null,
										2
									)}</pre>
							{/if}
							{#if showRelevance}
								<div style="--size:0.875rem; --weight:500; --dark-c:var(--color-gray-300, #cdcdcd); --mt:0.5rem">
									{$i18n.t('Relevance')}
								</div>
								{#if document.distance !== undefined}
									<Tooltip
										className="w-fit"
										content={$i18n.t('Semantic distance to query')}
										placement="top-start"
										tippyOptions={{ duration: [500, 0] }}
									>
										<div style="--size:0.875rem; --my:0.25rem; --dark-c:var(--color-gray-400, #b4b4b4); --d:flex; --ai:center; --g:0.5rem; --w:fit-content">
											{#if showPercentage}
												{@const percentage = calculatePercentage(document.distance)}

												{#if typeof percentage === 'number'}
													<span
														class={`px-1 rounded-sm font-medium ${getRelevanceColor(percentage)}`}
													>
														{percentage.toFixed(2)}%
													</span>
												{/if}

												{#if typeof document?.distance === 'number'}
													<span style="--c:var(--color-gray-500, #9b9b9b); --dark-c:var(--color-gray-500, #9b9b9b)">
														({(document?.distance ?? 0).toFixed(4)})
													</span>
												{/if}
											{:else if typeof document?.distance === 'number'}
												<span style="--c:var(--color-gray-500, #9b9b9b); --dark-c:var(--color-gray-500, #9b9b9b)">
													({(document?.distance ?? 0).toFixed(4)})
												</span>
											{/if}
										</div>
									</Tooltip>
								{:else}
									<div style="--size:0.875rem; --dark-c:var(--color-gray-400, #b4b4b4)">
										{$i18n.t('No distance available')}
									</div>
								{/if}
							{/if}
						{:else}
							<div style="--size:0.875rem; --dark-c:var(--color-gray-400, #b4b4b4)">
								{$i18n.t('No source available')}
							</div>
						{/if}
					</div>
					<div style="--d:flex; --fd:column; --w:100%">
						<div style="--size:0.875rem; --weight:500; --dark-c:var(--color-gray-300, #cdcdcd); --mt:0.5rem">
							{$i18n.t('Content')}
						</div>
						{#if document.metadata?.html}
							<iframe
								style="--w:100%; --bw:0; --h:auto; --radius:0"
								sandbox="allow-scripts allow-forms allow-same-origin"
								srcdoc={document.document}
								title={$i18n.t('Content')}
							></iframe>
						{:else}
							<pre style="--size:0.875rem; --dark-c:var(--color-gray-400, #b4b4b4); --ws:pre-line">
                {document.document}
              </pre>
						{/if}
					</div>

					{#if documentIdx !== mergedDocuments.length - 1}
						<hr style="--bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-850, #262626); --my:0.75rem" />
					{/if}
				{/each}
			</div>
		</div>
	</div>
</Modal>
