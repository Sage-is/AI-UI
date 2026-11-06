<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { models } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getBranding, type Branding } from '$lib/apis/configs';

	import { onMount, onDestroy, tick, getContext } from 'svelte';
	import { createNewModel, getModelById } from '$lib/apis/models';
	import { loadModels } from '$lib/apis';
	import { receiveFromHub } from '$lib/utils/community';

	import ModelEditorWithChat from '$lib/components/workshop/Models/ModelEditorWithChat.svelte';

	const i18n = getContext('i18n');

	let branding: Branding | null = null;
	let stopHub = () => {};
	onDestroy(() => stopHub());

	const onSubmit = async (modelInfo) => {
		if ($models.find((m) => m.id === modelInfo.id)) {
			toast.error(
				`Error: A model with the ID '${modelInfo.id}' already exists. Please select a different ID to proceed.`
			);
			return;
		}

		if (modelInfo.id === '') {
			toast.error('Error: Model ID cannot be empty. Please enter a valid ID to proceed.');
			return;
		}

		if (modelInfo) {
			const res = await createNewModel(localStorage.token, {
				...modelInfo,
				meta: {
					...modelInfo.meta,
					profile_image_url:
						modelInfo.meta.profile_image_url ?? branding?.logo_url ?? `${WEBUI_BASE_URL}/static/icons/favicon.png`,
					suggestion_prompts: modelInfo.meta.suggestion_prompts
						? modelInfo.meta.suggestion_prompts.filter((prompt) => prompt.content !== '')
						: null
				},
				params: { ...modelInfo.params }
			}).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				// Update models store
				await models.set(await loadModels());
				toast.success($i18n.t('Model created successfully!'));

				// Redirect to edit page to continue working on the model
				await goto(`/workshop/models/edit?id=${encodeURIComponent(res.id)}`);
			}
		}
	};

	let model = null;

	onMount(async () => {
		branding = await getBranding();

		stopHub = receiveFromHub((data) => {
			model = data?.info ?? data;
		});

		if (sessionStorage.model) {
			model = JSON.parse(sessionStorage.model);
			sessionStorage.removeItem('model');
		}
	});
</script>

{#key model}
	<ModelEditorWithChat {model} {onSubmit} />
{/key}
