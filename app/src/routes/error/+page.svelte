<script>
	import { goto } from '$app/navigation';
	import { WEBUI_NAME, config } from '$lib/stores';
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if ($config) {
			await goto('/');
		}

		loaded = true;
	});
</script>

{#if loaded}
	<div style="--pos:absolute; --w:100%; --h:100%; --d:flex; --z:50">
		<div style="--pos:absolute; --radius:0.6rem; --w:100%; --h:100%; backdrop-filter:blur(4px); --d:flex; --jc:center">
			<div style="--m:auto; --pb:11rem; --d:flex; --fd:column; --jc:center">
				<div style="--maxw:28rem">
					<div style="--ta:center; --size:1.5rem; --weight:500; --z:50">
						{$i18n.t('{{webUIName}} Backend Required', { webUIName: $WEBUI_NAME })}
					</div>

					<div style="--mt:1rem; --ta:center; --size:0.875rem; --w:100%">
						{$i18n.t(
							"Oops! You're using an unsupported method (frontend only). Please serve the WebUI from the backend."
						)}

						<br class=" " />
						<br class=" " />
						<a
							style="--weight:600; --td:underline"
							href="https://github.com/Sage-is/AI-UI#how-to-install-"
							target="_blank">{$i18n.t('See readme.md for instructions')}</a
						>
						{$i18n.t('or')}
						<a style="--weight:600; --td:underline" href="https://discord.gg/NkbYZJpX6D" target="_blank"
							>{$i18n.t('join our Discord for help.')}</a
						>
					</div>

					<div style="--mt:1.5rem; --mx:auto; --pos:relative; --w:fit-content"
	class="group">
						<button
							style="--pos:relative; --z:20; --d:flex; --px:1.25rem; --py:0.5rem; --radius:9999px; --bgc:var(--color-gray-100); --hvr-bgc:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --size:0.875rem"
							on:click={() => {
								location.href = '/';
							}}
						>
							{$i18n.t('Check Again')}
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
