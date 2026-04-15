<script lang="ts">
	import { getContext } from 'svelte';
	import CodeBlock from './CodeBlock.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Icon from '$lib/components/Icon.svelte';
		const i18n = getContext('i18n');

	export let show = false;
	export let codeExecution = null;
</script>

<Modal size="lg" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300); --px:1.2rem; --pt:1rem; --pb:0.5rem">
			<div style="--size:1.125rem; --weight:500; --as:center; --d:flex; --fd:column; --g:0.125rem; --tt:capitalize">
				{#if codeExecution?.result}
					<div>
						{#if codeExecution.result?.error}
							<Badge type="error" content="error" />
						{:else if codeExecution.result?.output}
							<Badge type="success" content="success" />
						{:else}
							<Badge type="warning" content="incomplete" />
						{/if}
					</div>
				{/if}

				<div style="--d:flex; --g:0.5rem; --ai:center">
					{#if !codeExecution?.result}
						<div>
							<Spinner className="size-4" />
						</div>
					{/if}

					<div>
						{#if codeExecution?.name}
							{$i18n.t('Code execution')}: {codeExecution?.name}
						{:else}
							{$i18n.t('Code execution')}
						{/if}
					</div>
				</div>
			</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
					codeExecution = null;
				}}
			>
				<Icon name="x-mark" strokeWidth="2" className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1rem; --pb:1.2rem">
			<div
				style="--d:flex; --fd:column; --w:100%; --dark-c:var(--color-gray-200); --ofy:scroll; --maxh:22rem"
	class="scrollbar-hidden"
			>
				<div style="--d:flex; --fd:column; --w:100%">
					<CodeBlock
						id="code-exec-{codeExecution?.id}-code"
						lang={codeExecution?.language ?? ''}
						code={codeExecution?.code ?? ''}
						className=""
						editorClassName={codeExecution?.result &&
						(codeExecution?.result?.error || codeExecution?.result?.output)
							? 'rounded-b-none'
							: ''}
						stickyButtonsClassName="top-0"
						run={false}
					/>
				</div>

				{#if codeExecution?.result && (codeExecution?.result?.error || codeExecution?.result?.output)}
					<div style="--dark-bgc:#202123; --dark-c:#fff; --px:1rem; --py:1rem; --bblr:0.5rem; --bbrr:0.5rem; --d:flex; --fd:column; --g:0.6rem">
						{#if codeExecution?.result?.error}
							<div>
								<div style="--c:var(--color-gray-500); --size:0.6rem; --mb:0.2rem">{$i18n.t('ERROR')}</div>
								<div style="--size:0.8rem">{codeExecution?.result?.error}</div>
							</div>
						{/if}
						{#if codeExecution?.result?.output}
							<div>
								<div style="--c:var(--color-gray-500); --size:0.6rem; --mb:0.2rem">{$i18n.t('OUTPUT')}</div>
								<div style="--size:0.8rem">{codeExecution?.result?.output}</div>
							</div>
						{/if}
					</div>
				{/if}
				{#if codeExecution?.result?.files && codeExecution?.result?.files.length > 0}
					<div style="--d:flex; --fd:column; --w:100%">
						<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />
						<div style="--size:0.8rem; --weight:500; --dark-c:var(--color-gray-300)">
							{$i18n.t('Files')}
						</div>
						<ul style="--mt:0.2rem; list-style-type:disc; --pl:1rem; --size:0.6rem">
							{#each codeExecution?.result?.files as file}
								<li>
									<a href={file.url} target="_blank">{file.name}</a>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>
