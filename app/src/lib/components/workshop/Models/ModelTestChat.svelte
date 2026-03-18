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

<div style="--d:flex; --fd:column; --h:100%; --bgc:var(--color-gray-50); --dark-bgc:rgb(23 23 23 / 0.5)">
	<!-- Header -->
	<div style="--d:flex; --ai:center; --jc:space-between; --p:1rem;  --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700)">
		<div style="--d:flex; --ai:center; --g:0.5rem">
			<EyeSlash className="size-4 text-gray-500" />
			<h3 style="--size:0.875rem; --weight:500; --c:var(--color-gray-700); --dark-c:var(--color-gray-300)">
				{$i18n.t('Test Chat')}
			</h3>
		</div>
		
		{#if messages.length > 0}
			<button
				style="--size:0.6rem; --px:0.5rem; --py:0.25rem; --c:var(--color-gray-500); --hvr-c:var(--color-gray-700); --hvr-dark-c:var(--color-gray-300); --tn:color, background-color, border-color, text-decoration-color, fill, stroke 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				on:click={clearChat}
			>
				{$i18n.t('Clear')}
			</button>
		{/if}
	</div>

	<!-- Model info -->
	{#if testModel}
		<div style="--p:0.6rem; --bgc:#eff6ff; --dark-bgc:rgb(30 58 138 / 0.2);  --bc:#bfdbfe; --dark-bc:#1e40af">
			<div style="--size:0.6rem; --c:#1d4ed8; --dark-c:#93c5fd">
				<div style="--weight:500">{testModel.name}</div>
				{#if testModel.base_model_id}
					<div style="--op:0.75">Base: {testModel.base_model_id}</div>
				{/if}
				{#if liveModelData?.params?.system}
					<div style="--mt:0.25rem; --op:0.75; --line-clamp:2">System: {liveModelData.params.system}</div>
				{/if}
			</div>
		</div>
	{:else}
		<div style="--p:0.6rem; --bgc:#fefce8; --dark-bgc:rgb(113 63 18 / 0.2);  --bc:#fef08a; --dark-bc:#854d0e">
			<div style="--size:0.6rem; --c:#a16207; --dark-c:#fde047">
				{$i18n.t('Configure your model to start testing')}
			</div>
		</div>
	{/if}

	<!-- Messages -->
	<div 
		style="--fx:1 1 0%; --ofy:auto; --p:1rem; --g:1rem"
		bind:this={messagesContainer}
	>
		{#if messages.length === 0}
			<div style="--ta:center; --c:var(--color-gray-500); --mt:2rem">
				<div style="--size:0.875rem">{$i18n.t('Start a conversation to test your model')}</div>
				{#if testModel}
					<div style="--size:0.6rem; --mt:0.5rem; --op:0.75">
						Not all chat features are available in test chats. <br>
						{$i18n.t('This is a temporary test chat that won\'t be saved')}
					</div>
				{/if}
			</div>
		{:else}
			{#each messages as message}
				<div style="--d:flex"
	class="{message.role === 'user' ? 'justify-end' : 'justify-start'}">
					<div style="--maxw:80%; --radius:0.5rem; --px:0.6rem; --py:0.5rem; --size:0.875rem"
	class="{message.role === 'user' 
						? 'bg-gray-900 text-white dark:bg-white dark:text-black' 
						: 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700'}">
						
						{#if message.role === 'user'}
							<div style="--ws:pre-wrap">{message.content}</div>
						{:else}
							<div style="--ws:pre-wrap">{message.content}</div>
							{#if message.loading}
								<div style="--d:flex; --ai:center; --g:0.25rem; --mt:0.25rem; --op:0.75">
									<Spinner className="size-3" />
									<span style="--size:0.6rem">{$i18n.t('Thinking...')}</span>
								</div>
							{/if}
						{/if}
					</div>
				</div>
			{/each}
		{/if}
	</div>

	<!-- Input -->
	<div style="--p:1rem; --bt:1px solid; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700)">
		<div style="--d:flex; --g:0.5rem">
			<div style="--fx:1 1 0%">
				<textarea
					bind:this={textareaElement}
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
					style="--w:100%; --size:0.875rem; --bgc:#fff; --dark-bgc:var(--color-gray-800);  --bc:var(--color-gray-300); --dark-bc:var(--color-gray-600); --radius:0.5rem; --px:0.6rem; --py:0.5rem; resize:none; --oe:none; height: auto; min-height: 2.5rem; max-height: 10rem;"
				/>
			</div>
			
			{#if loading}
				<button
					style="--px:0.6rem; --py:0.5rem; --size:0.875rem; --bgc:var(--color-gray-300); --c:var(--color-gray-600); --radius:0.5rem; --d:flex; --ai:center; --g:0.25rem"
					on:click={stopResponse}
				>
					<span>{$i18n.t('Stop')}</span>
				</button>
			{:else}
				<button
					style="--px:0.6rem; --py:0.5rem; --size:0.875rem; --bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --radius:0.5rem; --hvr-op:0.9; --tn:opacity 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="disabled:opacity-50"
					disabled={!currentMessage.trim() || !testModel}
					on:click={sendMessage}
				>
					{$i18n.t('Send')}
				</button>
			{/if}
		</div>
		
		<div style="--size:0.6rem; --c:var(--color-gray-500); --mt:0.5rem; --d:flex; --ai:center; --g:0.25rem">
			<EyeSlash className="size-3" />
			<span>{$i18n.t('Temporary chat - messages won\'t be saved')}</span>
		</div>
	</div>
</div>
