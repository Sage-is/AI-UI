<script lang="ts">
	import Fuse from 'fuse.js';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, knowledge } from '$lib/stores';
	import {
		getKnowledgeBases,
		deleteKnowledgeById,
		getKnowledgeBaseList
	} from '$lib/apis/knowledge';

	import { goto } from '$app/navigation';

	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import ItemMenu from './Knowledge/ItemMenu.svelte';
	import Badge from '../common/Badge.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import Spinner from '../common/Spinner.svelte';
	import { capitalizeFirstLetter } from '$lib/utils';
	import Tooltip from '../common/Tooltip.svelte';
	import XMark from '../icons/XMark.svelte';

	let loaded = false;

	let query = '';
	let selectedItem = null;
	let showDeleteConfirm = false;

	let fuse = null;

	let knowledgeBases = [];
	let filteredItems = [];

	$: if (knowledgeBases.length > 0) {
		// Added a check for non-empty array, good practice
		fuse = new Fuse(knowledgeBases, {
			keys: [
				'name',
				'description',
				'user.name', // Ensures Fuse looks into item.user.name
				'user.email' // Ensures Fuse looks into item.user.email
			],
			threshold: 0.0 // You might want to adjust this. Lower is more strict. Default is 0.6.
			// 0.0 is exact match.
		});
	} else {
		fuse = null; // Reset fuse if knowledgeBases is empty
	}

	$: if (fuse) {
		filteredItems = query
			? fuse.search(query).map((e) => {
					return e.item;
				})
			: knowledgeBases;
	}

	const deleteHandler = async (item) => {
		const res = await deleteKnowledgeById(localStorage.token, item.id).catch((e) => {
			toast.error(`${e}`);
		});

		if (res) {
			knowledgeBases = await getKnowledgeBaseList(localStorage.token);
			knowledge.set(await getKnowledgeBases(localStorage.token));
			toast.success($i18n.t('Knowledge deleted successfully.'));
		}
	};

	onMount(async () => {
		knowledgeBases = await getKnowledgeBaseList(localStorage.token);
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Knowledge')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		on:confirm={() => {
			deleteHandler(selectedItem);
		}}
	/>

	<div style="--d:flex; --fd:column; --g:0.25rem; --my:0.375rem">
		<div style="--d:flex; --jc:space-between; --ai:center">
			<div style="--d:flex; --as-md:center; --size:1.25rem; --weight:500; --px:0.125rem; --ai:center">
				{$i18n.t('Knowledge')}
				<div style="--d:flex; --as:center; --w:1px; --h:1.5rem; --mx:0.625rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850)" />
				<span style="--size:1.125rem; --weight:500; --c:var(--color-gray-500); --dark-c:var(--color-gray-300)"
					>{filteredItems.length}</span
				>
			</div>
		</div>

		<div style="--d:flex; --w:100%; --g:0.5rem">
			<div style="--d:flex; --fx:1 1 0%">
				<div style="--as:center; --ml:0.25rem; --mr:0.6rem">
					<Search className="size-3.5" />
				</div>
				<input
					style="--w:100%; --size:0.875rem; --py:0.25rem; --btrr:0.6rem; --bbrr:0.6rem; --oe:none; --bgc:transparent"
					bind:value={query}
					placeholder={$i18n.t('Search Knowledge')}
				/>
				{#if query}
					<div style="--as:center; --pl:0.375rem; --translatey:0.5px; --btlr:0.6rem; --bblr:0.6rem; --bgc:transparent">
						<button
							style="--p:0.125rem; --radius:9999px; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-900); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
							on:click={() => {
								query = '';
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					</div>
				{/if}
			</div>

			<div>
				<button
					style="--px:0.5rem; --py:0.5rem; --radius:0.6rem; --hvr-bgc:rgb(78 78 78 / 0.1); --hvr-dark-bgc:rgb(236 236 236 / 0.1); --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --size:0.875rem; --d:flex; --ai:center; --g:0.25rem"
					aria-label={$i18n.t('Create Knowledge')}
					on:click={() => {
						goto('/workshop/knowledge/create');
					}}
				>
					<Plus className="size-3.5" />
				</button>
			</div>
		</div>
	</div>

	<div style="--mb:1.25rem; --d:grid; --gtc:repeat(1, minmax(0, 1fr)); --gtc-lg:repeat(2, minmax(0, 1fr)); --gtc-xl:repeat(3, minmax(0, 1fr)); --g:0.5rem">
		{#each filteredItems as item}
			<button
				style="--d:flex; --g:1rem; --cur:pointer; --ta:left; --w:100%; --px:0.6rem; --py:0.5rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.6rem"
				on:click={() => {
					if (item?.meta?.document) {
						toast.error(
							$i18n.t(
								'Only collections can be edited, create a new knowledge base to edit/add documents.'
							)
						);
					} else {
						goto(`/workshop/knowledge/${item.id}`);
					}
				}}
			>
				<div style="--w:100%">
					<div style="--d:flex; --ai:center; --jc:space-between; --mt:-0.25rem">
						{#if item?.meta?.document}
							<Badge type="muted" content={$i18n.t('Document')} />
						{:else}
							<Badge type="success" content={$i18n.t('Collection')} />
						{/if}

						<div style="--d:flex; --as:center; --mr:-0.25rem; --translatey:0.25rem">
							<ItemMenu
								on:delete={() => {
									selectedItem = item;
									showDeleteConfirm = true;
								}}
							/>
						</div>
					</div>

					<div style="--as:center; --fx:1 1 0%; --px:0.25rem; --mb:0.25rem">
						<div style="--weight:600; --line-clamp:1; --h:fit-content">{item.name}</div>

						<div style="--size:0.6rem; --of:hidden; text-overflow:ellipsis; --line-clamp:1">
							{item.description}
						</div>

						<div style="--mt:0.6rem; --d:flex; --jc:space-between">
							<div style="--size:0.6rem; --c:var(--color-gray-500)">
								<Tooltip
									content={item?.user?.email ?? $i18n.t('Deleted User')}
									className="flex shrink-0"
									placement="top-start"
								>
									{$i18n.t('By {{name}}', {
										name: capitalizeFirstLetter(
											item?.user?.name ?? item?.user?.email ?? $i18n.t('Deleted User')
										)
									})}
								</Tooltip>
							</div>
							<div style="--size:0.6rem; --c:var(--color-gray-500); --line-clamp:1">
								{$i18n.t('Updated')}
								{dayjs(item.updated_at * 1000).fromNow()}
							</div>
						</div>
					</div>
				</div>
			</button>
		{/each}
	</div>

	<div style="--c:var(--color-gray-500); --size:0.6rem; --mt:0.25rem; --mb:0.5rem">
		ⓘ {$i18n.t("Use '#' in the prompt input to load and include your knowledge.")}
	</div>
{:else}
	<div style="--w:100%; --h:100%; --d:flex; --jc:center; --ai:center">
		<Spinner className="size-5" />
	</div>
{/if}
