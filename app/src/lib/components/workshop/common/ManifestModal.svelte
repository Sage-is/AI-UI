<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';

	import Modal from '../../common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let manifest = {};
</script>

<Modal size="sm" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300, #cdcdcd); --px:1.25rem; --pt:1rem; --pb:0.5rem">
			<div style="--size:1.125rem; --weight:500; --as:center">{$i18n.t('Show your support!')}</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1.25rem; --pb:1rem; --g-md:1rem; --dark-c:var(--color-gray-200, #e3e3e3)">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<form
					style="--d:flex; --fd:column; --w:100%"
					on:submit|preventDefault={() => {
						show = false;
					}}
				>
					<div style="--px:0.25rem; --size:0.875rem">
						<div style="--my:0.5rem">
							{$i18n.t(
								'The developers behind this plugin are passionate volunteers from the community. If you find this plugin helpful, please consider contributing to its development.'
							)}
						</div>

						<div style="--my:0.5rem">
							{$i18n.t(
								'Your entire contribution will go directly to the plugin developer; Sage.is AI does not take any percentage. However, the chosen funding platform might have its own fees.'
							)}
						</div>

						<hr style="--dark-bc:var(--color-gray-800, #333); --my:0.75rem" />
						<div style="--my:0.5rem">
							{$i18n.t('Support this plugin:')}
							<a
								href={manifest.funding_url}
								target="_blank"
								style="--td:underline; --c:#60a5fa; --hvr-c:#93c5fd">{manifest.funding_url}</a
							>
						</div>
					</div>

					<div style="--d:flex; --jc:flex-end; --pt:0.75rem; --size:0.875rem; --weight:500">
						<button
							style="--px:1rem; --py:0.5rem; --bgc:#047857; --hvr-bgc:#065f46; --c:var(--color-gray-100, #ececec); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem; --d:flex; --fd:row; --g:0.25rem; --ai:center"
							type="submit"
						>
							{$i18n.t('Done')}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		/* display: none; <- Crashes Chrome on hover */
		-webkit-appearance: none;
		margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
	}

	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}

	input[type='number'] {
		-moz-appearance: textfield; /* Firefox */
	}
</style>
