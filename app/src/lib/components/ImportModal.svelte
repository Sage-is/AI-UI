<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { extractFrontmatter } from '$lib/utils';

	export let show = false;

	export let onImport = (e) => {};
	export let onClose = () => {};

	export let loadUrlHandler: Function = () => {};
	export let successMessage: string = '';

	let loading = false;
	let url = '';

	const submitHandler = async () => {
		loading = true;

		if (!url) {
			toast.error($i18n.t('Please enter a valid URL'));
			loading = false;
			return;
		}

		const res = await loadUrlHandler(url).catch((err) => {
			toast.error(`${err}`);
			loading = false;
			return null;
		});

		if (res) {
			if (!successMessage) {
				successMessage = $i18n.t('Function imported successfully');
			}

			toast.success(successMessage);

			let func = res;
			func.id = func.id || func.name.replace(/\s+/g, '_').toLowerCase();

			const frontmatter = extractFrontmatter(res.content); // Ensure frontmatter is extracted

			if (frontmatter?.title) {
				func.name = frontmatter.title;
			}

			func.meta = {
				...(func.meta ?? {}),
				description: frontmatter?.description ?? func.name
			};

			onImport(func);
			show = false;
		}
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300, #cdcdcd); --px:1.25rem; --pt:1rem; --pb:0.5rem">
			<div style="--size:1.125rem; --weight:500; --as:center">{$i18n.t('Import')}</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1rem; --pb:0.75rem; --g-md:1rem; --dark-c:var(--color-gray-200, #e3e3e3)">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<form
					style="--d:flex; --fd:column; --w:100%"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div style="--px:0.25rem">
						<div style="--d:flex; --fd:column; --w:100%">
							<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">{$i18n.t('URL')}</div>

							<div style="--fx:1 1 0%">
								<input
									style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
	class="disabled:text-gray-500 dark:disabled:text-gray-500"
									type="url"
									bind:value={url}
									placeholder={$i18n.t('Enter the URL to import')}
									required
								/>

								<!-- $i18n.t('Enter the URL of the function to import') -->
							</div>
						</div>
					</div>

					<div style="--d:flex; --jc:flex-end; --pt:0.75rem; --size:0.875rem; --weight:500">
						<button
							style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900, #171717); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100, #ececec); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.25rem; --ai:center"
	class="{loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Import')}

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
