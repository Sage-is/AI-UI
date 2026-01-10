<script>
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';

	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { page } from '$app/stores';
	import { config, models, settings } from '$lib/stores';

	import { getModelById, updateModelById } from '$lib/apis/models';

	import { getModels } from '$lib/apis';
	import ModelEditorWithChat from '$lib/components/workshop/Models/ModelEditorWithChat.svelte';

	let model = null;

	onMount(async () => {
		const _id = $page.url.searchParams.get('id');
		if (_id) {
			model = await getModelById(localStorage.token, _id).catch((e) => {
				return null;
			});

			if (!model) {
				goto('/workshop/models');
			}
		} else {
			goto('/workshop/models');
		}
	});

	const onSubmit = async (modelInfo) => {
		const res = await updateModelById(localStorage.token, modelInfo.id, modelInfo);

		if (res) {
			// Update models store but stay on the page for continued testing
			await models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
			toast.success($i18n.t('Model updated successfully! You can continue testing in the chat.'));
			
			// Update the model data to reflect the updated model
			model = res;
			
			// Don't navigate away - stay for testing
			// await goto('/workshop/models');
		}
	};
</script>

{#if model}
	<ModelEditorWithChat edit={true} {model} {onSubmit} />
{/if}
