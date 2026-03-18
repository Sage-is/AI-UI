<script lang="ts">
	import Switch from '$lib/components/common/Switch.svelte';
	import { config, models, settings, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import ManageModal from './Personalization/ManageModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	let showManageModal = false;

	// Addons
	let enableMemory = false;

	onMount(async () => {
		enableMemory = $settings?.memory ?? false;
	});
</script>

<ManageModal bind:show={showManageModal} />

<form
	id="tab-personalization"
	style="--d:flex; --fd:column; --h:100%; --jc:space-between; --g:0.6rem; --size:0.8rem"
	on:submit|preventDefault={() => {
		dispatch('save');
	}}
>
	<div style="--py:0.2rem; --ofy:scroll; --maxh:28rem; --maxh-lg:100%">
		<div>
			<div style="--d:flex; --ai:center; --jc:space-between; --mb:0.2rem">
				<Tooltip
					content={$i18n.t(
						'This is an experimental feature, it may not function as expected and is subject to change at any time.'
					)}
				>
					<div style="--size:0.8rem; --weight:500">
						{$i18n.t('Memory')}

						<span style="--size:0.6rem; --c:var(--color-gray-500)">({$i18n.t('Experimental')})</span>
					</div>
				</Tooltip>

				<div class="">
					<Switch
						bind:state={enableMemory}
						on:change={async () => {
							saveSettings({ memory: enableMemory });
						}}
					/>
				</div>
			</div>
		</div>

		<div style="--size:0.6rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400)">
			<div>
				{$i18n.t(
					"You can personalize your interactions with LLMs by adding memories through the 'Manage' button below, making them more helpful and tailored to you."
				)}
			</div>

			<!-- <div style="--mt:0.6rem">
				To understand what LLM remembers or teach it something new, just chat with it:

				<div>- “Remember that I like concise responses.”</div>
				<div>- “I just got a puppy!”</div>
				<div>- “What do you remember about me?”</div>
				<div>- “Where did we leave off on my last project?”</div>
			</div> -->
		</div>

		<div style="--mt:0.6rem; --mb:0.2rem; --ml:0.2rem">
			<button
				type="button"
				style="--px:0.8rem; --py:0.4rem; --weight:500; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); outline-style:solid; outline-width:1px; outline-color:var(--color-gray-300); outline-color:var(--color-gray-800); --radius:1.5rem"
				on:click={() => {
					showManageModal = true;
				}}
			>
				{$i18n.t('Manage')}
			</button>
		</div>
	</div>

	<div style="--d:flex; --jc:flex-end; --size:0.8rem; --weight:500">
		<button
			style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
