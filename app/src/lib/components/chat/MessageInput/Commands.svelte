<script>
	import { knowledge, prompts } from '$lib/stores';

	import { removeLastWordFromString } from '$lib/utils';
	import { getPrompts } from '$lib/apis/prompts';
	import { getKnowledgeBases } from '$lib/apis/knowledge';

	import Prompts from './Commands/Prompts.svelte';
	import Knowledge from './Commands/Knowledge.svelte';
	import Models from './Commands/Models.svelte';
	import Mentions from '$lib/components/channel/MessageInput/Mentions.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let show = false;

	export let files = [];
	export let command = '';
	/** Space participants for @mention autocomplete; null in regular chat (falls back to model selector). */
	export let spaceParticipants = null;

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

	// Only load prompts/knowledge for / and # commands — @mentions don't need them.
	$: if (show && command?.charAt(0) !== '@') {
		init();
	}

	/** Load prompts and knowledge bases for / and # command dropdowns. */
	const init = async () => {
		loading = true;
		try {
			await Promise.all([
				(async () => {
					prompts.set(await getPrompts(localStorage.token));
				})(),
				(async () => {
					knowledge.set(await getKnowledgeBases(localStorage.token));
				})()
			]);
		} catch (e) {
			console.error('[Commands] Failed to load prompts/knowledge:', e);
		}
		loading = false;
	};
</script>

{#if show}
	<!-- @mentions render immediately — no loading needed, participants are already loaded -->
	{#if command?.charAt(0) === '@'}
		{#if spaceParticipants?.users?.length > 0 || spaceParticipants?.agents?.length > 0}
			<Mentions
				bind:this={commandElement}
				participants={spaceParticipants}
				query={command.slice(1)}
				show={true}
				onSelect={(participant) => {
					insertTextHandler(`@${participant.data.name} `);
				}}
			/>
		{:else}
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

	<!-- / and # commands wait for prompts/knowledge to load -->
	{:else if !loading}
		{#if command?.charAt(0) === '/'}
			<Prompts
				bind:this={commandElement}
				{command}
				onSelect={(e) => {
					const { type, data } = e;

					if (type === 'prompt') {
						insertTextHandler(data.content, data.title);
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
		{/if}

	<!-- Loading spinner (only for / and # commands) -->
	{:else}
		<div
			id="commands-container"
			style="--px:0.5rem; --mb:0.5rem; --ta:left; --w:100%; --pos:absolute; --bottom:0; --left:0; --right:0; --z:10"
		>
			<div style="--d:flex; --w:100%; --radius:0.6rem;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)">
				<div
					style="--maxh:15rem; --d:flex; --fd:column; --w:100%; --radius:0.6rem; --bgc:#fff; --dark-bgc:var(--color-gray-900); --dark-c:var(--color-gray-100)"
				>
					<Spinner />
				</div>
			</div>
		</div>
	{/if}
{/if}
