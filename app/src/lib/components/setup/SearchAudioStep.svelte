<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Icon from '$lib/components/Icon.svelte';

	import { getModelsStatus, triggerModelDownload, graftSprig } from '$lib/apis/retrieval';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let onNext: () => void = () => {};
	export let onBack: () => void = () => {};

	let loading = true;

	let includeEmbedding = true;
	let includeWhisper = true;

	let embeddingStatus = 'pending';
	let whisperStatus = 'pending';
	let embeddingModel = '';
	let vectorDbReady = false;

	onMount(async () => {
		try {
			const res = await getModelsStatus(localStorage.token);
			if (res?.models) {
				embeddingStatus = res.models.embedding ?? 'pending';
				whisperStatus = res.models.whisper ?? 'pending';
			}
			embeddingModel = res?.embedding_model ?? '';
			vectorDbReady = res?.vector_db_ready ?? false;
		} catch {
			// Status check failed — leave defaults
		}
		loading = false;
	});

	$: needsDownload =
		(includeEmbedding && embeddingStatus !== 'ready') ||
		(includeWhisper && whisperStatus !== 'ready');

	const downloadAndNext = async () => {
		if (!needsDownload) {
			onNext();
			return;
		}

		const components: string[] = [];
		if (includeEmbedding && embeddingStatus !== 'ready') components.push('embedding');
		if (includeWhisper && whisperStatus !== 'ready') components.push('whisper');

		try {
			await triggerModelDownload(localStorage.token, { components });
			toast.success($i18n.t('Downloading in background. You will be notified when ready.'));
		} catch {
			toast.error($i18n.t('Failed to start download'));
		}
		onNext();
	};

	let grafting = false;

	// Graft local Sprigs™ instead of downloading model weights — the one wizard
	// button that performs a real runtime graft.
	//
	// These are the in-housed cultivars, not the mock. This button used to graft
	// `mock-embedding`, whose vectors are seeded from a sha256 of the input text,
	// and then report "Document search is ready" — so uploads worked, queries
	// returned results, and the results were noise. minilm shares the mock's
	// 384-dim width, so swapping needs no reindex. Both are delivered as OCI
	// artifacts from the configured registry: still zero egress.
	// Embedding is a chain, not one graft: minilm-onnx-inhoused refuses to start
	// without chromadb, onnxruntime and numpy, which ride the vector-chroma
	// overlay. That prerequisite is enforced at graft time and not declared in
	// the catalog, which is precisely why the old one-shot mock graft was the
	// path of least resistance.
	const CULTIVARS = {
		embedding: [
			{ name: 'vector-chroma', capability: 'vector' },
			{ name: 'minilm-onnx-inhoused', capability: 'embedding' }
		],
		whisper: [{ name: 'whisper-base-ggml', capability: 'stt' }]
	};

	const graftAndNext = async () => {
		// Read the checkboxes. The old version ignored them and always grafted
		// exactly one thing, which made both toggles decorative on this path.
		const chains = [];
		if (includeEmbedding && embeddingStatus !== 'ready') chains.push(CULTIVARS.embedding);
		if (includeWhisper && whisperStatus !== 'ready') chains.push(CULTIVARS.whisper);

		if (chains.length === 0) {
			onNext();
			return;
		}

		grafting = true;
		const failed: string[] = [];
		// Sequential, not parallel: each graft unpacks an OCI artifact and starts
		// a child process, and the supervisor is the shared resource.
		for (const chain of chains) {
			for (const cultivar of chain) {
				try {
					await graftSprig(localStorage.token, cultivar);
				} catch {
					// Stop this chain — whatever rides on the failed prerequisite
					// will fail for the same reason, and reporting it twice reads
					// as two problems.
					failed.push(cultivar.name);
					break;
				}
			}
		}
		grafting = false;

		if (failed.length) {
			toast.error($i18n.t('Failed to graft: {{names}}', { names: failed.join(', ') }));
		} else {
			toast.success($i18n.t('Grafted local Sprigs™. Document search and audio are ready.'));
		}
		onNext();
	};
</script>

