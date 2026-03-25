<!--
  IndicatorStack.svelte — Stacked thinking/typing indicators for Spaces.

  Shows each thinking agent and typing user on its own line (not comma-joined).
  Agent thinking messages rotate through playful phrases with a crossfade.
  Scrollable if more than ~4 entries visible. Replaces the duplicate indicator
  rendering that was in Space.svelte, MessageInput.svelte, and Thread.svelte.

  Props:
    thinkingAgents — array of {name, ...} objects for agents currently thinking
    typingUsers    — array of {name, ...} objects for users currently typing

  Usage:
    <IndicatorStack {thinkingAgents} {typingUsers} />
-->
<script>
	import { onDestroy, getContext } from 'svelte';
	import ThinkingDots from './ThinkingDots.svelte';

	const i18n = getContext('i18n');

	/** @type {Array<{name: string}>} Agents currently thinking */
	export let thinkingAgents = [];
	/** @type {Array<{name: string}>} Users currently typing */
	export let typingUsers = [];

	// Rotating phrases for agent thinking — keeps it fun during longer waits.
	// The first entry is the default so the initial render is always sensible.
	const thinkingPhrases = [
		'is thinking',
		'is pondering',
		'is crafting a response',
		'is mulling it over',
		'is working on it',
		'is reasoning',
		'is connecting the dots',
		'is brewing something up'
	];

	// How often (ms) to rotate to the next phrase
	const ROTATE_INTERVAL = 4000;

	/** Map<agentKey, { index, interval }> — per-agent rotation state */
	let rotations = {};
	/** Map<agentKey, string> — current phrase per agent (reactive) */
	let agentPhrases = {};

	// Pick a random starting index (but not 0 — always start with "is thinking")
	const startPhrase = () => 0;

	// When thinkingAgents changes, sync rotation timers
	$: {
		const activeKeys = new Set(thinkingAgents.map((a) => a.name));

		// Start timers for new agents
		for (const agent of thinkingAgents) {
			if (!rotations[agent.name]) {
				const idx = startPhrase();
				agentPhrases[agent.name] = thinkingPhrases[idx];
				agentPhrases = agentPhrases; // trigger reactivity

				rotations[agent.name] = {
					index: idx,
					interval: setInterval(() => {
						rotations[agent.name].index =
							(rotations[agent.name].index + 1) % thinkingPhrases.length;
						agentPhrases[agent.name] =
							thinkingPhrases[rotations[agent.name].index];
						agentPhrases = agentPhrases;
					}, ROTATE_INTERVAL)
				};
			}
		}

		// Clean up timers for agents that stopped thinking
		for (const key of Object.keys(rotations)) {
			if (!activeKeys.has(key)) {
				clearInterval(rotations[key].interval);
				delete rotations[key];
				delete agentPhrases[key];
				agentPhrases = agentPhrases;
			}
		}
	}

	onDestroy(() => {
		for (const key of Object.keys(rotations)) {
			clearInterval(rotations[key].interval);
		}
	});
</script>

{#if thinkingAgents.length > 0 || typingUsers.length > 0}
	<!-- Container: max ~4 lines visible, scrolls if more -->
	<div style="--maxh:4rem; --ofy:auto; --d:flex; --fd:column; --g:0.1rem; --size:0.65rem; --px:1rem; --mb:0.25rem">
		<!-- Thinking agents — blue, one per line with rotating phrase + animated dots -->
		{#each thinkingAgents as agent (agent.name)}
			<div style="--d:flex; --ai:center">
				<span style="--weight:500; --c:var(--color-blue-600); --dark-c:var(--color-blue-400)">
					{agent.name}
				</span>
				<!-- Keyed block forces re-mount → re-triggers fadePhrase animation on each phrase change -->
				{#key agentPhrases[agent.name]}
					<span class="thinking-phrase">
						&nbsp;{$i18n.t(agentPhrases[agent.name] || 'is thinking')}
					</span>
				{/key}
				<ThinkingDots />
			</div>
		{/each}

		<!-- Typing users — default color, one per line -->
		{#each typingUsers as user (user.name)}
			<div>
				<span style="--weight:500; --c:#000; --dark-c:#fff">
					{user.name}
				</span>
				{$i18n.t('is typing...')}
			</div>
		{/each}
	</div>
{/if}

<style>
	/* Smooth crossfade when the phrase text swaps */
	.thinking-phrase {
		display: inline-block;
		animation: fadePhrase 0.5s ease-in-out;
	}

	@keyframes fadePhrase {
		0% {
			opacity: 0;
			transform: translateY(2px);
		}
		100% {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
