<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	export let show = false;
	export let query = '';
	export let participants: { users: any[]; agents: any[] } = { users: [], agents: [] };
	export let onSelect: (participant: any) => void = () => {};

	let selectedIdx = 0;

	$: filteredParticipants = getFilteredParticipants(query, participants);

	function getFilteredParticipants(
		q: string,
		p: { users: any[]; agents: any[] }
	): { type: string; data: any }[] {
		const lowerQ = q.toLowerCase();
		const results: { type: string; data: any }[] = [];

		for (const agent of p.agents ?? []) {
			const name = (agent.name || '').toLowerCase();
			if (!lowerQ || name.includes(lowerQ) || name.replace(/\s+/g, '-').includes(lowerQ)) {
				results.push({ type: 'agent', data: agent });
			}
		}

		for (const user of p.users ?? []) {
			const name = (user.name || '').toLowerCase();
			if (!lowerQ || name.includes(lowerQ)) {
				results.push({ type: 'user', data: user });
			}
		}

		return results;
	}

	$: if (filteredParticipants) {
		selectedIdx = 0;
	}

	export const selectUp = () => {
		selectedIdx = Math.max(0, selectedIdx - 1);
	};

	export const selectDown = () => {
		selectedIdx = Math.min(filteredParticipants.length - 1, selectedIdx + 1);
	};

	export const getSelected = () => {
		return filteredParticipants[selectedIdx] ?? null;
	};
</script>

{#if show}
	<div
		id="commands-container"
		style="--pos:absolute; --bottom:100%; --left:0; --right:0; --mb:0.5rem; --maxh:12rem; --ofy:auto; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --radius:0.75rem; --shadow:5;  --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --py:0.25rem"
		class="scrollbar-hidden"
	>
		{#if filteredParticipants.length === 0}
			<div style="--px:0.75rem; --py:0.5rem; --size:0.8rem; --c:var(--color-gray-500)">
				{$i18n.t('No participants found')}
			</div>
		{/if}
		{#each filteredParticipants as participant, idx}
			<button
				class="w-full {idx === selectedIdx
					? 'bg-gray-100 dark:bg-gray-800 selected-command-option-button'
					: 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}"
				style="--d:flex; --ai:center; --g:0.5rem; --px:0.75rem; --py:0.4rem; --size:0.85rem; --w:100%; --ta:left"
				on:click={() => onSelect(participant)}
			>
				<img
					src={participant.type === 'agent'
						? participant.data.profile_image_url || '/static/icons/favicon.png'
						: participant.data.profile_image_url || '/static/user.png'}
					alt={participant.data.name}
					style="--w:1.5rem; --h:1.5rem; --radius:9999px; --objf:cover"
				/>
				<span style="--weight:500">{participant.data.name}</span>
				{#if participant.type === 'agent'}
					<span
						style="--size:0.6rem; --px:0.35rem; --py:0.1rem; --radius:0.25rem; --bgc:var(--color-blue-100); --dark-bgc:var(--color-blue-900); --c:var(--color-blue-700); --dark-c:var(--color-blue-300); --weight:600"
					>
						BOT
					</span>
				{/if}
			</button>
		{/each}
	</div>
{/if}
