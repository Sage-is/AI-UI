<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	export let onSubmit: Function = () => {};
	export let show = false;

	let name = '';
	let description = '';
	let userIds = [];

	let loading = false;

	const submitHandler = async () => {
		loading = true;

		const group = {
			name,
			description
		};

		await onSubmit(group);

		loading = false;
		show = false;

		name = '';
		description = '';
		userIds = [];
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-100); --px:1.25rem; --pt:1rem; --mb:0.375rem">
			<div style="--size:1.125rem; --weight:500; --as:center"
	class="font-primary">
				{$i18n.t('Add User Group')}
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

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1rem; --pb:1rem; --p: 1rem 0;--bgc: var(--white); --br: 1rem; --shadow: 6">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<form
					style="--d:flex; --fd:column; --w:100%"
					on:submit={(e) => {
						e.preventDefault();
						submitHandler();
					}}
				>
					<div style="--px:0.25rem; --d:flex; --fd:column; --w:100%">
						<div style="--d:flex; --g:0.5rem">
							<div style="--d:flex; --fd:column; --w:100%">
								<div style="--mb:0.125rem; --size:0.75rem; --c:var(--color-gray-500)">{$i18n.t('Name')}</div>

								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
	class="placeholder:text-gray-300 dark:placeholder:text-gray-700"
										type="text"
										bind:value={name}
										placeholder={$i18n.t('Group Name')}
										autocomplete="off"
										required
									/>
								</div>
							</div>
						</div>

						<div style="--d:flex; --fd:column; --w:100%; --mt:0.5rem">
							<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500)">{$i18n.t('Description')}</div>

							<div style="--fx:1 1 0%">
								<Textarea
									className="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden resize-none"
									rows={2}
									bind:value={description}
									placeholder={$i18n.t('Group Description')}
								/>
							</div>
						</div>
					</div>

					<div style="--d:flex; --jc:flex-end; --pt:0.75rem; --size:0.875rem; --weight:500; --g:0.375rem">
						<button
							style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.25rem; --ai:center"
	class="{loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Create')}

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
