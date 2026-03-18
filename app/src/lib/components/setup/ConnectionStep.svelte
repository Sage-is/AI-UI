<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { models, config } from '$lib/stores';
	import { settings } from '$lib/stores';
	import { getModels } from '$lib/apis';
	import {
		getOpenAIConfig,
		updateOpenAIConfig,
		verifyOpenAIConnection
	} from '$lib/apis/openai';
	import {
		getOllamaConfig,
		updateOllamaConfig,
		verifyOllamaConnection
	} from '$lib/apis/ollama';

	const i18n = getContext('i18n');

	export let onNext: () => void = () => {};
	export let onBack: () => void = () => {};

	let openaiUrl = '';
	let openaiKey = '';
	let openaiVerified = false;
	let openaiVerifying = false;

	let ollamaUrl = 'http://localhost:11434';
	let ollamaVerified = false;
	let ollamaVerifying = false;

	let openaiConfig: any = null;
	let ollamaConfig: any = null;

	let openaiExisting = false;
	let ollamaExisting = false;
	let hasVerifiedConnection = false;

	onMount(async () => {
		openaiConfig = await getOpenAIConfig(localStorage.token);
		ollamaConfig = await getOllamaConfig(localStorage.token);

		if (openaiConfig?.OPENAI_API_BASE_URLS?.length > 0 && openaiConfig.OPENAI_API_BASE_URLS[0]) {
			openaiUrl = openaiConfig.OPENAI_API_BASE_URLS[0];
			openaiKey = openaiConfig.OPENAI_API_KEYS?.[0] ?? '';
			if (openaiConfig.ENABLE_OPENAI_API && openaiKey) {
				openaiExisting = true;
				hasVerifiedConnection = true;
			}
		}
		if (ollamaConfig?.OLLAMA_BASE_URLS?.length > 0 && ollamaConfig.OLLAMA_BASE_URLS[0]) {
			ollamaUrl = ollamaConfig.OLLAMA_BASE_URLS[0];
			if (ollamaConfig.ENABLE_OLLAMA_API) {
				ollamaExisting = true;
				hasVerifiedConnection = true;
			}
		}
	});

	const verifyOpenAI = async () => {
		if (!openaiUrl) {
			toast.error($i18n.t('Please enter a URL'));
			return;
		}
		openaiVerifying = true;
		try {
			const res = await verifyOpenAIConnection(localStorage.token, {
				url: openaiUrl,
				key: openaiKey
			});
			if (res) {
				toast.success($i18n.t('Connection verified'));
				openaiVerified = true;
				await saveOpenAI();
			}
		} catch (e) {
			toast.error($i18n.t('Connection failed: {{error}}', { error: e }));
			openaiVerified = false;
		}
		openaiVerifying = false;
	};

	const verifyOllama = async () => {
		if (!ollamaUrl) {
			toast.error($i18n.t('Please enter a URL'));
			return;
		}
		ollamaVerifying = true;
		try {
			const res = await verifyOllamaConnection(localStorage.token, {
				url: ollamaUrl
			});
			if (res) {
				toast.success($i18n.t('Connection verified'));
				ollamaVerified = true;
				await saveOllama();
			}
		} catch (e) {
			toast.error($i18n.t('Connection failed: {{error}}', { error: e }));
			ollamaVerified = false;
		}
		ollamaVerifying = false;
	};

	const saveOpenAI = async () => {
		if (!openaiConfig) return;
		const urls = [...(openaiConfig.OPENAI_API_BASE_URLS || [])];
		const keys = [...(openaiConfig.OPENAI_API_KEYS || [])];

		if (urls.length === 0 || !urls[0]) {
			urls[0] = openaiUrl;
			keys[0] = openaiKey;
		} else {
			urls[0] = openaiUrl;
			keys[0] = openaiKey;
		}

		await updateOpenAIConfig(localStorage.token, {
			...openaiConfig,
			ENABLE_OPENAI_API: true,
			OPENAI_API_BASE_URLS: urls,
			OPENAI_API_KEYS: keys
		});

		hasVerifiedConnection = true;
		await refreshModels();
	};

	const saveOllama = async () => {
		if (!ollamaConfig) return;
		const urls = [...(ollamaConfig.OLLAMA_BASE_URLS || [])];

		if (urls.length === 0 || !urls[0]) {
			urls[0] = ollamaUrl;
		} else {
			urls[0] = ollamaUrl;
		}

		await updateOllamaConfig(localStorage.token, {
			...ollamaConfig,
			ENABLE_OLLAMA_API: true,
			OLLAMA_BASE_URLS: urls
		});

		hasVerifiedConnection = true;
		await refreshModels();
	};

	const refreshModels = async () => {
		models.set(
			await getModels(
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};
</script>

<div style="--px:1.2rem; --pt:1rem; --pb:1.5rem">
	<div style="--size:1.2rem; --weight:600; --dark-c:#fff; --mb:0.2rem">
		{$i18n.t('Connect a Model Provider')}
	</div>
	<div style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:1.2rem">
		{$i18n.t('Add at least one connection to start chatting with AI models.')}
	</div>

	<div style="--d:flex; --fd:column; --g:1rem; --mb:1.5rem; --ofy:auto; --maxh:20rem" class="scrollbar-hidden">
		<!-- OpenAI Card -->
		<div style="--p:1rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid">
			<div style="--d:flex; --ai:center; --jc:space-between; --mb:0.6rem">
				<div style="--d:flex; --ai:center; --g:0.4rem">
					<span style="--size:0.85rem; --weight:600">{$i18n.t('OpenAI API')}</span>
					{#if openaiVerified}
						<span style="--size:0.6rem; --c:var(--color-green-600); --weight:500">{$i18n.t('connected')}</span>
					{:else if openaiExisting}
						<span style="--size:0.6rem; --c:var(--color-green-600); --weight:500">{$i18n.t('configured')}</span>
					{/if}
				</div>
			</div>

			<div style="--d:flex; --fd:column; --g:0.5rem">
				<div>
					<div style="--size:0.65rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300)">
						{$i18n.t('API Base URL')}
					</div>
					<input
						style="--w:100%; --radius:0.5rem; --py:0.4rem; --px:0.6rem; --size:0.75rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --dark-c:var(--color-gray-300); --oe:none"
						type="text"
						placeholder="https://api.openai.com/v1"
						bind:value={openaiUrl}
					/>
				</div>
				<div>
					<div style="--size:0.65rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300)">
						{$i18n.t('API Key')}
					</div>
					<input
						style="--w:100%; --radius:0.5rem; --py:0.4rem; --px:0.6rem; --size:0.75rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --dark-c:var(--color-gray-300); --oe:none"
						type="password"
						placeholder="sk-..."
						bind:value={openaiKey}
					/>
				</div>
				<button
					on:click={verifyOpenAI}
					disabled={openaiVerifying}
					style="--as:flex-end; --px:0.6rem; --py:0.3rem; --size:0.7rem; --weight:500; --bgc:var(--color-gray-100); --hvr-bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --radius:0.5rem; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				>
					{openaiVerifying ? $i18n.t('Verifying...') : $i18n.t('Verify & Save')}
				</button>
			</div>
		</div>

		<!-- Ollama Card -->
		<div style="--p:1rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid">
			<div style="--d:flex; --ai:center; --jc:space-between; --mb:0.6rem">
				<div style="--d:flex; --ai:center; --g:0.4rem">
					<span style="--size:0.85rem; --weight:600">{$i18n.t('Ollama')}</span>
					{#if ollamaVerified}
						<span style="--size:0.6rem; --c:var(--color-green-600); --weight:500">{$i18n.t('connected')}</span>
					{:else if ollamaExisting}
						<span style="--size:0.6rem; --c:var(--color-green-600); --weight:500">{$i18n.t('configured')}</span>
					{/if}
				</div>
			</div>

			<div style="--d:flex; --fd:column; --g:0.5rem">
				<div>
					<div style="--size:0.65rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300)">
						{$i18n.t('Ollama URL')}
					</div>
					<input
						style="--w:100%; --radius:0.5rem; --py:0.4rem; --px:0.6rem; --size:0.75rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --dark-c:var(--color-gray-300); --oe:none"
						type="text"
						placeholder="http://localhost:11434"
						bind:value={ollamaUrl}
					/>
				</div>
				<button
					on:click={verifyOllama}
					disabled={ollamaVerifying}
					style="--as:flex-end; --px:0.6rem; --py:0.3rem; --size:0.7rem; --weight:500; --bgc:var(--color-gray-100); --hvr-bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --radius:0.5rem; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				>
					{ollamaVerifying ? $i18n.t('Verifying...') : $i18n.t('Verify & Save')}
				</button>
			</div>
		</div>
	</div>

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
				on:click={onNext}
				disabled={!hasVerifiedConnection}
				style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:{hasVerifiedConnection ? '#000' : 'var(--color-gray-300)'}; --hvr-bgc:{hasVerifiedConnection ? 'var(--color-gray-900)' : 'var(--color-gray-300)'}; --c:#fff; --dark-bgc:{hasVerifiedConnection ? '#fff' : 'var(--color-gray-600)'}; --dark-c:{hasVerifiedConnection ? '#000' : 'var(--color-gray-400)'}; --hvr-dark-bgc:{hasVerifiedConnection ? 'var(--color-gray-100)' : 'var(--color-gray-600)'}; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			>
				{$i18n.t('Next')}
			</button>
		</div>
	</div>
</div>
