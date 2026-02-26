<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { onMount, tick, getContext } from 'svelte';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, models, settings, showSidebar } from '$lib/stores';
	import { chatCompletion } from '$lib/apis/openai';

	import { splitStream } from '$lib/utils';
	import Selector from '$lib/components/chat/ModelSelector/Selector.svelte';
	import MenuLines from '../icons/MenuLines.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let text = '';

	let selectedModelId = '';

	let loading = false;
	let stopResponseFlag = false;

	let textCompletionAreaElement: HTMLTextAreaElement;

	const scrollToBottom = () => {
		const element = textCompletionAreaElement;

		if (element) {
			element.scrollTop = element?.scrollHeight;
		}
	};

	const stopResponse = () => {
		stopResponseFlag = true;
		console.log('stopResponse');
	};

	const textCompletionHandler = async () => {
		const model = $models.find((model) => model.id === selectedModelId);

		const [res, controller] = await chatCompletion(
			localStorage.token,
			{
				model: model.id,
				stream: true,
				messages: [
					{
						role: 'assistant',
						content: text
					}
				]
			},
			`${WEBUI_BASE_URL}/api`
		);

		if (res && res.ok) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				const { value, done } = await reader.read();
				if (done || stopResponseFlag) {
					if (stopResponseFlag) {
						controller.abort('User: Stop Response');
					}
					break;
				}

				try {
					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							if (line.includes('[DONE]')) {
								console.log('done');
							} else {
								let data = JSON.parse(line.replace(/^data: /, ''));
								console.log(data);

								text += data.choices[0].delta.content ?? '';
							}
						}
					}
				} catch (error) {
					console.log(error);
				}

				scrollToBottom();
			}
		}
	};

	const submitHandler = async () => {
		if (selectedModelId) {
			loading = true;
			await textCompletionHandler();

			loading = false;
			stopResponseFlag = false;
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}

		if ($settings?.models) {
			selectedModelId = $settings?.models[0];
		} else if ($config?.default_models) {
			selectedModelId = $config?.default_models.split(',')[0];
		} else {
			selectedModelId = '';
		}
		loaded = true;
	});
</script>

<div style="--d:flex; --fd:column; --jc:space-between; --w:100%; --ofy:auto; --h:100%">
	<div style="--mx:auto; --w:100%; --px-md:0; --h:100%">
		<div style="--d:flex; --fd:column; --h:100%; --px:1rem">
			<div style="--d:flex; --fd:column; --jc:space-between; --mb:0.25rem; --g:0.25rem">
				<div style="--d:flex; --fd:column; --g:0.25rem; --w:100%">
					<div style="--d:flex; --w:100%">
						<div style="--of:hidden; --w:100%">
							<div style="--maxw:100%">
								<Selector
									placeholder={$i18n.t('Select a model')}
									items={$models.map((model) => ({
										value: model.id,
										label: model.name,
										model: model
									}))}
									bind:value={selectedModelId}
								/>
							</div>
						</div>
					</div>
				</div>
			</div>

			<div
				style="--pt:0.125rem; --pb:0.625rem; --d:flex; --fd:column; --jc:space-between; --w:100%; --fx:1 1 auto; --of:auto; --h:0"
				id="messages-container"
			>
				<div style="--h:100%; --w:100%; --d:flex; --fd:column">
					<div style="--fx:1 1 0%">
						<textarea
							id="text-completion-textarea"
							bind:this={textCompletionAreaElement}
							style="--w:100%; --h:100%; --p:0.75rem; --bgc:transparent; --b:1px solid; --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --oe:none; resize:none; --radius:0.5rem; --size:0.875rem"
							bind:value={text}
							placeholder={$i18n.t("You're a helpful assistant.")}
						/>
					</div>
				</div>
			</div>

			<div style="--pb:0.75rem; --d:flex; --jc:flex-end">
				{#if !loading}
					<button
						style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
						on:click={() => {
							submitHandler();
						}}
					>
						{$i18n.t('Run')}
					</button>
				{:else}
					<button
						style="--px:0.75rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:var(--color-gray-300); --c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
						on:click={() => {
							stopResponse();
						}}
					>
						{$i18n.t('Cancel')}
					</button>
				{/if}
			</div>
		</div>
	</div>
</div>

<style>
	.scrollbar-hidden::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.scrollbar-hidden {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}
</style>
