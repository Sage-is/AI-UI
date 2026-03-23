<!--
  IndicatorStack.svelte — Stacked thinking/typing indicators for Spaces.

  Shows each thinking agent and typing user on its own line (not comma-joined).
  Scrollable if more than ~4 entries visible. Replaces the duplicate indicator
  rendering that was in Space.svelte, MessageInput.svelte, and Thread.svelte.

  Props:
    thinkingAgents — array of {name, ...} objects for agents currently thinking
    typingUsers    — array of {name, ...} objects for users currently typing

  Usage:
    <IndicatorStack {thinkingAgents} {typingUsers} />
-->
<script>
	import { getContext } from 'svelte';
	import ThinkingDots from './ThinkingDots.svelte';

	const i18n = getContext('i18n');

	/** @type {Array<{name: string}>} Agents currently thinking */
	export let thinkingAgents = [];
	/** @type {Array<{name: string}>} Users currently typing */
	export let typingUsers = [];
</script>

{#if thinkingAgents.length > 0 || typingUsers.length > 0}
	<!-- Container: max ~4 lines visible, scrolls if more -->
	<div style="--maxh:4rem; --ofy:auto; --d:flex; --fd:column; --g:0.1rem; --size:0.65rem; --px:1rem; --mb:0.25rem">
		<!-- Thinking agents — blue, one per line with animated dots -->
		{#each thinkingAgents as agent (agent.name)}
			<div>
				<span style="--weight:500; --c:var(--color-blue-600); --dark-c:var(--color-blue-400)">
					{agent.name}
				</span>
				{$i18n.t('is thinking')}<ThinkingDots />
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