<div data-cy="search-audio-panel" data-embedding-status={embeddingStatus} data-whisper-status={whisperStatus} style="--px:1.2rem; --pt:1rem; --pb:1.5rem">
	<div style="--size:1.2rem; --weight:600; --dark-c:#fff; --mb:0.2rem">
		{$i18n.t('AI Engine')}
	</div>
	<div style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:1.2rem">
		{$i18n.t('Install local AI components for document search, knowledge base, and audio transcription.')}
	</div>

	{#if loading}
		<div style="--d:flex; --jc:center; --py:2rem; --size:0.8rem; --c:var(--color-gray-400)">
			{$i18n.t('Loading...')}
		</div>
	{:else}
		<div style="--d:flex; --fd:column; --g:0.6rem; --mb:1.5rem">

			<!-- Document Search (Embedding Model) -->
			<label
				style="--d:flex; --ai:center; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; cursor:{embeddingStatus === 'ready' ? 'default' : 'pointer'}; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<input
					data-cy="search-audio-embedding"
					type="checkbox"
					bind:checked={includeEmbedding}
					disabled={embeddingStatus === 'ready'}
					style="--w:1rem; --h:1rem; --shrink:0"
				/>
				<div style="--grow:1">
					<div style="--d:flex; --ai:center; --g:0.4rem">
						<span style="--size:0.85rem; --weight:500">{$i18n.t('Document Search')}</span>
						{#if embeddingStatus === 'ready'}
							<span style="--size:0.6rem; --c:var(--color-green-600); --weight:500">{$i18n.t('installed')}</span>
						{:else if embeddingStatus === 'downloading'}
							<span style="--size:0.6rem; --c:var(--color-blue-600); --weight:500">{$i18n.t('downloading...')}</span>
						{/if}
						<Tooltip content={$i18n.t('Embedding model for RAG document search and knowledge base queries. Required for uploading and searching documents.')} placement="right" className="flex items-center">
							<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"><Icon name="question-mark-circle" strokeWidth="2" className="size-3.5" /></span>
						</Tooltip>
					</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{embeddingModel || 'intfloat/multilingual-e5-large'} (~2.5 GB)
					</div>
					<div style="--size:0.65rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500); --mt:0.15rem">
						ChromaDB (~100 MB) —
						{#if vectorDbReady}
							<span style="--c:var(--color-green-600)">{$i18n.t('installed')}</span>
						{:else}
							{$i18n.t('will be installed automatically')}
						{/if}
					</div>
				</div>
			</label>

			<!-- Speech-to-Text (Whisper) -->
			<label
				style="--d:flex; --ai:center; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; cursor:{whisperStatus === 'ready' ? 'default' : 'pointer'}; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<input
					data-cy="search-audio-whisper"
					type="checkbox"
					bind:checked={includeWhisper}
					disabled={whisperStatus === 'ready'}
					style="--w:1rem; --h:1rem; --shrink:0"
				/>
				<div style="--grow:1">
					<div style="--d:flex; --ai:center; --g:0.4rem">
						<span style="--size:0.85rem; --weight:500">{$i18n.t('Speech-to-Text')}</span>
						{#if whisperStatus === 'ready'}
							<span style="--size:0.6rem; --c:var(--color-green-600); --weight:500">{$i18n.t('installed')}</span>
						{:else if whisperStatus === 'downloading'}
							<span style="--size:0.6rem; --c:var(--color-blue-600); --weight:500">{$i18n.t('downloading...')}</span>
						{/if}
						<Tooltip content={$i18n.t('Whisper model for transcribing audio files and voice input into text.')} placement="right" className="flex items-center">
							<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"><Icon name="question-mark-circle" strokeWidth="2" className="size-3.5" /></span>
						</Tooltip>
					</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						Whisper base (~150 MB)
					</div>
				</div>
			</label>

		</div>
	{/if}

	<div style="--d:flex; --jc:space-between; --ai:center">
		<button
			on:click={onBack}
			style="--px:0.6rem; --py:0.3rem; --size:0.75rem; --c:var(--color-gray-500); --hvr-c:var(--color-gray-700); --dark-hvr-c:var(--color-gray-200)"
		>
			{$i18n.t('Back')}
		</button>

		<div style="--d:flex; --ai:center; --g:0.6rem">
			<button
				on:click={onNext}
				style="--px:0.6rem; --py:0.3rem; --size:0.7rem; --c:var(--color-gray-400); --hvr-c:var(--color-gray-600); --td:underline"
			>
				{$i18n.t('Skip')}
			</button>

			<button
				data-cy="search-audio-graft"
				on:click={graftAndNext}
				disabled={grafting}
				style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:transparent; --c:var(--color-gray-700); --dark-c:var(--color-gray-200); --bc:var(--color-gray-300); --dark-bc:var(--color-gray-600); --bw:1px; --bs:solid; --radius:9999px; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				{$i18n.t('Graft Sprigs™ for me')}
			</button>

			<button
				data-cy="search-audio-download"
				on:click={downloadAndNext}
				disabled={loading}
				style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:{!loading ? '#000' : 'var(--color-gray-300)'}; --hvr-bgc:{!loading ? 'var(--color-gray-900)' : 'var(--color-gray-300)'}; --c:#fff; --dark-bgc:{!loading ? '#fff' : 'var(--color-gray-600)'}; --dark-c:{!loading ? '#000' : 'var(--color-gray-400)'}; --hvr-dark-bgc:{!loading ? 'var(--color-gray-100)' : 'var(--color-gray-600)'}; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			>
				{#if needsDownload}
					{$i18n.t('Download & Next')}
				{:else}
					{$i18n.t('Next')}
				{/if}
			</button>
		</div>
	</div>
</div>
