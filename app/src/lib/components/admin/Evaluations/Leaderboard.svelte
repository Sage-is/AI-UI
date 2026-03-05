<script lang="ts">
	import * as ort from 'onnxruntime-web';
	import { env, AutoModel, AutoTokenizer } from '@huggingface/transformers';

	env.backends.onnx.wasm.wasmPaths = '/wasm/';

	import { onMount, getContext } from 'svelte';
	import { models } from '$lib/stores';

	import ModelModal from './LeaderboardModal.svelte';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	const EMBEDDING_MODEL = 'TaylorAI/bge-micro-v2';

	let tokenizer = null;
	let model = null;

	export let feedbacks = [];

	let rankedModels = [];

	let query = '';

	let tagEmbeddings = new Map();
	let loadingLeaderboard = true;
	let debounceTimer;

	let orderBy: string = 'rating'; // default sort column
	let direction: 'asc' | 'desc' = 'desc'; // default sort order

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

	function setSortKey(key) {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = key === 'name' ? 'asc' : 'desc';
		}
	}

	//////////////////////
	//
	// Aggregate Level Modal
	//
	//////////////////////

	let showLeaderboardModal = false;
	let selectedModel = null;

	const openLeaderboardModelModal = (model) => {
		showLeaderboardModal = true;
		selectedModel = model;
	};

	const closeLeaderboardModal = () => {
		showLeaderboardModal = false;
		selectedModel = null;
	};

	//////////////////////
	//
	// Rank models by Elo rating
	//
	//////////////////////

	const rankHandler = async (similarities: Map<string, number> = new Map()) => {
		const modelStats = calculateModelStats(feedbacks, similarities);

		rankedModels = $models
			.filter((m) => m?.owned_by !== 'arena' && (m?.info?.meta?.hidden ?? false) !== true)
			.map((model) => {
				const stats = modelStats.get(model.id);
				return {
					...model,
					rating: stats ? Math.round(stats.rating) : '-',
					stats: {
						count: stats ? stats.won + stats.lost : 0,
						won: stats ? stats.won.toString() : '-',
						lost: stats ? stats.lost.toString() : '-'
					}
				};
			})
			.sort((a, b) => {
				if (a.rating === '-' && b.rating !== '-') return 1;
				if (b.rating === '-' && a.rating !== '-') return -1;
				if (a.rating !== '-' && b.rating !== '-') return b.rating - a.rating;
				return a.name.localeCompare(b.name);
			});

		loadingLeaderboard = false;
	};

	function calculateModelStats(
		feedbacks: Feedback[],
		similarities: Map<string, number>
	): Map<string, ModelStats> {
		const stats = new Map<string, ModelStats>();
		const K = 32;

		function getOrDefaultStats(modelId: string): ModelStats {
			return stats.get(modelId) || { rating: 1000, won: 0, lost: 0 };
		}

		function updateStats(modelId: string, ratingChange: number, outcome: number) {
			const currentStats = getOrDefaultStats(modelId);
			currentStats.rating += ratingChange;
			if (outcome === 1) currentStats.won++;
			else if (outcome === 0) currentStats.lost++;
			stats.set(modelId, currentStats);
		}

		function calculateEloChange(
			ratingA: number,
			ratingB: number,
			outcome: number,
			similarity: number
		): number {
			const expectedScore = 1 / (1 + Math.pow(10, (ratingB - ratingA) / 400));
			return K * (outcome - expectedScore) * similarity;
		}

		feedbacks.forEach((feedback) => {
			const modelA = feedback.data.model_id;
			const statsA = getOrDefaultStats(modelA);
			let outcome: number;

			switch (feedback.data.rating.toString()) {
				case '1':
					outcome = 1;
					break;
				case '-1':
					outcome = 0;
					break;
				default:
					return; // Skip invalid ratings
			}

			// If the query is empty, set similarity to 1, else get the similarity from the map
			const similarity = query !== '' ? similarities.get(feedback.id) || 0 : 1;
			const opponents = feedback.data.sibling_model_ids || [];

			opponents.forEach((modelB) => {
				const statsB = getOrDefaultStats(modelB);
				const changeA = calculateEloChange(statsA.rating, statsB.rating, outcome, similarity);
				const changeB = calculateEloChange(statsB.rating, statsA.rating, 1 - outcome, similarity);

				updateStats(modelA, changeA, outcome);
				updateStats(modelB, changeB, 1 - outcome);
			});
		});

		return stats;
	}

	//////////////////////
	//
	// Calculate cosine similarity
	//
	//////////////////////

	const cosineSimilarity = (vecA, vecB) => {
		// Ensure the lengths of the vectors are the same
		if (vecA.length !== vecB.length) {
			throw new Error('Vectors must be the same length');
		}

		// Calculate the dot product
		let dotProduct = 0;
		let normA = 0;
		let normB = 0;

		for (let i = 0; i < vecA.length; i++) {
			dotProduct += vecA[i] * vecB[i];
			normA += vecA[i] ** 2;
			normB += vecB[i] ** 2;
		}

		// Calculate the magnitudes
		normA = Math.sqrt(normA);
		normB = Math.sqrt(normB);

		// Avoid division by zero
		if (normA === 0 || normB === 0) {
			return 0;
		}

		// Return the cosine similarity
		return dotProduct / (normA * normB);
	};

	const calculateMaxSimilarity = (queryEmbedding, tagEmbeddings: Map<string, number[]>) => {
		let maxSimilarity = 0;
		for (const tagEmbedding of tagEmbeddings.values()) {
			const similarity = cosineSimilarity(queryEmbedding, tagEmbedding);
			maxSimilarity = Math.max(maxSimilarity, similarity);
		}
		return maxSimilarity;
	};

	//////////////////////
	//
	// Embedding functions
	//
	//////////////////////

	const loadEmbeddingModel = async () => {
		// Check if the tokenizer and model are already loaded and stored in the window object
		if (!window.tokenizer) {
			window.tokenizer = await AutoTokenizer.from_pretrained(EMBEDDING_MODEL);
		}

		if (!window.model) {
			window.model = await AutoModel.from_pretrained(EMBEDDING_MODEL);
		}

		// Use the tokenizer and model from the window object
		tokenizer = window.tokenizer;
		model = window.model;

		// Pre-compute embeddings for all unique tags
		const allTags = new Set(feedbacks.flatMap((feedback) => feedback.data.tags || []));
		await getTagEmbeddings(Array.from(allTags));
	};

	const getEmbeddings = async (text: string) => {
		const tokens = await tokenizer(text);
		const output = await model(tokens);

		// Perform mean pooling on the last hidden states
		const embeddings = output.last_hidden_state.mean(1);
		return embeddings.ort_tensor.data;
	};

	const getTagEmbeddings = async (tags: string[]) => {
		const embeddings = new Map();
		for (const tag of tags) {
			if (!tagEmbeddings.has(tag)) {
				tagEmbeddings.set(tag, await getEmbeddings(tag));
			}
			embeddings.set(tag, tagEmbeddings.get(tag));
		}
		return embeddings;
	};

	const debouncedQueryHandler = async () => {
		loadingLeaderboard = true;

		if (query.trim() === '') {
			rankHandler();
			return;
		}

		clearTimeout(debounceTimer);

		debounceTimer = setTimeout(async () => {
			const queryEmbedding = await getEmbeddings(query);
			const similarities = new Map<string, number>();

			for (const feedback of feedbacks) {
				const feedbackTags = feedback.data.tags || [];
				const tagEmbeddings = await getTagEmbeddings(feedbackTags);
				const maxSimilarity = calculateMaxSimilarity(queryEmbedding, tagEmbeddings);
				similarities.set(feedback.id, maxSimilarity);
			}

			rankHandler(similarities);
		}, 1500); // Debounce for 1.5 seconds
	};

	$: query, debouncedQueryHandler();

	onMount(async () => {
		rankHandler();
	});

	$: sortedModels = [...rankedModels].sort((a, b) => {
		let aVal, bVal;
		if (orderBy === 'name') {
			aVal = a.name;
			bVal = b.name;
			return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
		} else if (orderBy === 'rating') {
			aVal = a.rating === '-' ? -Infinity : a.rating;
			bVal = b.rating === '-' ? -Infinity : b.rating;
			return direction === 'asc' ? aVal - bVal : bVal - aVal;
		} else if (orderBy === 'won') {
			aVal = a.stats.won === '-' ? -Infinity : Number(a.stats.won);
			bVal = b.stats.won === '-' ? -Infinity : Number(b.stats.won);
			return direction === 'asc' ? aVal - bVal : bVal - aVal;
		} else if (orderBy === 'lost') {
			aVal = a.stats.lost === '-' ? -Infinity : Number(a.stats.lost);
			bVal = b.stats.lost === '-' ? -Infinity : Number(b.stats.lost);
			return direction === 'asc' ? aVal - bVal : bVal - aVal;
		}
		return 0;
	});
