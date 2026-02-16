<script>
	import { knowledge, prompts } from '$lib/stores';

	import { removeLastWordFromString } from '$lib/utils';
	import { getPrompts } from '$lib/apis/prompts';
	import { getKnowledgeBases } from '$lib/apis/knowledge';

	import Prompts from './Commands/Prompts.svelte';
	import Knowledge from './Commands/Knowledge.svelte';
	import Models from './Commands/Models.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let show = false;

	export let files = [];
	export let command = '';

	export let onSelect = (e) => {};
	export let onUpload = (e) => {};

	export let insertTextHandler = (text) => {};

	let loading = false;
	let commandElement = null;

	export const selectUp = () => {
		commandElement?.selectUp();
	};

	export const selectDown = () => {
		commandElement?.selectDown();
	};

	$: if (show) {
		init();
	}

	const init = async () => {
		loading = true;
		await Promise.all([
			(async () => {
				prompts.set(await getPrompts(localStorage.token));
			})(),
			(async () => {
				knowledge.set(await getKnowledgeBases(localStorage.token));
			})()
		]);
		loading = false;
	};
</script>

{#if show}
	{#if !loading}
		{#if command?.charAt(0) === '/'}
			<Prompts
				bind:this={commandElement}
				{command}
				onSelect={(e) => {
					const { type, data } = e;

					if (type === 'prompt') {
						insertTextHandler(data.content);
					}
				}}
			/>
		{:else if (command?.charAt(0) === '#' && command.startsWith('#') && !command.includes('# ')) || ('\\#' === command.slice(0, 2) && command.startsWith('#') && !command.includes('# '))}
			<Knowledge
				bind:this={commandElement}
				command={command.includes('\\#') ? command.slice(2) : command}
				onSelect={(e) => {
					const { type, data } = e;

					if (type === 'knowledge') {
						insertTextHandler('');

						onUpload({
							type: 'file',
							data: data
						});
					} else if (type === 'youtube') {
						insertTextHandler('');

						onUpload({
							type: 'youtube',
							data: data
						});
					} else if (type === 'web') {
						insertTextHandler('');

						onUpload({
							type: 'web',
							data: data
						});
					}
				}}
			/>
		{:else if command?.charAt(0) === '@'}
			<Models
				bind:this={commandElement}
				{command}
				onSelect={(e) => {
					const { type, data } = e;

					if (type === 'model') {
						insertTextHandler('');

						onSelect({
							type: 'model',
							data: data
						});
					}
				}}
			/>
		{/if}
	{:else}
		<div
			id="commands-container"
			style="--px:0.5rem; --mb:0.5rem; --ta:left; --w:100%; --pos:absolute; --bottom:0; --left:0; --right:0; --z:10"
		>
			<div style="--d:flex; --w:100%; --radius:0.75rem; --b:1px solid; --bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-850, #262626)">
				<div
					style="--maxh:15rem; --d:flex; --fd:column; --w:100%; --radius:0.75rem; --bgc:#fff; --dark-bgc:var(--color-gray-900, #171717); --dark-c:var(--color-gray-100, #ececec)"
				>
					<Spinner />
				</div>
			</div>
		</div>
	{/if}
{/if}
