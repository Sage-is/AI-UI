<script lang="ts">
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
			import Sortable from 'sortablejs';
	import { getContext } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';
	const i18n = getContext('i18n');

	export let banners = [];

	let sortable = null;
	let bannerListElement = null;

	const positionChangeHandler = () => {
		const bannerIdOrder = Array.from(bannerListElement.children).map((child) =>
			child.id.replace('banner-item-', '')
		);

		// Sort the banners array based on the new order
		banners = bannerIdOrder.map((id) => {
			const index = banners.findIndex((banner) => banner.id === id);
			return banners[index];
		});
	};

	const classNames: Record<string, string> = {
		info: 'bg-blue-500/20 text-blue-700 dark:text-blue-200 ',
		success: 'bg-green-500/20 text-green-700 dark:text-green-200',
		warning: 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-200',
		error: 'bg-red-500/20 text-red-700 dark:text-red-200'
	};

	$: if (banners) {
		init();
	}

	const init = () => {
		if (sortable) {
			sortable.destroy();
		}

		if (bannerListElement) {
			sortable = Sortable.create(bannerListElement, {
				animation: 150,
				handle: '.item-handle',
				onUpdate: async (event) => {
					positionChangeHandler();
				}
			});
		}
	};
</script>

<div style="--d:flex; --fd:column; --g:0.6rem"
	class="{banners?.length > 0 ? 'mt-2' : ''}" bind:this={bannerListElement}>
	{#each banners as banner, bannerIdx (banner.id)}
		<div style="--d:flex; --jc:space-between; --ai:flex-start; --ml:-0.2rem" id="banner-item-{banner.id}">
			<Icon name="ellipsis-vertical" className="size-4 cursor-move item-handle" />

			<div style="--d:flex; --fd:row; --fx:1 1 0%; --g:0.5rem; --ai:flex-start">
				<select
					style="--w:fit-content; --tt:capitalize; --radius:0.6rem; --size:0.6rem; --bgc:transparent; --oe:none; --pl:0.2rem; --pr:1.2rem"
					bind:value={banner.type}
					required
				>
					{#if banner.type == ''}
						<option value="" selected disabled style="--c:var(--color-gray-900)">{$i18n.t('Type')}</option>
					{/if}
					<option value="info" style="--c:var(--color-gray-900)">{$i18n.t('Info')}</option>
					<option value="warning" style="--c:var(--color-gray-900)">{$i18n.t('Warning')}</option>
					<option value="error" style="--c:var(--color-gray-900)">{$i18n.t('Error')}</option>
					<option value="success" style="--c:var(--color-gray-900)">{$i18n.t('Success')}</option>
				</select>

				<Textarea
					className="mr-2 text-xs w-full bg-transparent outline-hidden resize-none"
					placeholder={$i18n.t('Content')}
					bind:value={banner.content}
					maxSize={100}
				/>

				<div style="--pos:relative; --left:-0.5rem">
					<Tooltip content={$i18n.t('Remember Dismissal')} className="flex h-fit items-center">
						<Switch bind:state={banner.dismissible} />
					</Tooltip>
				</div>
			</div>

			<button
				style="--pr:0.6rem"
				type="button"
				on:click={() => {
					banners.splice(bannerIdx, 1);
					banners = banners;
				}}
			>
				<Icon name="x-mark" strokeWidth="2" className={'size-4'} />
			</button>
		</div>
	{/each}
</div>
