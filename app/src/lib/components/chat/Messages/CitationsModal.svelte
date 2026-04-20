<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';
	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { copyToClipboard as _copyToClipboard } from '$lib/utils';
	import Icon from '$lib/components/Icon.svelte';


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
			style="--d:flex; --jc:space-between; --ai:center; --dark-c:var(--color-gray-300); --px:1.2rem; --pt:1rem; --pb:0.5rem"
		>
			<div style="--size:1.125rem; --weight:500; --tt:capitalize">
				{$i18n.t('Citation')}
			</div>

			<div style="--d:flex; --ai:center; --g:0.2rem">
				<!-- Copy citation content + chat link -->
				<Tooltip content={$i18n.t('Copy citation')} placement="bottom">
					<button
						id="citation-copy-btn"
						style="--p:0.4rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --tn:all 150ms ease"
						on:click={handleCopy}
					>
						{#if copied}
							<!-- Checkmark icon: shown briefly after copy -->
							<Icon name="check-outline" className="size-[1.125rem]" strokeWidth="2.3" />
						{:else}
							<!-- Clipboard icon: default state -->
							<Icon name="clipboard-doc" className="size-[1.125rem]" strokeWidth="2.3" />
						{/if}
					</button>
				</Tooltip>

				<!-- Close modal -->
				<button
					id="citation-close-btn"
					style="--p:0.4rem"
					on:click={() => {
						show = false;
					}}
				>
					<Icon name="x-mark" strokeWidth="2" className={'size-5'} />
				</button>
			</div>
		</div>

		<!-- Citation documents list -->
		<div
			id="citation-modal-body"
			style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1.5rem; --pb:1.2rem; --g-md:1rem"
		>
			<div
				style="--d:flex; --fd:column; --w:100%; --dark-c:var(--color-gray-200); --ofy:scroll; --maxh:22rem"
				class="scrollbar-hidden"
			>
				{#each mergedDocuments as document, documentIdx}
					<div id="citation-source-{documentIdx}" style="--d:flex; --fd:column; --w:100%">
						<div style="--size:0.8rem; --weight:500; --dark-c:var(--color-gray-300)">
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
									style="--size:0.8rem; --dark-c:var(--color-gray-400); --d:flex; --ai:center; --g:0.5rem; --w:fit-content"
								>
									<a
										style="--hvr-c:var(--color-gray-500); --hvr-dark-c:var(--color-gray-100); --td:underline; --fg:1"
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
											style="--size:0.6rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)"
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
									style="--size:0.8rem; --mt:0.5rem"
								>
									<summary
										class="cursor-pointer select-none"
										style="--weight:500; --dark-c:var(--color-gray-300)"
									>
										{$i18n.t('Parameters')}
									</summary>
									<div
										style="--dark-c:var(--color-gray-400); --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-800); --p:0.5rem; --radius:0.4rem; --mt:0.2rem; --of:auto; --maxh:10rem"
									>
										{#if typeof document.metadata.parameters === 'object' && !Array.isArray(document.metadata.parameters)}
											{#each Object.entries(document.metadata.parameters) as [key, value]}
												<div style="--d:flex; --g:0.5rem; --py:0.125rem">
													<span style="--weight:500; --ws:nowrap">{key}:</span>
													<span style="--c:var(--color-gray-600); --dark-c:var(--color-gray-400)">{typeof value === 'object' ? JSON.stringify(value) : value}</span>
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
									style="--size:0.8rem; --weight:500; --dark-c:var(--color-gray-300); --mt:0.5rem"
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
											style="--size:0.8rem; --my:0.2rem; --dark-c:var(--color-gray-400); --d:flex; --ai:center; --g:0.5rem; --w:fit-content"
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
														style="--c:var(--color-gray-500); --dark-c:var(--color-gray-500)"
													>
														({(document?.distance ?? 0).toFixed(4)})
													</span>
												{/if}
											{:else if typeof document?.distance === 'number'}
												<span
													style="--c:var(--color-gray-500); --dark-c:var(--color-gray-500)"
												>
													({(document?.distance ?? 0).toFixed(4)})
												</span>
											{/if}
										</div>
									</Tooltip>
								{:else}
									<div style="--size:0.8rem; --dark-c:var(--color-gray-400)">
										{$i18n.t('No distance available')}
									</div>
								{/if}
							{/if}
						{:else}
							<div style="--size:0.8rem; --dark-c:var(--color-gray-400)">
								{$i18n.t('No source available')}
							</div>
						{/if}
					</div>
					<div id="citation-content-{documentIdx}" style="--d:flex; --fd:column; --w:100%">
						<div
							style="--size:0.8rem; --weight:500; --dark-c:var(--color-gray-300); --mt:0.5rem"
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
								style="--size:0.8rem; --dark-c:var(--color-gray-400); --maxw:none"
							>
								{@html DOMPurify.sanitize(marked.parse(document.document))}
							</div>
						{:else}
							<pre
								style="--size:0.8rem; --dark-c:var(--color-gray-400); --ws:pre-line">{document.document}</pre>
						{/if}
					</div>

					{#if documentIdx !== mergedDocuments.length - 1}
						<hr
							style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.6rem"
						/>
					{/if}
				{/each}
			</div>
		</div>
	</div>
</Modal>
