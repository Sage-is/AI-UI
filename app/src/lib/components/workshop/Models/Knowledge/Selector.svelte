<script lang="ts">
	import Fuse from 'fuse.js';

	import { DropdownMenu } from 'bits-ui';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { flyAndScale } from '$lib/utils/transitions';
	import { knowledge } from '$lib/stores';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import { getNoteList } from '$lib/apis/notes';
	import dayjs from 'dayjs';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let onClose: Function = () => {};

	export let knowledgeItems = [];

	let query = '';

	let items = [];
	let filteredItems = [];

	let fuse = null;
	$: if (fuse) {
		filteredItems = query
			? fuse.search(query).map((e) => {
					return e.item;
				})
			: items;
	}

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};

	onMount(async () => {
		let notes = await getNoteList(localStorage.token).catch(() => {
			return [];
		});

		notes = notes.map((note) => {
			return {
				...note,
				type: 'note',
				name: note.title,
				description: dayjs(note.updated_at / 1000000).fromNow()
			};
		});

		let legacy_documents = knowledgeItems
			.filter((item) => item?.meta?.document)
			.map((item) => ({
				...item,
				type: 'file'
			}));

		let legacy_collections =
			legacy_documents.length > 0
				? [
						{
							name: 'All Documents',
							legacy: true,
							type: 'collection',
							description: 'Deprecated (legacy collection), please create a new knowledge base.',
							title: $i18n.t('All Documents'),
							collection_names: legacy_documents.map((item) => item.id)
						},

						...legacy_documents
							.reduce((a, item) => {
								return [...new Set([...a, ...(item?.meta?.tags ?? []).map((tag) => tag.name)])];
							}, [])
							.map((tag) => ({
								name: tag,
								legacy: true,
								type: 'collection',
								description: 'Deprecated (legacy collection), please create a new knowledge base.',
								collection_names: legacy_documents
									.filter((item) => (item?.meta?.tags ?? []).map((tag) => tag.name).includes(tag))
									.map((item) => item.id)
							}))
					]
				: [];

		let collections = knowledgeItems
			.filter((item) => !item?.meta?.document)
			.map((item) => ({
				...item,
				type: 'collection'
			}));
		let collection_files =
			knowledgeItems.length > 0
				? [
						...knowledgeItems
							.reduce((a, item) => {
								return [
									...new Set([
										...a,
										...(item?.files ?? []).map((file) => ({
											...file,
											collection: { name: item.name, description: item.description } // DO NOT REMOVE, USED IN FILE DESCRIPTION/ATTACHMENT
										}))
									])
								];
							}, [])
							.map((file) => ({
								...file,
								name: file?.meta?.name,
								description: `${file?.collection?.name} - ${file?.collection?.description}`,
								type: 'file'
							}))
					]
				: [];

		items = [...notes, ...collections, ...legacy_collections].map((item) => {
			return {
				...item,
				...(item?.legacy || item?.meta?.legacy || item?.meta?.document ? { legacy: true } : {})
			};
		});

		fuse = new Fuse(items, {
			keys: ['name', 'description']
		});
	});
</script>

<Dropdown
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
			query = '';
		}
	}}
>
	<slot />

	<div slot="content">
		<DropdownMenu.Content
			style="--w:100%; --maxw:24rem; --radius:0.75rem; --px:0.25rem; --py:0.375rem; --b:1px solid; --bc:rgb(205 205 205 / 0.3); --dark-bc:rgb(78 78 78 / 0.5); --z:99999999; --bgc:#fff; --dark-bgc:var(--color-gray-850, #262626); --dark-c:#fff; --shadow:4"
			sideOffset={8}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			<div style="--d:flex; --w:100%; --g:0.5rem; --py:0.125rem; --px:0.5rem; --pb:0.5rem">
				<div style="--d:flex; --fx:1 1 0%">
					<div style="--as:center; --ml:0.25rem; --mr:0.75rem">
						<Search />
					</div>
					<input
						style="--w:100%; --size:0.875rem; --pr:1rem; --py:0.25rem; --btrr:0.75rem; --bbrr:0.75rem; --oe:none; --bgc:transparent"
						bind:value={query}
						placeholder={$i18n.t('Search Knowledge')}
					/>
				</div>
			</div>

			<div style="--maxh:14rem; --ofy:scroll">
				{#if filteredItems.length === 0}
					<div style="--ta:center; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b); --dark-c:var(--color-gray-400, #b4b4b4); --py:1rem">
						{$i18n.t('No knowledge found')}
					</div>
				{:else}
					{#each filteredItems as item}
						<DropdownMenu.Item
							style="--d:flex; --g:0.625rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem"
							on:click={() => {
								dispatch('select', item);
							}}
						>
							<div>
								<div style="--weight:500; --c:#000; --dark-c:var(--color-gray-100, #ececec); --d:flex; --ai:center; --g:0.25rem">
									{#if item.legacy}
										<div
											style="--bgc:rgb(155 155 155 / 0.2); --c:var(--color-gray-700, #4e4e4e); --dark-c:var(--color-gray-200, #e3e3e3); --radius:0.125rem; --tt:uppercase; --size:0.75rem; --weight:700; --px:0.25rem; --fs:0"
										>
											Legacy
										</div>
									{:else if item?.meta?.document}
										<div
											style="--bgc:rgb(155 155 155 / 0.2); --c:var(--color-gray-700, #4e4e4e); --dark-c:var(--color-gray-200, #e3e3e3); --radius:0.125rem; --tt:uppercase; --size:0.75rem; --weight:700; --px:0.25rem; --fs:0"
										>
											Document
										</div>
									{:else if item?.type === 'file'}
										<div
											style="--bgc:rgb(155 155 155 / 0.2); --c:var(--color-gray-700, #4e4e4e); --dark-c:var(--color-gray-200, #e3e3e3); --radius:0.125rem; --tt:uppercase; --size:0.75rem; --weight:700; --px:0.25rem; --fs:0"
										>
											File
										</div>
									{:else if item?.type === 'note'}
										<div
											style="--bgc:rgb(59 130 246 / 0.2); --c:#1d4ed8; --dark-c:#bfdbfe; --radius:0.125rem; --tt:uppercase; --size:0.75rem; --weight:700; --px:0.25rem; --fs:0"
										>
											Note
										</div>
									{:else}
										<div
											style="--bgc:rgb(34 197 94 / 0.2); --c:#15803d; --dark-c:#bbf7d0; --radius:0.125rem; --tt:uppercase; --size:0.75rem; --weight:700; --px:0.25rem; --fs:0"
										>
											Collection
										</div>
									{/if}

									<div style="--line-clamp:1">
										{decodeString(item?.name)}
									</div>
								</div>

								<div style="--size:0.75rem; --c:var(--color-gray-600, #676767); --dark-c:var(--color-gray-100, #ececec); --line-clamp:1">
									{item?.description}
								</div>
							</div>
						</DropdownMenu.Item>
					{/each}
				{/if}
			</div>
		</DropdownMenu.Content>
	</div>
</Dropdown>
