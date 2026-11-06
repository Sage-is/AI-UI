<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { prompts } from '$lib/stores';
	import { onMount, onDestroy, tick, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { createNewPrompt, getPrompts } from '$lib/apis/prompts';
	import { receiveFromHub } from '$lib/utils/community';
	import PromptEditor from '$lib/components/workshop/Prompts/PromptEditor.svelte';

	let stopHub = () => {};
	onDestroy(() => stopHub());

	let prompt: {
		title: string;
		command: string;
		content: string;
		access_control: any | null;
	} | null = null;

	let clone = false;

	const onSubmit = async (_prompt) => {
		const res = await createNewPrompt(localStorage.token, _prompt).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Prompt created successfully'));

			await prompts.set(await getPrompts(localStorage.token));
			await goto('/workshop/prompts');
		}
	};

	onMount(async () => {
		stopHub = receiveFromHub((_prompt) => {
			clone = true;
			prompt = {
				title: _prompt.title,
				command: _prompt.command,
				content: _prompt.content,
				access_control: null
			};
		});

		if (sessionStorage.prompt) {
			const _prompt = JSON.parse(sessionStorage.prompt);
			sessionStorage.removeItem('prompt');

			console.log('Received prompt via sessionStorage:', _prompt);

			clone = true;
			prompt = {
				title: _prompt.title,
				command: _prompt.command,
				content: _prompt.content,
				access_control: null
			};
		}
	});
</script>

{#key prompt}
	<PromptEditor {prompt} {onSubmit} {clone} />
{/key}
