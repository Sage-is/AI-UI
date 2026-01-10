<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { models, temporaryChatEnabled } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { chatCompletion, generateOpenAIChatCompletion } from '$lib/apis/openai';
	import { splitStream } from '$lib/utils';
	
	import Spinner from '$lib/components/common/Spinner.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';

	const i18n = getContext('i18n');

	export let liveModelData = null;

	let messages = [];
	let currentMessage = '';
	let loading = false;
	let stopResponseFlag = false;
	let messagesContainer;
	let textareaElement;

	// Reactive temporary model for testing
	$: testModel = liveModelData ? {
		id: liveModelData.id || 'test-model',
		name: liveModelData.name || 'Test Model',
		info: liveModelData,
		// Use the base model for actual inference
		base_model_id: liveModelData.base_model_id
	} : null;

	const scrollToBottom = () => {
		if (messagesContainer) {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
		}
	};

	const stopResponse = () => {
		stopResponseFlag = true;
	};

	const sendMessage = async () => {
		if (!currentMessage.trim() || loading || !testModel) return;

		const userMessage = {
			role: 'user',
			content: currentMessage.trim(),
			timestamp: Date.now()
		};

		messages = [...messages, userMessage];
		currentMessage = '';
		loading = true;
		await tick();
		scrollToBottom();

		// Find the actual base model to use for inference
		const baseModel = $models.find(m => m.id === testModel.base_model_id);
		if (!baseModel) {
			console.error('Base model not found:', testModel.base_model_id, 'Available models:', $models.map(m => m.id));
			toast.error('Base model not found. Please select a valid base model.');
			loading = false;
			return;
		}

		console.log('ModelTestChat - Using base model:', {
			id: baseModel.id,
			name: baseModel.name,
			owned_by: baseModel.owned_by,
			base_url: baseModel.base_url,
			api_key: baseModel.api_key ? '[PRESENT]' : '[MISSING]'
		});

		// Create assistant message
		const assistantMessage = {
			role: 'assistant',
			content: '',
			timestamp: Date.now(),
			loading: true
		};
		messages = [...messages, assistantMessage];
		await tick();
		scrollToBottom();

		try {
			// Prepare messages for API call (same format as main chat)
			const apiMessages = [
				// Add system prompt if available (same as main chat)
				...(liveModelData?.params?.system ? [{
					role: 'system',
					content: liveModelData.params.system
				}] : []),
				// Add conversation history
				...messages.filter(m => m.role !== 'assistant' || !m.loading).map(m => ({
					role: m.role,
					content: m.content
				}))
			];

			// Filter params to only include standard OpenAI parameters that Groq supports
			const allowedParams = ['temperature', 'top_p', 'max_tokens', 'stop', 'presence_penalty', 'frequency_penalty'];
			const filteredParams = liveModelData?.params ? 
				Object.fromEntries(
					Object.entries(liveModelData.params)
						.filter(([key]) => allowedParams.includes(key) && key !== 'system')
				) : {};

			const payload = {
				stream: true,
				model: baseModel.id,
				messages: apiMessages,
				...filteredParams
			};

			console.log('ModelTestChat - Chat payload:', {
				model: payload.model,
				messages_count: payload.messages.length,
				has_system: apiMessages.some(m => m.role === 'system'),
				stream: payload.stream,
				filtered_params: filteredParams,
				original_params: liveModelData?.params || {},
				api_url: `${WEBUI_BASE_URL}/api`
			});

			// Use chatCompletion with proper params structure for backend routing
			const [res, controller] = await chatCompletion(
				localStorage.token,
				payload,
				`${WEBUI_BASE_URL}/api`
			);

			if (res && res.ok) {
				console.log('ModelTestChat - Got successful response, starting stream read');
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
						const lines = value.split('\n');
						for (const line of lines) {
							if (line !== '') {
								if (line === 'data: [DONE]') {
									// Stream complete
									break;
								} else if (line.startsWith('data: ')) {
									const data = JSON.parse(line.replace(/^data: /, ''));
									if (data.choices?.[0]?.delta?.content) {
										// Update the last assistant message
										const lastMessage = messages[messages.length - 1];
										if (lastMessage.role === 'assistant') {
											lastMessage.content += data.choices[0].delta.content;
											lastMessage.loading = false;
											messages = [...messages];
											await tick();
											scrollToBottom();
										}
									}
								}
							}
						}
					} catch (error) {
						console.error('Error parsing stream data:', error);
					}
				}
			} else {
				console.error('ModelTestChat - Bad response:', {
					status: res?.status,
					statusText: res?.statusText,
					headers: res?.headers ? Object.fromEntries(res.headers.entries()) : 'No headers',
					url: res?.url
				});
				const responseText = await res?.text();
				console.error('ModelTestChat - Response body:', responseText);
				throw new Error(`Failed to get response from model (${res?.status}: ${res?.statusText})`);
			}
		} catch (error) {
			console.error('ModelTestChat - Chat error details:', {
				error: error,
				message: error?.message,
				stack: error?.stack,
				baseModel: baseModel?.id,
				modelOwnership: baseModel?.owned_by
			});
			toast.error('Error communicating with model: ' + (error?.message || 'Unknown error'));
			
			// Remove the failed assistant message
			messages = messages.slice(0, -1);
		} finally {
			loading = false;
			stopResponseFlag = false;
			
			// Ensure the last message is marked as not loading
			if (messages.length > 0 && messages[messages.length - 1].role === 'assistant') {
				messages[messages.length - 1].loading = false;
				messages = [...messages];
			}
			
			// Return focus to textarea for continued conversation
			await tick();
			if (textareaElement) {
				textareaElement.focus();
			}
		}
	};

	const clearChat = () => {
		messages = [];
	};

	const handleKeydown = (e) => {
		if (e.key === 'Enter' && !e.shiftKey) {
			// Send message on Enter, regardless of Ctrl/Cmd state
			e.preventDefault();
			sendMessage();
		}
		// Shift+Enter allows new line (default textarea behavior)
	};

	onMount(() => {
		// Set temporary chat mode
		temporaryChatEnabled.set(true);
		
		return () => {
			// Restore previous temporary chat setting when component is destroyed
			temporaryChatEnabled.set(false);
		};
	});
