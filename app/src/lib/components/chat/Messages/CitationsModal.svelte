<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';
	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { copyToClipboard as _copyToClipboard } from '$lib/utils';

	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let citation;
	export let chatId = '';
	export let messageId = '';
	export let showPercentage = false;
	export let showRelevance = true;

	// Tracks copy button feedback state
	let copied = false;

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
		// Reset copy state when citation changes
		copied = false;
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

	const containsMarkdown = (text: string): boolean => {
		if (!text) return false;
		// Detect common markdown patterns: headers, bold, italic, links, lists, code blocks, tables
		return /(?:^#{1,6}\s|(?:\*\*|__).+(?:\*\*|__)|(?:\*|_).+(?:\*|_)|\[.+\]\(.+\)|^[-*+]\s|^\d+\.\s|```|^\|.+\|)/m.test(
			text
		);
	};

	/**
	 * Builds a direct link to the chat message that produced this citation.
	 * Format: {origin}/c/{chatId}#{messageId}
	 */
	function getChatLink(): string {
		if (!chatId) return '';
		const base = `${window.location.origin}/c/${chatId}`;
		return messageId ? `${base}#${messageId}` : base;
	}

	/**
	 * Builds a plain-text summary of all citation documents for clipboard.
	 * Includes source name, content, and a direct chat link.
	 */
	function buildCopyText(): string {
		const sections = mergedDocuments.map((doc, i) => {
			const sourceName = decodeString(doc.metadata?.name ?? doc.source?.name ?? 'Unknown');
			const content = doc.document ?? '';
			return `[${i + 1}] ${sourceName}\n${content}`;
		});

		const chatLink = getChatLink();
		const linkLine = chatLink ? `\n---\n${chatLink}` : '';

		return sections.join('\n\n') + linkLine;
	}

	/** Copy all citation content + chat link to clipboard */
	async function handleCopy() {
		const text = buildCopyText();
		await _copyToClipboard(text);
		copied = true;
		toast.success($i18n.t('Copying to clipboard was successful!'));
		setTimeout(() => (copied = false), 2000);
	}
</script>

