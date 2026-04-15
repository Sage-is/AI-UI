<script lang="ts" context="module">
	import { marked, type Token } from 'marked';

	type AlertType = 'NOTE' | 'TIP' | 'IMPORTANT' | 'WARNING' | 'CAUTION';

	interface AlertTheme {
		border: string;
		text: string;
		icon: string;
	}

	export interface AlertData {
		type: AlertType;
		text: string;
		tokens: Token[];
	}

	const alertStyles: Record<AlertType, AlertTheme> = {
		NOTE: {
			border: 'border-sky-500',
			text: 'text-sky-500',
			icon: 'info'
		},
		TIP: {
			border: 'border-emerald-500',
			text: 'text-emerald-500',
			icon: 'light-bulb'
		},
		IMPORTANT: {
			border: 'border-purple-500',
			text: 'text-purple-500',
			icon: 'star'
		},
		WARNING: {
			border: 'border-yellow-500',
			text: 'text-yellow-500',
			icon: 'arrow-right-circle'
		},
		CAUTION: {
			border: 'border-rose-500',
			text: 'text-rose-500',
			icon: 'bolt'
		}
	};

	export function alertComponent(token: Token): AlertData | false {
		const regExpStr = `^(?:\\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\\])\\s*?\n*`;
		const regExp = new RegExp(regExpStr);
		const matches = token.text?.match(regExp);

		if (matches && matches.length) {
			const alertType = matches[1] as AlertType;
			const newText = token.text.replace(regExp, '');
			const newTokens = marked.lexer(newText);
			return {
				type: alertType,
				text: newText,
				tokens: newTokens
			};
		}
		return false;
	}
</script>

<script lang="ts">
	import MarkdownTokens from './MarkdownTokens.svelte';
	import Icon from '$lib/components/Icon.svelte';

	export let token: Token;
	export let alert: AlertData;
	export let id = '';
	export let tokenIdx = 0;
	export let onTaskClick: ((event: MouseEvent) => void) | undefined = undefined;
	export let onSourceClick: ((event: MouseEvent) => void) | undefined = undefined;
</script>

<!--

Renders the following Markdown as alerts:

> [!NOTE]
> Example note

> [!TIP]
> Example tip

> [!IMPORTANT]
> Example important

> [!CAUTION]
> Example caution

> [!WARNING]
> Example warning

-->
<div class={`border-l-4 pl-2.5 ${alertStyles[alert.type].border} my-0.5`}>
	<div style="--ai:center; --d:flex; --g:0.2rem; --py:0.4rem"
	class="{alertStyles[alert.type].text}">
		<Icon name={alertStyles[alert.type].icon} className="inline-block size-4" />
		<span style="--weight:500">{alert.type}</span>
	</div>
	<div style="--pb:0.5rem">
		<MarkdownTokens id={`${id}-${tokenIdx}`} tokens={alert.tokens} {onTaskClick} {onSourceClick} />
	</div>
</div>
