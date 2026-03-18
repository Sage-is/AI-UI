<script lang="ts">
	import CodeExecutionModal from './CodeExecutionModal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';

	export let codeExecutions = [];

	let selectedCodeExecution = null;
	let showCodeExecutionModal = false;

	$: if (codeExecutions) {
		updateSelectedCodeExecution();
	}

	const updateSelectedCodeExecution = () => {
		if (selectedCodeExecution) {
			selectedCodeExecution = codeExecutions.find(
				(execution) => execution.id === selectedCodeExecution.id
			);
		}
	};
</script>

<CodeExecutionModal bind:show={showCodeExecutionModal} codeExecution={selectedCodeExecution} />

{#if codeExecutions.length > 0}
	<div style="--mt:0.2rem; --mb:0.5rem; --w:100%; --d:flex; --g:0.2rem; --ai:center; --fw:wrap">
		{#each codeExecutions as execution (execution.id)}
			<div style="--d:flex; --g:0.2rem; --size:0.6rem; --weight:600">
				<button
					style="--d:flex; --dark-c:var(--color-gray-300); --py:0.2rem; --px:0.2rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.6rem; --maxw:24rem"
					on:click={() => {
						selectedCodeExecution = execution;
						showCodeExecutionModal = true;
					}}
				>
					<div
						style="--bgc:#fff; --dark-bgc:var(--color-gray-700); --radius:9999px; --w:1rem; --h:1rem; --d:flex; --ai:center; --jc:center"
					>
						{#if execution?.result}
							{#if execution.result?.error}
								<XMark />
							{:else if execution.result?.output}
								<Check strokeWidth="3" className="size-3" />
							{:else}
								<EllipsisHorizontal />
							{/if}
						{:else}
							<Spinner className="size-4" />
						{/if}
					</div>
					<div
						style="--fx:1 1 0%; --mx:0.5rem; --line-clamp:1"
	class="code-execution-name {execution?.result ? '' : 'pulse'}"
					>
						{execution.name}
					</div>
				</button>
			</div>
		{/each}
	</div>
{/if}

<style>
	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.6;
		}
	}

	.pulse {
		opacity: 1;
		animation: pulse 1.5s ease;
	}
</style>
