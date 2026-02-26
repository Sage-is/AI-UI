<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { onMount, tick, getContext } from 'svelte';

	import {
		OLLAMA_API_BASE_URL,
		OPENAI_API_BASE_URL,
		WEBUI_API_BASE_URL,
		WEBUI_BASE_URL
	} from '$lib/constants';
	import { WEBUI_NAME, config, user, models, settings } from '$lib/stores';

	import { chatCompletion, generateOpenAIChatCompletion } from '$lib/apis/openai';

	import { splitStream } from '$lib/utils';
	import Collapsible from '../common/Collapsible.svelte';

	import Messages from '$lib/components/playground/Chat/Messages.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import Pencil from '../icons/Pencil.svelte';
	import Cog6 from '../icons/Cog6.svelte';
	import Sidebar from '../common/Sidebar.svelte';
	import ArrowRight from '../icons/ArrowRight.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let selectedModelId = '';
	let loading = false;
	let stopResponseFlag = false;

	let systemTextareaElement: HTMLTextAreaElement;
	let messagesContainerElement: HTMLDivElement;

	let showSystem = false;
	let showSettings = false;

	let system = '';

	let role = 'user';
	let message = '';

	let messages = [];

	const scrollToBottom = () => {
		const element = messagesContainerElement;

		if (element) {
			element.scrollTop = element?.scrollHeight;
		}
	};

	const stopResponse = () => {
		stopResponseFlag = true;
		console.log('stopResponse');
	};

	const resizeSystemTextarea = async () => {
		await tick();
		if (systemTextareaElement) {
			systemTextareaElement.style.height = '';
			systemTextareaElement.style.height = Math.min(systemTextareaElement.scrollHeight, 555) + 'px';
		}
	};

	$: if (showSystem) {
		resizeSystemTextarea();
	}

	const chatCompletionHandler = async () => {
		if (selectedModelId === '') {
			toast.error($i18n.t('Please select a model.'));
			return;
		}

		const model = $models.find((model) => model.id === selectedModelId);
		if (!model) {
			selectedModelId = '';
			return;
		}

		const [res, controller] = await chatCompletion(
			localStorage.token,
			{
				model: model.id,
				stream: true,
				messages: [
					system
						? {
								role: 'system',
								content: system
							}
						: undefined,
					...messages
				].filter((message) => message)
			},
			`${WEBUI_BASE_URL}/api`
		);

		let responseMessage;
		if (messages.at(-1)?.role === 'assistant') {
			responseMessage = messages.at(-1);
		} else {
			responseMessage = {
				role: 'assistant',
				content: ''
			};
			messages.push(responseMessage);
			messages = messages;
		}

		await tick();
		const textareaElement = document.getElementById(`assistant-${messages.length - 1}-textarea`);

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
							console.log(line);
							if (line === 'data: [DONE]') {
								// responseMessage.done = true;
								messages = messages;
							} else {
								let data = JSON.parse(line.replace(/^data: /, ''));
								console.log(data);

								if (responseMessage.content == '' && data.choices[0].delta.content == '\n') {
									continue;
								} else {
									textareaElement.style.height = textareaElement.scrollHeight + 'px';

									responseMessage.content += data.choices[0].delta.content ?? '';
									messages = messages;

									textareaElement.style.height = textareaElement.scrollHeight + 'px';

									await tick();
								}
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

	const addHandler = async () => {
		if (message) {
			messages.push({
				role: role,
				content: message
			});
			messages = messages;
			message = '';
			await tick();
			scrollToBottom();
		}
	};

	const submitHandler = async () => {
		if (selectedModelId) {
			await addHandler();

			loading = true;
			await chatCompletionHandler();

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
	<div style="--mx:auto; --w:100%; --px-md:0; --h:100%; --pos:relative">
		<div style="--d:flex; --fd:column; --h:100%; --px:0.875rem">
			<div style="--d:flex; --w:100%; --ai:flex-start; --g:0.375rem">
				<Collapsible
					className="w-full flex-1"
					bind:open={showSystem}
					buttonClassName="w-full rounded-lg text-sm border border-gray-100 dark:border-gray-850 w-full py-1 px-1.5"
					grow={true}
				>
					<div style="--d:flex; --g:0.5rem; --jc:space-between; --ai:center">
						<div style="--fs:0; --weight:500; --ml:0.375rem">
							{$i18n.t('System Prompt')}
						</div>

						{#if !showSystem}
							<div style="--fx:1 1 0%; --c:var(--color-gray-500); --line-clamp:1">
								{system}
							</div>
						{/if}

						<div style="--fs:0">
							<button style="--p:0.375rem; --bgc:transparent; --hvr-bgc:rgb(255 255 255 / 0.05); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem">
								{#if showSystem}
									<ChevronUp className="size-3.5" />
								{:else}
									<Pencil className="size-3.5" />
								{/if}
							</button>
						</div>
					</div>

					<div slot="content">
						<div style="--pt:0.25rem; --px:0.375rem">
							<textarea
								bind:this={systemTextareaElement}
								style="--w:100%; --h:100%; --bgc:transparent; resize:none; --oe:none; --size:0.875rem"
								bind:value={system}
								placeholder={$i18n.t("You're a helpful assistant.")}
								on:input={() => {
									resizeSystemTextarea();
								}}
								rows="4"
							/>
						</div>
					</div>
				</Collapsible>
			</div>

			<div
				style="--pb:0.625rem; --d:flex; --fd:column; --jc:space-between; --w:100%; --fx:1 1 auto; --of:auto; --h:0"
				id="messages-container"
				bind:this={messagesContainerElement}
			>
				<div style="--h:100%; --w:100%; --d:flex; --fd:column">
					<div style="--fx:1 1 0%; --p:0.25rem">
						<Messages bind:messages />
					</div>
				</div>
			</div>

			<div style="--pb:0.75rem">
				<div style="--b:1px solid; --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --w:100%; --px:0.75rem; --py:0.625rem; --radius:0.75rem">
					<div style="--py:0.125rem">
						<!-- $i18n.t('a user') -->
						<!-- $i18n.t('an assistant') -->
						<textarea
							bind:value={message}
							style="--w:100%; --h:100%; --bgc:transparent; resize:none; --oe:none; --size:0.875rem"
							placeholder={$i18n.t(`Enter {{role}} message here`, {
								role: role === 'user' ? $i18n.t('a user') : $i18n.t('an assistant')
							})}
							on:input={(e) => {
								e.target.style.height = '';
								e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
							}}
							on:focus={(e) => {
								e.target.style.height = '';
								e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
							}}
							rows="2"
						/>
					</div>

					<div style="--d:flex; --jc:space-between">
						<div>
							<button
								style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --c:var(--color-gray-900); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem"
								on:click={() => {
									role = role === 'user' ? 'assistant' : 'user';
								}}
							>
								{#if role === 'user'}
									{$i18n.t('User')}
								{:else}
									{$i18n.t('Assistant')}
								{/if}
							</button>
						</div>

						<div style="--d:flex; --ai:center; --g:0.5rem">
							<div class="">
								<select
									style="--bgc:transparent; --b:1px solid; --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --radius:0.5rem; --py:0.25rem; --px:0.5rem; --mx:-0.125rem; --size:0.875rem; --oe:none; --w:10rem"
									bind:value={selectedModelId}
								>
									{#each $models as model}
										<option value={model.id} style="--bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-700)"
											>{model.name}</option
										>
									{/each}
								</select>
							</div>

							{#if !loading}
								<button
									disabled={message === ''}
									style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --c:var(--color-gray-900); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem"
	class="disabled:bg-gray-50 dark:disabled:hover:bg-gray-850 disabled:cursor-not-allowed"
									on:click={() => {
										addHandler();
										role = role === 'user' ? 'assistant' : 'user';
									}}
								>
									{$i18n.t('Add')}
								</button>

								<button
									style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem"
									on:click={() => {
										submitHandler();
									}}
								>
									{$i18n.t('Run')}
								</button>
							{:else}
								<button
									style="--px:0.75rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:var(--color-gray-300); --c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem"
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
		</div>
	</div>
</div>
