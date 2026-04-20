<script>
	import { goto } from '$app/navigation';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { createNewKnowledge, getKnowledgeBases } from '$lib/apis/knowledge';
	import { toast } from 'svelte-sonner';
	import { knowledge, user } from '$lib/stores';
	import AccessControl from '../common/AccessControl.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let loading = false;

	let name = '';
	let description = '';
	let accessControl = {};

	const submitHandler = async () => {
		loading = true;

		if (name.trim() === '' || description.trim() === '') {
			toast.error($i18n.t('Please fill in all fields.'));
			name = '';
			description = '';
			loading = false;
			return;
		}

		const res = await createNewKnowledge(
			localStorage.token,
			name,
			description,
			accessControl
		).catch((e) => {
			toast.error(`${e}`);
		});

		if (res) {
			toast.success($i18n.t('Knowledge created successfully.'));
			knowledge.set(await getKnowledgeBases(localStorage.token));
			goto(`/workshop/knowledge/${res.id}`);
		}

		loading = false;
	};
</script>

<div style="--w:100%; --maxh:100%">
	<button
		style="--d:flex; --g:0.2rem"
		on:click={() => {
			goto('/workshop/knowledge');
		}}
	>
		<div style="--as:center">
			<Icon name="arrow-left-fill-20" className="size-4" />
		</div>
		<div style="--as:center; --weight:500; --size:0.8rem">{$i18n.t('Back')}</div>
	</button>

	<form
		style="--d:flex; --fd:column; --maxw:32rem; --mx:auto; --mt:2.5rem; --mb:2.5rem"
		on:submit|preventDefault={() => {
			submitHandler();
		}}
	>
		<div style="--w:100%; --d:flex; --fd:column; --jc:center">
			<div style="--size:1.5rem; --weight:500; --mb:0.625rem"
	class="font-primary">
				{$i18n.t('Create a knowledge base')}
			</div>

			<div style="--w:100%; --d:flex; --fd:column; --g:0.625rem">
				<div style="--w:100%">
					<div style="--size:0.8rem; --mb:0.5rem">{$i18n.t('What are you working on?')}</div>

					<div style="--w:100%; --mt:0.2rem">
						<input
							style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
							type="text"
							bind:value={name}
							placeholder={$i18n.t('Name your knowledge base')}
							required
						/>
					</div>
				</div>

				<div>
					<div style="--size:0.8rem; --mb:0.5rem">{$i18n.t('What are you trying to achieve?')}</div>

					<div style="--w:100%; --mt:0.2rem">
						<textarea
							style="--w:100%; resize:none; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
							rows="4"
							bind:value={description}
							placeholder={$i18n.t('Describe your knowledge base and objectives')}
							required
						/>
					</div>
				</div>
			</div>
		</div>

		<div style="--mt:0.5rem">
			<div style="--px:0.6rem; --py:0.5rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-950); --radius:0.5rem">
				<AccessControl
					bind:accessControl
					accessRoles={['read', 'write']}
					allowPublic={$user?.permissions?.sharing?.public_knowledge || $user?.role === 'admin'}
				/>
			</div>
		</div>

		<div style="--d:flex; --jc:flex-end; --mt:0.5rem">
			<div>
				<button
					style="--size:0.8rem; --px:1rem; --py:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem; --d:flex"
	class="{loading
						? ' cursor-not-allowed bg-gray-100 dark:bg-gray-800'
						: ' bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800'}"
					type="submit"
					disabled={loading}
				>
					<div style="--as:center; --weight:500">{$i18n.t('Create Knowledge')}</div>

					{#if loading}
						<div style="--ml:0.4rem; --as:center">
							<Spinner />
						</div>
					{/if}
				</button>
			</div>
		</div>
	</form>
</div>
