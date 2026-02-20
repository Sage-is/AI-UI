<script lang="ts">
	import { getContext } from 'svelte';
	import CitationsModal from './CitationsModal.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';

	const i18n = getContext('i18n');

	export let id = '';
	export let chatId = '';
	export let sources = [];

	let citations = [];
	let showPercentage = false;
	let showRelevance = true;

	let showCitationModal = false;
	let selectedCitation: any = null;
	let isCollapsibleOpen = false;

	function calculateShowRelevance(sources: any[]) {
		const distances = sources.flatMap((citation) => citation.distances ?? []);
		const inRange = distances.filter((d) => d !== undefined && d >= -1 && d <= 1).length;
		const outOfRange = distances.filter((d) => d !== undefined && (d < -1 || d > 1)).length;

		if (distances.length === 0) {
			return false;
		}

		if (
			(inRange === distances.length - 1 && outOfRange === 1) ||
			(outOfRange === distances.length - 1 && inRange === 1)
		) {
			return false;
		}

		return true;
	}

	function shouldShowPercentage(sources: any[]) {
		const distances = sources.flatMap((citation) => citation.distances ?? []);
		return distances.every((d) => d !== undefined && d >= -1 && d <= 1);
	}

	$: {
		citations = sources.reduce((acc, source) => {
			if (Object.keys(source).length === 0) {
				return acc;
			}

			source.document.forEach((document, index) => {
				const metadata = source.metadata?.[index];
				const distance = source.distances?.[index];

				// Within the same citation there could be multiple documents
				const id = metadata?.source ?? source?.source?.id ?? 'N/A';
				let _source = source?.source;

				if (metadata?.name) {
					_source = { ..._source, name: metadata.name };
				}

				if (id.startsWith('http://') || id.startsWith('https://')) {
					_source = { ..._source, name: id, url: id };
				}

				const existingSource = acc.find((item) => item.id === id);

				if (existingSource) {
					existingSource.document.push(document);
					existingSource.metadata.push(metadata);
					if (distance !== undefined) existingSource.distances.push(distance);
				} else {
					acc.push({
						id: id,
						source: _source,
						document: [document],
						metadata: metadata ? [metadata] : [],
						distances: distance !== undefined ? [distance] : undefined
					});
				}
			});
			return acc;
		}, []);
		console.log('citations', citations);

		showRelevance = calculateShowRelevance(citations);
		showPercentage = shouldShowPercentage(citations);
	}

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};
</script>

<CitationsModal
	bind:show={showCitationModal}
	citation={selectedCitation}
	{chatId}
	messageId={id}
	{showPercentage}
	{showRelevance}
/>