</script>

<div class="flex flex-col h-full bg-gray-50 dark:bg-gray-900/50">
	<!-- Header -->
	<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
		<div class="flex items-center gap-2">
			<EyeSlash className="size-4 text-gray-500" />
			<h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">
				{$i18n.t('Test Chat')}
			</h3>
		</div>
		
		{#if messages.length > 0}
			<button
				class="text-xs px-2 py-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
				on:click={clearChat}
			>
				{$i18n.t('Clear')}
			</button>
		{/if}
	</div>

	<!-- Model info -->
	{#if testModel}
		<div class="p-3 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800">
			<div class="text-xs text-blue-700 dark:text-blue-300">
				<div class="font-medium">{testModel.name}</div>
				{#if testModel.base_model_id}
					<div class="opacity-75">Base: {testModel.base_model_id}</div>
				{/if}
				{#if liveModelData?.params?.system}
					<div class="mt-1 opacity-75 line-clamp-2">System: {liveModelData.params.system}</div>
				{/if}
			</div>
		</div>
	{:else}
		<div class="p-3 bg-yellow-50 dark:bg-yellow-900/20 border-b border-yellow-200 dark:border-yellow-800">
			<div class="text-xs text-yellow-700 dark:text-yellow-300">
				{$i18n.t('Configure your model to start testing')}
			</div>
		</div>
	{/if}

	<!-- Messages -->
	<div 
		class="flex-1 overflow-y-auto p-4 space-y-4"
		bind:this={messagesContainer}
	>
		{#if messages.length === 0}
			<div class="text-center text-gray-500 mt-8">
				<div class="text-sm">{$i18n.t('Start a conversation to test your model')}</div>
				{#if testModel}
					<div class="text-xs mt-2 opacity-75">
						Not all chat features are available in test chats. <br>
						{$i18n.t('This is a temporary test chat that won\'t be saved')}
					</div>
				{/if}
			</div>
		{:else}
			{#each messages as message}
				<div class="flex {message.role === 'user' ? 'justify-end' : 'justify-start'}">
					<div class="max-w-[80%] {message.role === 'user' 
						? 'bg-gray-900 text-white dark:bg-white dark:text-black' 
						: 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700'} 
						rounded-lg px-3 py-2 text-sm">
						
						{#if message.role === 'user'}
							<div class="whitespace-pre-wrap">{message.content}</div>
						{:else}
							<div class="whitespace-pre-wrap">{message.content}</div>
							{#if message.loading}
								<div class="flex items-center gap-1 mt-1 opacity-75">
									<Spinner className="size-3" />
									<span class="text-xs">{$i18n.t('Thinking...')}</span>
								</div>
							{/if}
						{/if}
					</div>
				</div>
			{/each}
		{/if}
	</div>

	<!-- Input -->
	<div class="p-4 border-t border-gray-200 dark:border-gray-700">
		<div class="flex gap-2">
			<div class="flex-1">
				<textarea
					bind:this={textareaElement}
					class="w-full text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 resize-none outline-hidden"
					placeholder={testModel ? $i18n.t('Ask something...') : $i18n.t('Configure your model first')}
					bind:value={currentMessage}
					on:keydown={handleKeydown}
					on:input={(e) => {
						// Auto-resize textarea
						e.target.style.height = 'auto';
						e.target.style.height = e.target.scrollHeight + 'px';
					}}
					rows={1}
					disabled={!testModel || loading}
					style="height: auto; min-height: 2.5rem; max-height: 10rem;"
				/>
			</div>
			
			{#if loading}
				<button
					class="px-3 py-2 text-sm bg-gray-300 text-gray-600 rounded-lg flex items-center gap-1"
					on:click={stopResponse}
				>
					<span>{$i18n.t('Stop')}</span>
				</button>
			{:else}
				<button
					class="px-3 py-2 text-sm bg-gray-900 text-white dark:bg-white dark:text-black rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
					disabled={!currentMessage.trim() || !testModel}
					on:click={sendMessage}
				>
					{$i18n.t('Send')}
				</button>
			{/if}
		</div>
		
		<div class="text-xs text-gray-500 mt-2 flex items-center gap-1">
			<EyeSlash className="size-3" />
			<span>{$i18n.t('Temporary chat - messages won\'t be saved')}</span>
		</div>
	</div>
</div>
