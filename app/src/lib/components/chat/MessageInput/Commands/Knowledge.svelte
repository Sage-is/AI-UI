<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Fuse from 'fuse.js';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { tick, getContext, onMount, onDestroy } from 'svelte';
	import { removeLastWordFromString, isValidHttpUrl } from '$lib/utils';
	import { knowledge } from '$lib/stores';
	import { getNoteList, getNotes } from '$lib/apis/notes';

	const i18n = getContext('i18n');

	export let command = '';
	export let onSelect = (e) => {};

	let selectedIdx = 0;

	let items = [];
	let fuse = null;

	let filteredItems = [];
	$: if (fuse) {
		filteredItems = command.slice(1)
			? fuse.search(command).map((e) => {
					return e.item;
				})
			: items;
	}

	$: if (command) {
		selectedIdx = 0;
	}

	export const selectUp = () => {
		selectedIdx = Math.max(0, selectedIdx - 1);
	};

	export const selectDown = () => {
		selectedIdx = Math.min(selectedIdx + 1, filteredItems.length - 1);
	};

	let container;
	let adjustHeightDebounce;

	const adjustHeight = () => {
		if (container) {
			if (adjustHeightDebounce) {
				clearTimeout(adjustHeightDebounce);
			}

			adjustHeightDebounce = setTimeout(() => {
				if (!container) return;

				// Ensure the container is visible before adjusting height
				const rect = container.getBoundingClientRect();
				container.style.maxHeight = Math.max(Math.min(240, rect.bottom - 100), 100) + 'px';
			}, 100);
		}
	};

	const confirmSelect = async (type, data) => {
		onSelect({
			type: type,
			data: data
		});
	};

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};

	onMount(async () => {
		window.addEventListener('resize', adjustHeight);
		adjustHeight();

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

		let legacy_documents = $knowledge
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

		let collections = $knowledge
			.filter((item) => !item?.meta?.document)
			.map((item) => ({
				...item,
				type: 'collection'
			}));
		let collection_files =
			$knowledge.length > 0
				? [
						...$knowledge
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
								knowledge: true, // DO NOT REMOVE, USED TO INDICATE KNOWLEDGE BASE FILE
								type: 'file'
							}))
					]
				: [];

		items = [
			...notes,
			...collections,
			...collection_files,
			...legacy_collections,
			...legacy_documents
		].map((item) => {
			return {
				...item,
				...(item?.legacy || item?.meta?.legacy || item?.meta?.document ? { legacy: true } : {})
			};
		});

		fuse = new Fuse(items, {
			keys: ['name', 'description']
		});
	});

	onDestroy(() => {
		window.removeEventListener('resize', adjustHeight);
	});
</script>