{#if citations.length > 0}
	<div style="--py:0.125rem; --mx:-0.125rem; --w:100%; --d:flex; --g:0.25rem; --ai:center; --fw:wrap">
		{#if citations.length <= 3}
			<div style="--d:flex; --size:0.75rem; --weight:500; --fw:wrap">
				{#each citations as citation, idx}
					<button
						id={`source-${id}-${idx + 1}`}
						style="--oe:none; --d:flex; --dark-c:var(--color-gray-300, #cdcdcd); --p:0.25rem; --bgc:#fff; --dark-bgc:var(--color-gray-900, #171717); --radius:0.75rem; --maxw:24rem"
	class="no-toggle"
						on:click={() => {
							showCitationModal = true;
							selectedCitation = citation;
						}}
					>
						{#if citations.every((c) => c.distances !== undefined)}
							<div style="--bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-800, #333); --radius:9999px; --w:1rem; --h:1rem">
								{idx + 1}
							</div>
						{/if}
						<div
							style="--fx:1 1 0%; --mx:0.25rem; overflow:hidden; text-overflow:ellipsis; --ws:nowrap; --c:rgb(0 0 0 / 0.6); --hvr-c:#000; --dark-c:rgb(255 255 255 / 0.6); --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						>
							{decodeString(citation.source.name)}
						</div>
					</button>
				{/each}
			</div>
		{:else}
			<Collapsible
				id={`collapsible-${id}`}
				bind:open={isCollapsibleOpen}
				className="w-full max-w-full "
				buttonClassName="w-fit max-w-full"
			>
				<div
					style="--d:flex; --w:100%; --of:auto; --ai:center; --g:0.5rem; --c:var(--color-gray-500, #9b9b9b); --hvr-c:var(--color-gray-600, #676767); --hvr-dark-c:var(--color-gray-400, #b4b4b4); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --cur:pointer"
				>
					<div
						style="--fx:1 1 0%; --d:flex; --ai:center; --g:0.25rem; --of:auto; --w:100%; --maxw:100%"
	class="scrollbar-none"
					>
						<span style="--ws:nowrap; --d:none; --d-sm:inline; --fs:0"
							>{$i18n.t('References from')}</span
						>
						<div style="--d:flex; --ai:center; --of:auto; --w:100%; --maxw:100%; --fx:1 1 0%"
	class="scrollbar-none">
							<div style="--d:flex; --size:0.75rem; --weight:500; --ai:center">
								{#each citations.slice(0, 2) as citation, idx}
									<button
										style="--oe:none; --d:flex; --dark-c:var(--color-gray-300, #cdcdcd); --p:0.25rem; --bgc:var(--color-gray-50, #f9f9f9); --hvr-bgc:var(--color-gray-100, #ececec); --dark-bgc:var(--color-gray-900, #171717); --hvr-dark-bgc:var(--color-gray-850, #262626); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.75rem; --maxw:24rem"
	class="no-toggle"
										on:click={() => {
											showCitationModal = true;
											selectedCitation = citation;
										}}
										on:pointerup={(e) => {
											e.stopPropagation();
										}}
									>
										{#if citations.every((c) => c.distances !== undefined)}
											<div style="--bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-800, #333); --radius:9999px; --w:1rem; --h:1rem">
												{idx + 1}
											</div>
										{/if}
										<div style="--fx:1 1 0%; --mx:0.25rem; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">
											{decodeString(citation.source.name)}
										</div>
									</button>
								{/each}
							</div>
						</div>
						<div style="--d:flex; --ai:center; --g:0.25rem; --ws:nowrap; --fs:0">
							<span style="--d:none; --d-sm:inline">{$i18n.t('and')}</span>
							{citations.length - 2}
							<span>{$i18n.t('more')}</span>
						</div>
					</div>
					<div style="--fs:0">
						{#if isCollapsibleOpen}
							<ChevronUp strokeWidth="3.5" className="size-3.5" />
						{:else}
							<ChevronDown strokeWidth="3.5" className="size-3.5" />
						{/if}
					</div>
				</div>
				<div slot="content">
					<div style="--d:flex; --size:0.75rem; --weight:500; --fw:wrap">
						{#each citations.slice(2) as citation, idx}
							<button
								style="--oe:none; --d:flex; --dark-c:var(--color-gray-300, #cdcdcd); --p:0.25rem; --bgc:var(--color-gray-50, #f9f9f9); --hvr-bgc:var(--color-gray-100, #ececec); --dark-bgc:var(--color-gray-900, #171717); --hvr-dark-bgc:var(--color-gray-850, #262626); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.75rem; --maxw:24rem"
	class="no-toggle"
								on:click={() => {
									showCitationModal = true;
									selectedCitation = citation;
								}}
							>
								{#if citations.every((c) => c.distances !== undefined)}
									<div style="--bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-800, #333); --radius:9999px; --w:1rem; --h:1rem">
										{idx + 3}
									</div>
								{/if}
								<div style="--fx:1 1 0%; --mx:0.25rem; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">
									{decodeString(citation.source.name)}
								</div>
							</button>
						{/each}
					</div>
				</div>
			</Collapsible>
		{/if}
	</div>
{/if}
