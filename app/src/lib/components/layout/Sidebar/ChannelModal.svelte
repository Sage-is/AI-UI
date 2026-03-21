<script lang="ts">
	import { getContext, createEventDispatcher, onMount } from 'svelte';
	import { createNewChannel, deleteChannelById } from '$lib/apis/spaces';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import AccessControl from '$lib/components/workshop/common/AccessControl.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import { toast } from 'svelte-sonner';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	const i18n = getContext('i18n');

	export let show = false;
	export let onSubmit: Function = () => {};
	export let onUpdate: Function = () => {};

	export let channel = null;
	export let edit = false;

	let name = '';
	let accessControl = {};

	let loading = false;

	$: if (name) {
		name = name.replace(/\s/g, '-').toLocaleLowerCase();
	}

	const submitHandler = async () => {
		loading = true;
		await onSubmit({
			name: name.replace(/\s/g, '-'),
			access_control: accessControl
		});
		show = false;
		loading = false;
	};

	const init = () => {
		name = channel.name;
		accessControl = channel.access_control;
	};

	$: if (channel) {
		init();
	}

	let showDeleteConfirmDialog = false;

	const deleteHandler = async () => {
		showDeleteConfirmDialog = false;

		const res = await deleteChannelById(localStorage.token, channel.id).catch((error) => {
			toast.error(error.message);
		});

		if (res) {
			toast.success('Channel deleted successfully');
			onUpdate();

			if ($page.url.pathname === `/space/${channel.id}`) {
				goto('/');
			}
		}

		show = false;
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300); --px:1.2rem; --pt:1rem; --pb:0.2rem">
			<div style="--size:1.125rem; --weight:500; --as:center">
				{#if edit}
					{$i18n.t('Edit Channel')}
				{:else}
					{$i18n.t('Create Channel')}
				{/if}
			</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1.2rem; --pb:1rem; --p: 1rem 0;--bgc: var(--white); --br: 1rem">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<form
					style="--d:flex; --fd:column; --w:100%"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div style="--d:flex; --fd:column; --w:100%; --mt:0.5rem">
						<div style="--mb:0.2rem; --size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Channel Name')}</div>

						<div style="--fx:1 1 0%">
							<input
								style="--w:100%; --size:0.8rem; --bgc:transparent; --oe:none"
	class="placeholder:text-gray-300 dark:placeholder:text-gray-700"
								type="text"
								bind:value={name}
								placeholder={$i18n.t('new-channel')}
								autocomplete="off"
							/>
						</div>
					</div>

					<hr style="--bc:var(--color-gray-100); --dark-bc:rgb(78 78 78 / 0.1); --my:0.6rem; --w:100%" />

					<div style="--my:0.5rem; --mx:-0.5rem">
						<div style="--px:0.6rem; --py:0.5rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-950); --radius:0.5rem">
							<AccessControl bind:accessControl />
						</div>
					</div>

					<div style="--d:flex; --jc:flex-end; --pt:0.6rem; --size:0.8rem; --weight:500; --g:0.4rem">
						{#if edit}
							<button
								style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --dark-bgc:#000; --hvr-dark-bgc:rgb(0 0 0 / 0.9); --dark-c:#fff; --bgc:#fff; --c:#000; --hvr-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.2rem; --ai:center"
								type="button"
								on:click={() => {
									showDeleteConfirmDialog = true;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}

						<button
							style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-950); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.2rem; --ai:center"
	class="{loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{#if edit}
								{$i18n.t('Update')}
							{:else}
								{$i18n.t('Create')}
							{/if}

							{#if loading}
								<div style="--ml:0.5rem; --as:center">
									<Spinner />
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<DeleteConfirmDialog
	bind:show={showDeleteConfirmDialog}
	message={$i18n.t('Are you sure you want to delete this channel?')}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={() => {
		deleteHandler();
	}}
/>
