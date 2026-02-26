<script lang="ts">
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');

	import { getGroups } from '$lib/apis/groups';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import UserCircleSolid from '$lib/components/icons/UserCircleSolid.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
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
		<div style="--size:0.875rem; --weight:600; --mb:0.25rem">{$i18n.t('Visibility')}</div>

		<div style="--d:flex; --g:0.625rem; --ai:center; --mb:0.25rem">
			<div>
				<div style="--p:0.5rem; --bgc:rgb(0 0 0 / 0.05); --dark-bgc:rgb(255 255 255 / 0.05); --radius:9999px">
					{#if accessControl !== null}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							style="--w:1.25rem; --h:1.25rem"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
							/>
						</svg>
					{:else}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							style="--w:1.25rem; --h:1.25rem"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M6.115 5.19l.319 1.913A6 6 0 008.11 10.36L9.75 12l-.387.775c-.217.433-.132.956.21 1.298l1.348 1.348c.21.21.329.497.329.795v1.089c0 .426.24.815.622 1.006l.153.076c.433.217.956.132 1.298-.21l.723-.723a8.7 8.7 0 002.288-4.042 1.087 1.087 0 00-.358-1.099l-1.33-1.108c-.251-.21-.582-.299-.905-.245l-1.17.195a1.125 1.125 0 01-.98-.314l-.295-.295a1.125 1.125 0 010-1.591l.13-.132a1.125 1.125 0 011.3-.21l.603.302a.809.809 0 001.086-1.086L14.25 7.5l1.256-.837a4.5 4.5 0 001.528-1.732l.146-.292M6.115 5.19A9 9 0 1017.18 4.64M6.115 5.19A8.965 8.965 0 0112 3c1.929 0 3.716.607 5.18 1.64"
							/>
						</svg>
					{/if}
				</div>
			</div>

			<div>
				<select
					id="models"
					style="--oe:none; --bgc:transparent; --size:0.875rem; --weight:500; --radius:0.5rem; --d:block; --w:fit-content; --pr:2.5rem; --maxw:100%"
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

				<div style="--size:0.75rem; --c:var(--color-gray-400); --weight:500">
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
				<div style="--d:flex; --jc:space-between; --mb:0.375rem">
					<div style="--size:0.875rem; --weight:600">
						{$i18n.t('Groups')}
					</div>
				</div>

				<div style="--mb:0.25rem">
					<div style="--d:flex; --w:100%">
						<div style="--d:flex; --fx:1 1 0%; --ai:center">
							<div style="--w:100%; --px:0.125rem">
								<select
									style="--oe:none; --bgc:transparent; --size:0.875rem; --radius:0.5rem; --d:block; --w:100%; --pr:2.5rem; --maxw:100%"
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
										style="--p:0.25rem; --radius:0.75rem; --bgc:transparent; --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-bgc:rgb(0 0 0 / 0.05); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --size:0.875rem; --d:flex; --ai:center; --g:0.25rem"
										type="button"
										on:click={() => {}}
									>
										<Plus className="size-3.5" />
									</button>
								</Tooltip>
							</div> -->
						</div>
					</div>
				</div>

				<hr style="--bc:var(--color-gray-100); --dark-bc:rgb(78 78 78 / 0.1); --mt:0.375rem; --mb:0.625rem; --w:100%" />

				<div style="--d:flex; --fd:column; --g:0.5rem; --mb:0.25rem; --px:0.125rem">
					{#if accessGroups.length > 0}
						{#each accessGroups as group}
							<div style="--d:flex; --ai:center; --g:0.75rem; --jc:space-between; --size:0.75rem; --w:100%; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)">
								<div style="--d:flex; --ai:center; --g:0.375rem; --w:100%; --weight:500">
									<div>
										<UserCircleSolid className="size-4" />
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
										style="--radius:9999px; --p:0.25rem; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
										type="button"
										on:click={() => {
											accessControl.read.group_ids = accessControl.read.group_ids.filter(
												(id) => id !== group.id
											);
										}}
									>
										<XMark />
									</button>
								</div>
							</div>
						{/each}
					{:else}
						<div style="--d:flex; --ai:center; --jc:center">
							<div style="--c:var(--color-gray-500); --size:0.75rem; --ta:center; --py:0.5rem; --px:2.5rem">
								{$i18n.t('No groups with access, add a group to grant access')}
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
