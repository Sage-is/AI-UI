<script lang="ts">
	import { getContext, createEventDispatcher, onMount } from 'svelte';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import { toast } from 'svelte-sonner';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Knowledge from '$lib/components/workshop/Models/Knowledge.svelte';
	import { user } from '$lib/stores';
	const i18n = getContext('i18n');

	export let show = false;
	export let onSubmit: Function = (e) => {};

	export let edit = false;

	export let folder = null;

	let name = '';
	let data = {
		system_prompt: '',
		files: []
	};

	let loading = false;

	const submitHandler = async () => {
		loading = true;
		await onSubmit({
			name,
			data
		});
		show = false;
		loading = false;
	};

	const init = () => {
		name = folder.name;
		data = folder.data || {
			system_prompt: '',
			files: []
		};
	};

	$: if (folder) {
		init();
	}

	$: if (!show && !edit) {
		name = '';
		data = {
			system_prompt: '',
			files: []
		};
	}
</script>

<Modal size="md" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300); --px:1.25rem; --pt:1rem; --pb:0.25rem">
			<div style="--size:1.125rem; --weight:500; --as:center">
				{#if edit}
					{$i18n.t('Edit Folder')}
				{:else}
					{$i18n.t('Create Folder')}
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

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1.25rem; --pb:1rem; --p: 1rem 0;--bgc: var(--white); --br: 1rem; --shadow: 6">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<form
					style="--d:flex; --fd:column; --w:100%"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div style="--d:flex; --fd:column; --w:100%; --mt:0.25rem">
						<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500)">{$i18n.t('Folder Name')}</div>

						<div style="--fx:1 1 0%">
							<input
								style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
	class="placeholder:text-gray-300 dark:placeholder:text-gray-700"
								type="text"
								bind:value={name}
								placeholder={$i18n.t('Enter folder name')}
								autocomplete="off"
							/>
						</div>
					</div>

					<hr style="--bc:var(--color-gray-50); --dark-bc:var(--color-gray-850); --my:0.625rem; --w:100%" />

					{#if $user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true)}
						<div style="--my:0.25rem">
							<div style="--mb:0.5rem; --size:0.75rem; --c:var(--color-gray-500)">Folder {$i18n.t('System Prompt')}</div>
							<div>
								<Textarea
									className=" text-sm w-full bg-transparent outline-hidden "
									placeholder={`Write your model system prompt content here\ne.g.) You are Mario from Super Mario Bros, acting as an assistant.`}
									maxSize={200}
									bind:value={data.system_prompt}
								/>
							</div>
						</div>
					{/if}

					<div style="--my:0.5rem">
						<Knowledge bind:selectedItems={data.files}>
							<div slot="label">
								<div style="--d:flex; --w:100%; --jc:space-between">
									<div style="--mb:0.5rem; --size:0.75rem; --c:var(--color-gray-500)">
										{$i18n.t('Knowledge')}
									</div>
								</div>
							</div>
						</Knowledge>
					</div>

					<div style="--d:flex; --jc:flex-end; --pt:0.75rem; --size:0.875rem; --weight:500; --g:0.375rem">
						<button
							style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-950); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.25rem; --ai:center"
	class="{loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Save')}

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