{#if filteredItems.length > 0 || command?.substring(1).startsWith('http')}
	<div
		id="commands-container"
		style="--px:0.5rem; --mb:0.5rem; --ta:left; --w:100%; --pos:absolute; --bottom:0; --left:0; --right:0; --z:10"
	>
		<div style="--d:flex; --w:100%; --radius:0.75rem; --b:1px solid; --bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-850, #262626)">
			<div style="--d:flex; --fd:column; --w:100%; --radius:0.75rem; --bgc:#fff; --dark-bgc:var(--color-gray-900, #171717); --dark-c:var(--color-gray-100, #ececec)">
				<div
					style="--m:0.25rem; --ofy:auto; --p:0.25rem; --btrr:0.75rem; --bbrr:0.75rem; --g:0.125rem; --maxh:15rem"
	class="scrollbar-hidden"
					id="command-options-container"
					bind:this={container}
				>
					{#each filteredItems as item, idx}
						<button
							style="--px:0.75rem; --py:0.375rem; --radius:0.75rem; --w:100%; --ta:left; --d:flex; --jc:space-between; --ai:center"
	class="{idx ===
							selectedIdx
								? ' bg-gray-50 dark:bg-gray-850 dark:text-gray-100 selected-command-option-button'
								: ''}"
							type="button"
							on:click={() => {
								console.log(item);
								confirmSelect('knowledge', item);
							}}
							on:mousemove={() => {
								selectedIdx = idx;
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
						</button>

						<!-- <div slot="content" style="--pl:0.5rem; --pt:0.25rem; --d:flex; --fd:column; --g:0.125rem">
								{#if !item.legacy && (item?.files ?? []).length > 0}
									{#each item?.files ?? [] as file, fileIdx}
										<button
											style="--px:0.75rem; --py:0.375rem; --radius:0.75rem; --w:100%; --ta:left; --d:flex; --jc:space-between; --ai:center; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-850, #262626); --hvr-dark-c:var(--color-gray-100, #ececec)"
	class="selected-command-option-button"
											type="button"
											on:click={() => {
												console.log(file);
											}}
											on:mousemove={() => {
												selectedIdx = idx;
											}}
										>
											<div>
												<div
													style="--weight:500; --c:#000; --dark-c:var(--color-gray-100, #ececec); --d:flex; --ai:center; --g:0.25rem"
												>
													<div
														style="--bgc:rgb(155 155 155 / 0.2); --c:var(--color-gray-700, #4e4e4e); --dark-c:var(--color-gray-200, #e3e3e3); --radius:0.125rem; --tt:uppercase; --size:0.75rem; --weight:700; --px:0.25rem; --fs:0"
													>
														File
													</div>

													<div style="--line-clamp:1">
														{file?.meta?.name}
													</div>
												</div>

												<div style="--size:0.75rem; --c:var(--color-gray-600, #676767); --dark-c:var(--color-gray-100, #ececec); --line-clamp:1">
													{$i18n.t('Updated')}
													{dayjs(file.updated_at * 1000).fromNow()}
												</div>
											</div>
										</button>
									{/each}
								{:else}
									<div style="--c:var(--color-gray-500, #9b9b9b); --size:0.75rem; --mt:0.25rem; --mb:0.5rem">
										{$i18n.t('File not found.')}
									</div>
								{/if}
							</div> -->
					{/each}

					{#if command.substring(1).startsWith('https://www.youtube.com') || command
							.substring(1)
							.startsWith('https://youtu.be')}
						<button
							style="--px:0.75rem; --py:0.375rem; --radius:0.75rem; --w:100%; --ta:left; --bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-850, #262626); --dark-c:var(--color-gray-100, #ececec)"
	class="selected-command-option-button"
							type="button"
							on:click={() => {
								if (isValidHttpUrl(command.substring(1))) {
									confirmSelect('youtube', command.substring(1));
								} else {
									toast.error(
										$i18n.t(
											'Oops! Looks like the URL is invalid. Please double-check and try again.'
										)
									);
								}
							}}
						>
							<div style="--weight:500; --c:#000; --dark-c:var(--color-gray-100, #ececec); --line-clamp:1">
								{command.substring(1)}
							</div>

							<div style="--size:0.75rem; --c:var(--color-gray-600, #676767); --line-clamp:1">{$i18n.t('Youtube')}</div>
						</button>
					{:else if command.substring(1).startsWith('http')}
						<button
							style="--px:0.75rem; --py:0.375rem; --radius:0.75rem; --w:100%; --ta:left; --bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-850, #262626); --dark-c:var(--color-gray-100, #ececec)"
	class="selected-command-option-button"
							type="button"
							on:click={() => {
								if (isValidHttpUrl(command.substring(1))) {
									confirmSelect('web', command.substring(1));
								} else {
									toast.error(
										$i18n.t(
											'Oops! Looks like the URL is invalid. Please double-check and try again.'
										)
									);
								}
							}}
						>
							<div style="--weight:500; --c:#000; --dark-c:var(--color-gray-100, #ececec); --line-clamp:1">
								{command}
							</div>

							<div style="--size:0.75rem; --c:var(--color-gray-600, #676767); --line-clamp:1">{$i18n.t('Web')}</div>
						</button>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}