<Modal size="lg" bind:show>
	<div id="citation-modal">
		<!-- Header: title, copy button, close button -->
		<div
			id="citation-modal-header"
			style="--d:flex; --jc:space-between; --ai:center; --dark-c:var(--color-gray-300, #cdcdcd); --px:1.25rem; --pt:1rem; --pb:0.5rem"
		>
			<div style="--size:1.125rem; --weight:500; --tt:capitalize">
				{$i18n.t('Citation')}
			</div>

			<div style="--d:flex; --ai:center; --g:0.25rem">
				<!-- Copy citation content + chat link -->
				<Tooltip content={$i18n.t('Copy citation')} placement="bottom">
					<button
						id="citation-copy-btn"
						style="--p:0.375rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --tn:all 150ms ease"
						on:click={handleCopy}
					>
						{#if copied}
							<!-- Checkmark icon: shown briefly after copy -->
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2.3"
								stroke="currentColor"
								style="--w:1.125rem; --h:1.125rem; --c:var(--color-green-500, #22c55e)"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
							</svg>
						{:else}
							<!-- Clipboard icon: default state -->
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2.3"
								stroke="currentColor"
								style="--w:1.125rem; --h:1.125rem"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184"
								/>
							</svg>
						{/if}
					</button>
				</Tooltip>

				<!-- Close modal -->
				<button
					id="citation-close-btn"
					style="--p:0.375rem"
					on:click={() => {
						show = false;
					}}
				>
					<XMark className={'size-5'} />
				</button>
			</div>
		</div>

		<!-- Citation documents list -->
		<div
			id="citation-modal-body"
			style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1.5rem; --pb:1.25rem; --g-md:1rem"
		>
			<div
				style="--d:flex; --fd:column; --w:100%; --dark-c:var(--color-gray-200, #e3e3e3); --ofy:scroll; --maxh:22rem"
				class="scrollbar-hidden"
			>
				{#each mergedDocuments as document, documentIdx}
					<div id="citation-source-{documentIdx}" style="--d:flex; --fd:column; --w:100%">
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
								<div
									style="--size:0.875rem; --dark-c:var(--color-gray-400, #b4b4b4); --d:flex; --ai:center; --g:0.5rem; --w:fit-content"
								>
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
										<span
											style="--size:0.75rem; --c:var(--color-gray-500, #9b9b9b); --dark-c:var(--color-gray-400, #b4b4b4)"
										>
											({$i18n.t('page')}
											{document.metadata.page + 1})
										</span>
									{/if}
								</div>
							</Tooltip>
							{#if document.metadata?.parameters}
								<details
									id="citation-params-{documentIdx}"
									style="--size:0.875rem; --mt:0.5rem"
								>
									<summary
										class="cursor-pointer select-none"
										style="--weight:500; --dark-c:var(--color-gray-300, #cdcdcd)"
									>
										{$i18n.t('Parameters')}
									</summary>
									<div
										style="--dark-c:var(--color-gray-400, #b4b4b4); --bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-800, #333); --p:0.5rem; --radius:0.375rem; --mt:0.25rem; --of:auto; --maxh:10rem"
									>
										{#if typeof document.metadata.parameters === 'object' && !Array.isArray(document.metadata.parameters)}
											{#each Object.entries(document.metadata.parameters) as [key, value]}
												<div style="--d:flex; --g:0.5rem; --py:0.125rem">
													<span style="--weight:500; --ws:nowrap">{key}:</span>
													<span style="--c:var(--color-gray-600, #777); --dark-c:var(--color-gray-400, #b4b4b4)">{typeof value === 'object' ? JSON.stringify(value) : value}</span>
												</div>
											{/each}
										{:else}
											<pre style="--ws:pre-wrap">{JSON.stringify(document.metadata.parameters, null, 2)}</pre>
										{/if}
									</div>
								</details>
							{/if}
							{#if showRelevance}
								<div
									style="--size:0.875rem; --weight:500; --dark-c:var(--color-gray-300, #cdcdcd); --mt:0.5rem"
								>
									{$i18n.t('Relevance')}
								</div>
								{#if document.distance !== undefined}
									<Tooltip
										className="w-fit"
										content={$i18n.t('Semantic distance to query')}
										placement="top-start"
										tippyOptions={{ duration: [500, 0] }}
									>
										<div
											style="--size:0.875rem; --my:0.25rem; --dark-c:var(--color-gray-400, #b4b4b4); --d:flex; --ai:center; --g:0.5rem; --w:fit-content"
										>
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
													<span
														style="--c:var(--color-gray-500, #9b9b9b); --dark-c:var(--color-gray-500, #9b9b9b)"
													>
														({(document?.distance ?? 0).toFixed(4)})
													</span>
												{/if}
											{:else if typeof document?.distance === 'number'}
												<span
													style="--c:var(--color-gray-500, #9b9b9b); --dark-c:var(--color-gray-500, #9b9b9b)"
												>
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
					<div id="citation-content-{documentIdx}" style="--d:flex; --fd:column; --w:100%">
						<div
							style="--size:0.875rem; --weight:500; --dark-c:var(--color-gray-300, #cdcdcd); --mt:0.5rem"
						>
							{$i18n.t('Content')}
						</div>
						{#if document.metadata?.html}
							<iframe
								style="--w:100%; --bw:0; --h:auto; --radius:0"
								sandbox="allow-scripts allow-forms allow-same-origin"
								srcdoc={document.document}
								title={$i18n.t('Content')}
							></iframe>
						{:else if containsMarkdown(document.document)}
							<div
								class="citation-markdown prose dark:prose-invert"
								style="--size:0.875rem; --dark-c:var(--color-gray-400, #b4b4b4); --maxw:none"
							>
								{@html DOMPurify.sanitize(marked.parse(document.document))}
							</div>
						{:else}
							<pre
								style="--size:0.875rem; --dark-c:var(--color-gray-400, #b4b4b4); --ws:pre-line">{document.document}</pre>
						{/if}
					</div>

					{#if documentIdx !== mergedDocuments.length - 1}
						<hr
							style="--bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-850, #262626); --my:0.75rem"
						/>
					{/if}
				{/each}
			</div>
		</div>
	</div>
</Modal>
