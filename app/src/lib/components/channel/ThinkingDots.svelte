<!--
  ThinkingDots.svelte — Animated bouncing dots for "is thinking" indicators.

  Renders three dots with staggered bounce animation. Used inside IndicatorStack
  to replace the static "is thinking..." text with a more dynamic feel.

  Usage: <ThinkingDots />
-->
<span class="thinking-dots" aria-label="thinking">
	<span class="dot">.</span>
	<span class="dot">.</span>
	<span class="dot">.</span>
</span>

<style>
	/* Bouncing dots animation — staggered so dots rise and fall in sequence */
	.thinking-dots {
		display: inline-flex;
		gap: 0.05em;
		margin-left: 0.1em;
	}

	.thinking-dots .dot {
		display: inline-block;
		animation: bounce 1.4s ease-in-out infinite;
		font-weight: 700;
	}

	/* Stagger each dot so they bounce in sequence, not unison */
	.thinking-dots .dot:nth-child(2) {
		animation-delay: 0.2s;
	}
	.thinking-dots .dot:nth-child(3) {
		animation-delay: 0.4s;
	}

	@keyframes bounce {
		0%,
		60%,
		100% {
			transform: translateY(0);
		}
		30% {
			transform: translateY(-3px);
		}
	}
</style>