</script>

<ModelModal
	bind:show={showLeaderboardModal}
	model={selectedModel}
	{feedbacks}
	onClose={closeLeaderboardModal}
/>

<div style="--mt:0.125rem; --mb:0.5rem; --g:0.25rem; --d:flex; --fd:column; --fd-md:row; --jc:space-between">
	<div style="--d:flex; --as-md:center; --size:1.125rem; --weight:500; --px:0.125rem; --fs:0; --ai:center">
		<div style="--g:0.25rem">
			{$i18n.t('Leaderboard')}
		</div>

		<div style="--d:flex; --as:center; --w:1px; --h:1.5rem; --mx:0.625rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850)" />

		<span style="--size:1.125rem; --weight:500; --c:var(--color-gray-500); --dark-c:var(--color-gray-300); --mr:0.375rem"
			>{rankedModels.length}</span
		>
	</div>

	<div style="--d:flex; --g:0.5rem">
		<Tooltip content={$i18n.t('Re-rank models by topic similarity')}>
			<div style="--d:flex; --fx:1 1 0%">
				<div style="--as:center; --ml:0.25rem; --mr:0.75rem">
					<Search className="size-3" />
				</div>
				<input
					style="--w:100%; --size:0.875rem; --pr:1rem; --py:0.25rem; --btrr:0.75rem; --bbrr:0.75rem; --oe:none; --bgc:transparent"
					bind:value={query}
					placeholder={$i18n.t('Search')}
					on:focus={() => {
						loadEmbeddingModel();
					}}
				/>
			</div>
		</Tooltip>
	</div>
