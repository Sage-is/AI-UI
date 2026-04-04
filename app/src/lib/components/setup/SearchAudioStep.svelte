<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getModelsStatus, triggerModelDownload } from '$lib/apis/retrieval';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import QuestionMarkCircle from '$lib/components/icons/QuestionMarkCircle.svelte';

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
</script>

<div style="--px:1.2rem; --pt:1rem; --pb:1.5rem">
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
							<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"><QuestionMarkCircle className="size-3.5" /></span>
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
							<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"><QuestionMarkCircle className="size-3.5" /></span>
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
