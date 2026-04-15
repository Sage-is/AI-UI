<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	import Skeleton from '$lib/components/chat/Messages/Skeleton.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
		import Textarea from '$lib/components/common/Textarea.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let message;
	export let idx;

	export let onDelete;
	export let onEdit;
	export let onInsert;

	let textAreaElement: HTMLTextAreaElement;
</script>

<div style="--d:flex; --fd:column; --g:0.2rem"
	class="group">
	<div style="--d:flex; --ai:center; --jc:space-between; --pt:0.2rem">
		<div style="--py:0.2rem; --size:0.8rem; --weight:600; --tt:uppercase; --minw:6rem; --ta:left; --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)">
			{$i18n.t(message.role)}
		</div>

		<div style="--d:flex; --ai:center; --g:0.5rem">
			<Tooltip placement="top" content={$i18n.t('Insert')}>
				<button
					style="--c:transparent; --hvr-dark-c:var(--color-gray-300); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="group-hover:text-gray-500"
					on:click={() => {
						onInsert();
					}}
				>
					<Icon name="arrow-up-left" className="size-3.5" strokeWidth="2" />
				</button>
			</Tooltip>

			<Tooltip placement="top" content={$i18n.t('Edit')}>
				<button
					style="--c:transparent; --hvr-dark-c:var(--color-gray-300); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="group-hover:text-gray-500"
					on:click={() => {
						onEdit();
					}}
				>
					<Icon name="pencil" className="size-3.5" strokeWidth="2" />
				</button>
			</Tooltip>

			<Tooltip placement="top" content={$i18n.t('Delete')}>
				<button
					style="--c:transparent; --hvr-dark-c:var(--color-gray-300); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="group-hover:text-gray-500"
					on:click={() => {
						onDelete();
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2"
						stroke="currentColor"
						style="--w:1rem; --h:1rem"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M15 12H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
						/>
					</svg>
				</button>
			</Tooltip>
		</div>
	</div>

	<div style="--fx:1 1 0%">
		<!-- $i18n.t('a user') -->
		<!-- $i18n.t('an assistant') -->

		{#if !(message?.done ?? true) && message?.content === ''}
			<div class="">
				<Skeleton size="sm" />
			</div>
		{:else if message?.edit === true}
			<Textarea
				className="w-full bg-transparent outline-hidden text-sm resize-none overflow-hidden"
				placeholder={$i18n.t(`Enter {{role}} message here`, {
					role: message.role === 'user' ? $i18n.t('a user') : $i18n.t('an assistant')
				})}
				bind:value={message.content}
				onBlur={() => {
					message.edit = false;
				}}
			/>
		{:else}
			<div style="--size:0.8rem"
	class="markdown-prose-sm">
				<Markdown id={`note-message-${idx}`} content={message.content} />
			</div>
		{/if}
	</div>
</div>
