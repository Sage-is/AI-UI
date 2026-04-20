<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	import { getGroups } from '$lib/apis/groups';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
				import Badge from '$lib/components/common/Badge.svelte';

	export let onChange: Function = () => {};

	export let accessRoles = ['read'];
	export let accessControl = {};

	export let allowPublic = true;

	let selectedGroupId = '';
	let groups = [];

	$: if (!allowPublic && accessControl === null) {
		accessControl = {
			read: {
				group_ids: [],
				user_ids: []
			},
			write: {
				group_ids: [],
				user_ids: []
			}
		};
		onChange(accessControl);
	}

	onMount(async () => {
		groups = await getGroups(localStorage.token);

		if (accessControl === null) {
			if (allowPublic) {
				accessControl = null;
			} else {
				accessControl = {
					read: {
						group_ids: [],
						user_ids: []
					},
					write: {
						group_ids: [],
						user_ids: []
					}
				};
				onChange(accessControl);
			}
		} else {
			accessControl = {
				read: {
					group_ids: accessControl?.read?.group_ids ?? [],
					user_ids: accessControl?.read?.user_ids ?? []
				},
				write: {
					group_ids: accessControl?.write?.group_ids ?? [],
					user_ids: accessControl?.write?.user_ids ?? []
				}
			};
		}
	});

	$: onChange(accessControl);

	$: if (selectedGroupId) {
		onSelectGroup();
	}

	const onSelectGroup = () => {
		if (selectedGroupId !== '') {
			accessControl.read.group_ids = [...accessControl.read.group_ids, selectedGroupId];

			selectedGroupId = '';
		}
	};
</script>

<div style="--radius:0.5rem; --d:flex; --fd:column; --g:0.5rem">
	<div class="">
		<div style="--size:0.8rem; --weight:600; --mb:0.2rem">{$i18n.t('Visibility')}</div>

		<div style="--d:flex; --g:0.625rem; --ai:center; --mb:0.2rem">
			<div>
				<div style="--p:0.5rem; --bgc:rgb(0 0 0 / 0.05); --dark-bgc:rgb(255 255 255 / 0.05); --radius:9999px">
					{#if accessControl !== null}
						<Icon name="lock-open" className="size-[1.2rem]" />
					{:else}
						<Icon name="rocket" className="size-[1.2rem]" />
					{/if}
				</div>
			</div>

			<div>
				<select
					id="models"
					style="--oe:none; --bgc:transparent; --size:0.8rem; --weight:500; --radius:0.5rem; --d:block; --w:fit-content; --pr:2.5rem; --maxw:100%"
	class="placeholder-gray-400"
					value={accessControl !== null ? 'private' : 'public'}
					on:change={(e) => {
						if (e.target.value === 'public') {
							accessControl = null;
						} else {
							accessControl = {
								read: {
									group_ids: [],
									user_ids: []
								},
								write: {
									group_ids: [],
									user_ids: []
								}
							};
						}
					}}
				>
					<option style="--c:var(--color-gray-700)" value="private" selected>{$i18n.t('Private')}</option>
					{#if allowPublic}
						<option style="--c:var(--color-gray-700)" value="public" selected>{$i18n.t('Public')}</option>
					{/if}
				</select>

				<div style="--size:0.6rem; --c:var(--color-gray-400); --weight:500">
					{#if accessControl !== null}
						{$i18n.t('Only select users and groups with permission can access')}
					{:else}
						{$i18n.t('Accessible to all users')}
					{/if}
				</div>
			</div>
		</div>
	</div>
	{#if accessControl !== null}
		{@const accessGroups = groups.filter((group) =>
			accessControl.read.group_ids.includes(group.id)
		)}
		<div>
			<div class="">
				<div style="--d:flex; --jc:space-between; --mb:0.4rem">
					<div style="--size:0.8rem; --weight:600">
						{$i18n.t('Groups')}
					</div>
				</div>

				<div style="--mb:0.2rem">
					<div style="--d:flex; --w:100%">
						<div style="--d:flex; --fx:1 1 0%; --ai:center">
							<div style="--w:100%; --px:0.125rem">
								<select
									style="--oe:none; --bgc:transparent; --size:0.8rem; --radius:0.5rem; --d:block; --w:100%; --pr:2.5rem; --maxw:100%"
	class="{selectedGroupId ? '' : 'text-gray-500'} dark:placeholder-gray-500"
									bind:value={selectedGroupId}
								>
									<option style="--c:var(--color-gray-700)" value="" disabled selected
										>{$i18n.t('Select a group')}</option
									>
									{#each groups.filter((group) => !accessControl.read.group_ids.includes(group.id)) as group}
										<option style="--c:var(--color-gray-700)" value={group.id}>{group.name}</option>
									{/each}
								</select>
							</div>
							<!-- <div>
								<Tooltip content={$i18n.t('Add Group')}>
									<button
										style="--p:0.2rem; --radius:0.6rem; --bgc:transparent; --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-bgc:rgb(0 0 0 / 0.05); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --size:0.8rem; --d:flex; --ai:center; --g:0.2rem"
										type="button"
										on:click={() => {}}
									>
										<Icon name="plus" strokeWidth="2" className="size-3.5" />
									</button>
								</Tooltip>
							</div> -->
						</div>
					</div>
				</div>

				<hr style="--bc:var(--color-gray-100); --dark-bc:rgb(78 78 78 / 0.1); --mt:0.4rem; --mb:0.625rem; --w:100%" />

				<div style="--d:flex; --fd:column; --g:0.5rem; --mb:0.2rem; --px:0.125rem">
					{#if accessGroups.length > 0}
						{#each accessGroups as group}
							<div style="--d:flex; --ai:center; --g:0.6rem; --jc:space-between; --size:0.6rem; --w:100%; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)">
								<div style="--d:flex; --ai:center; --g:0.4rem; --w:100%; --weight:500">
									<div>
										<Icon name="user-circle-solid" className="size-4" />
									</div>

									<div>
										{group.name}
									</div>
								</div>

								<div style="--w:100%; --d:flex; --jc:flex-end; --ai:center; --g:0.125rem">
									<button
										class=""
										type="button"
										on:click={() => {
											if (accessRoles.includes('write')) {
												if (accessControl.write.group_ids.includes(group.id)) {
													accessControl.write.group_ids = accessControl.write.group_ids.filter(
														(group_id) => group_id !== group.id
													);
												} else {
													accessControl.write.group_ids = [
														...accessControl.write.group_ids,
														group.id
													];
												}
											}
										}}
									>
										{#if accessControl.write.group_ids.includes(group.id)}
											<Badge type={'success'} content={$i18n.t('Write')} />
										{:else}
											<Badge type={'info'} content={$i18n.t('Read')} />
										{/if}
									</button>

									<button
										style="--radius:9999px; --p:0.2rem; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
										type="button"
										on:click={() => {
											accessControl.read.group_ids = accessControl.read.group_ids.filter(
												(id) => id !== group.id
											);
										}}
									>
										<Icon name="x-mark" className="size-3.5" strokeWidth="2" />
									</button>
								</div>
							</div>
						{/each}
					{:else}
						<div style="--d:flex; --ai:center; --jc:center">
							<div style="--c:var(--color-gray-500); --size:0.6rem; --ta:center; --py:0.5rem; --px:2.5rem">
								{$i18n.t('No groups with access, add a group to grant access')}
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