</div>

<div
	style="--pos:relative; --ws:nowrap; --ofx:auto; --maxw:100%; --radius:0.125rem; --pt:0.125rem"
	class="scrollbar-hidden"
>
	{#if loadingLeaderboard}
		<div style="--pos:absolute; --top:0; --bottom:0; --left:0; --right:0; --d:flex">
			<div style="--m:auto">
				<Spinner className="size-5" />
			</div>
		</div>
	{/if}
	{#if (rankedModels ?? []).length === 0}
		<div style="--ta:center; --size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --py:0.25rem">
			{$i18n.t('No models found')}
		</div>
	{:else}
		<table
			style="--w:100%; --size:0.875rem; --ta:left; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); table-layout:auto; --maxw:100%; --radius:0.25rem"
	class="{loadingLeaderboard
				? 'opacity-20'
				: ''}"
		>
			<thead
				style="--size:0.75rem; --c:var(--color-gray-700); --tt:uppercase; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --dark-c:var(--color-gray-400); --translatey:-0.125rem"
			>
				<tr class="">
					<th
						scope="col"
						style="--px:0.75rem; --py:0.375rem; --cur:pointer; --us:none; --w:0.75rem"
						on:click={() => setSortKey('rating')}
					>
						<div style="--d:flex; --g:0.375rem; --ai:center">
							{$i18n.t('RK')}
							{#if orderBy === 'rating'}
								<span style="--weight:400">
									{#if direction === 'asc'}
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
					</th>
					<th
						scope="col"
						style="--px:0.75rem; --py:0.375rem; --cur:pointer; --us:none"
						on:click={() => setSortKey('name')}
					>
						<div style="--d:flex; --g:0.375rem; --ai:center">
							{$i18n.t('Model')}
							{#if orderBy === 'name'}
								<span style="--weight:400">
									{#if direction === 'asc'}
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
					</th>
					<th
						scope="col"
						style="--px:0.75rem; --py:0.375rem; --ta:right; --cur:pointer; --us:none; --w:fit-content"
						on:click={() => setSortKey('rating')}
					>
						<div style="--d:flex; --g:0.375rem; --ai:center; --jc:flex-end">
							{$i18n.t('Rating')}
							{#if orderBy === 'rating'}
								<span style="--weight:400">
									{#if direction === 'asc'}
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
					</th>
					<th
						scope="col"
						style="--px:0.75rem; --py:0.375rem; --ta:right; --cur:pointer; --us:none; --w:1.25rem"
						on:click={() => setSortKey('won')}
					>
						<div style="--d:flex; --g:0.375rem; --ai:center; --jc:flex-end">
							{$i18n.t('Won')}
							{#if orderBy === 'won'}
								<span style="--weight:400">
									{#if direction === 'asc'}
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
					</th>
					<th
						scope="col"
						style="--px:0.75rem; --py:0.375rem; --ta:right; --cur:pointer; --us:none; --w:1.25rem"
						on:click={() => setSortKey('lost')}
					>
						<div style="--d:flex; --g:0.375rem; --ai:center; --jc:flex-end">
							{$i18n.t('Lost')}
							{#if orderBy === 'lost'}
								<span style="--weight:400">
									{#if direction === 'asc'}
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
					</th>
				</tr>
			</thead>
			<tbody>
				{#each sortedModels as model, modelIdx (model.id)}
					<tr
						style="--d:table-row; --bgc:#fff; --dark-bgc:var(--color-gray-900); --dark-bc:var(--color-gray-850); --size:0.75rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:rgb(38 38 38 / 0.5); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="group"
						on:click={() => openLeaderboardModelModal(model)}
					>
						<td style="--px:0.75rem; --py:0.375rem; --ta:left; --weight:500; --c:var(--color-gray-900); --dark-c:#fff; --w:fit-content">
							<div style="--line-clamp:1">
								{model?.rating !== '-' ? modelIdx + 1 : '-'}
							</div>
						</td>
						<td style="--px:0.75rem; --py:0.375rem; --va:middle">
							<div style="--d:flex; --ai:center; --g:0.5rem">
								<div style="--fs:0">
									<img
										src={model?.info?.meta?.profile_image_url ?? `${WEBUI_BASE_URL}/favicon.png`}
										alt={model.name}
										style="--w:1.25rem; --h:1.25rem; --radius:9999px; --objf:cover; --fs:0"
									/>
								</div>

								<div style="--weight:500; --c:var(--color-gray-800); --dark-c:var(--color-gray-200); --pr:1rem">
									{model.name}
								</div>
							</div>
						</td>
						<td style="--px:0.75rem; --py:0.375rem; --ta:right; --weight:500; --c:var(--color-gray-900); --dark-c:#fff; --w:max-content">
							{model.rating}
						</td>

						<td style="--px:0.75rem; --py:0.375rem; --ta:right; --weight:600; --c:#22c55e">
							<div style="--w:2.5rem">
								{#if model.stats.won === '-'}
									-
								{:else}
									<span style="--d:none"
	class="group-hover:inline"
										>{((model.stats.won / model.stats.count) * 100).toFixed(1)}%</span
									>
									<span class=" group-hover:hidden">{model.stats.won}</span>
								{/if}
							</div>
						</td>

						<td style="--px:0.75rem; --py:0.375rem; --ta:right; --weight:600; --c:#ef4444">
							<div style="--w:2.5rem">
								{#if model.stats.lost === '-'}
									-
								{:else}
									<span style="--d:none"
	class="group-hover:inline"
										>{((model.stats.lost / model.stats.count) * 100).toFixed(1)}%</span
									>
									<span class=" group-hover:hidden">{model.stats.lost}</span>
								{/if}
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</div>

<div style="--c:var(--color-gray-500); --size:0.75rem; --mt:0.375rem; --w:100%; --d:flex; --jc:flex-end">
	<div style="--ta:right">
		<div style="--line-clamp:1">
			ⓘ {$i18n.t(
				'The evaluation leaderboard is based on the Elo rating system and is updated in real-time.'
			)}
		</div>
		{$i18n.t(
			'The leaderboard is currently in beta, and we may adjust the rating calculations as we refine the algorithm.'
		)}
	</div>
</div>
