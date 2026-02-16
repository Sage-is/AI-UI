<script>
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { updateMemoryById } from '$lib/apis/memories';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const dispatch = createEventDispatcher();

	export let show;
	export let memory = {};

	const i18n = getContext('i18n');

	let loading = false;
	let content = '';

	$: if (show) {
		setContent();
	}

	const setContent = () => {
		content = memory.content;
	};

	const submitHandler = async () => {
		loading = true;

		const res = await updateMemoryById(localStorage.token, memory.id, content).catch((error) => {
			toast.error(`${error}`);

			return null;
		});

		if (res) {
			console.log(res);
			toast.success($i18n.t('Memory updated successfully'));
			dispatch('save');
			show = false;
		}

		loading = false;
	};
</script>

<Modal bind:show size="sm">
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300, #cdcdcd); --px:1.25rem; --pt:1rem; --pb:0.5rem">
			<div style="--size:1.125rem; --weight:500; --as:center">
				{$i18n.t('Edit Memory')}
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

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1.25rem; --pb:1rem; --g-md:1rem; --dark-c:var(--color-gray-200, #e3e3e3)">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<form
					style="--d:flex; --fd:column; --w:100%"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="">
						<textarea
							bind:value={content}
							rows="6"
							style="--bgc:transparent; --w:100%; --size:0.875rem; --radius:0.75rem; --p:0.75rem; outline-style:solid; outline-width:1px; outline-color:var(--color-gray-100, #ececec); outline-color:var(--color-gray-800, #333); resize: vertical;"
							placeholder={$i18n.t('Enter a detail about yourself for your LLMs to recall')}
						/>

						<div style="--size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">
							ⓘ {$i18n.t('Refer to yourself as "User" (e.g., "User is learning Spanish")')}
						</div>
					</div>

					<div style="--d:flex; --jc:flex-end; --pt:0.25rem; --size:0.875rem; --weight:500">
						<button
							style="--px:1rem; --py:0.5rem; --bgc:#047857; --hvr-bgc:#065f46; --c:var(--color-gray-100, #ececec); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:1.5rem; --d:flex; --fd:row; --g:0.25rem; --ai:center"
	class="{loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Update')}

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
