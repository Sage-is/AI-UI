<script lang="ts">
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let message;
	export let idx;

	export let onDelete;

	let textAreaElement: HTMLTextAreaElement;

	onMount(() => {
		textAreaElement.style.height = '';
		textAreaElement.style.height = textAreaElement.scrollHeight + 'px';
	});
</script>

<div style="--d:flex; --g:0.5rem"
	class="group">
	<div style="--d:flex; --ai:flex-start; --pt:0.25rem">
		<div
			style="--px:0.5rem; --py:0.25rem; --size:0.875rem; --weight:600; --tt:uppercase; --minw:6rem; --ta:left; --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
		>
			{$i18n.t(message.role)}
		</div>
	</div>

	<div style="--fx:1 1 0%">
		<!-- $i18n.t('a user') -->
		<!-- $i18n.t('an assistant') -->
		<textarea
			id="{message.role}-{idx}-textarea"
			bind:this={textAreaElement}
			style="--w:100%; --bgc:transparent; --oe:none; --radius:0.5rem; --p:0.5rem; --size:0.875rem; resize:none; --of:hidden"
			placeholder={$i18n.t(`Enter {{role}} message here`, {
				role: message.role === 'user' ? $i18n.t('a user') : $i18n.t('an assistant')
			})}
			rows="1"
			on:input={(e) => {
				textAreaElement.style.height = '';
				textAreaElement.style.height = textAreaElement.scrollHeight + 'px';
			}}
			on:focus={(e) => {
				textAreaElement.style.height = '';
				textAreaElement.style.height = textAreaElement.scrollHeight + 'px';

				// e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
			}}
			bind:value={message.content}
		/>
	</div>

	<div style="--pt:0.25rem">
		<button
			style="--dark-c:var(--color-gray-500, #9b9b9b); --hvr-dark-c:var(--color-gray-300, #cdcdcd); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
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
				style="--w:1.25rem; --h:1.25rem"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M15 12H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
				/>
			</svg>
		</button>
	</div>
</div>
