<script>
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	import { deleteGroupById, updateGroupById } from '$lib/apis/groups';

				import GroupModal from './EditGroupModal.svelte';

	export let users = [];
	export let group = {
		name: 'Admins',
		user_ids: [1, 2, 3]
	};

	export let setGroups = () => {};

	let showEdit = false;

	const updateHandler = async (_group) => {
		const res = await updateGroupById(localStorage.token, group.id, _group).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Group updated successfully'));
			setGroups();
		}
	};

	const deleteHandler = async () => {
		const res = await deleteGroupById(localStorage.token, group.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Group deleted successfully'));
			setGroups();
		}
	};
</script>

<GroupModal
	bind:show={showEdit}
	edit
	{users}
	{group}
	onSubmit={updateHandler}
	onDelete={deleteHandler}
/>

<button
	style="--d:flex; --ai:center; --g:0.6rem; --jc:space-between; --px:0.2rem; --size:0.6rem; --w:100%; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	on:click={() => {
		showEdit = true;
	}}
>
	<div style="--d:flex; --ai:center; --g:0.4rem; --w:100%; --weight:500; --fx:1 1 0%">
		<div>
			<Icon name="user-circle-solid" className="size-4" />
		</div>
		<div style="--line-clamp:1">
			{group.name}
		</div>
	</div>

	<div style="--d:flex; --ai:center; --g:0.4rem; --w:fit-content; --weight:500; --ta:right; --jc:flex-end">
		{group.user_ids.length}

		<div>
			<Icon name="user" className="size-3.5" />
		</div>

		<div style="--radius:0.5rem; --p:0.2rem; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)">
			<Icon name="pencil" className="size-3.5" />
		</div>
	</div>
</button>
