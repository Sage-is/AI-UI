<script lang="ts">
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let onChange: (params: any) => void = () => {};
	export let admin = false;
	export let custom = false;

	const defaultParams = {
		// Advanced
		stream_response: null, // Set stream responses for this model individually
		function_calling: null,
		seed: null,
		stop: null,
		temperature: null,
		reasoning_effort: null,
		logit_bias: null,
		max_tokens: null,
		top_k: null,
		top_p: null,
		min_p: null,
		frequency_penalty: null,
		presence_penalty: null,
		mirostat: null,
		mirostat_eta: null,
		mirostat_tau: null,
		repeat_last_n: null,
		tfs_z: null,
		repeat_penalty: null,
		use_mmap: null,
		use_mlock: null,
		think: null,
		format: null,
		keep_alive: null,
		num_keep: null,
		num_ctx: null,
		num_batch: null,
		num_thread: null,
		num_gpu: null,
		custom_params: {}
	} as any;

	export let params: any = defaultParams;
	$: if (params) {
		onChange(params);
	}

	// DRY: Complete unified parameter configuration - eliminates ALL repetitive HTML
	const allParameters = [
		// Special tristate parameters
		{
			key: 'stream_response',
			label: 'Stream Chat Response',
			tooltip: 'When enabled, the model will respond to each chat message in real-time, generating a response as soon as the user sends a message. This mode is useful for live chat applications, but may impact performance on slower hardware.',
			type: 'tristate',
			defaultValue: true
		},
		{
			key: 'function_calling',
			label: 'Function Calling',
			tooltip: "Default mode works with a wider range of models by calling tools once before execution. Native mode leverages the model's built-in tool-calling capabilities, but requires the model to inherently support this feature.",
			type: 'function_calling',
			defaultValue: 'native'
		},
		// Basic AI parameters
		{
			key: 'seed',
			label: 'Seed',
			tooltip: 'Sets the random number seed to use for generation. Setting this to a specific number will make the model generate the same text for the same prompt.',
			type: 'number',
			placeholder: 'Enter Seed',
			min: '0',
			defaultValue: 0
		},
		{
			key: 'stop',
			label: 'Stop Sequence',
			tooltip: 'Sets the stop sequences to use. When this pattern is encountered, the LLM will stop generating text and return. Multiple stop patterns may be set by specifying multiple separate stop parameters in a modelfile.',
			type: 'text',
			placeholder: 'Enter stop sequence',
			defaultValue: ''
		},
		{
			key: 'temperature',
			label: 'Temperature',
			tooltip: 'The temperature of the model. Increasing the temperature will make the model answer more creatively.',
			type: 'number',
			placeholder: 'Enter temperature',
			step: '0.01',
			min: '0',
			max: '2',
			defaultValue: 0.8
		},
		{
			key: 'reasoning_effort',
			label: 'Reasoning Effort',
			tooltip: 'Constrains effort on reasoning for reasoning models. Only applicable to reasoning models from specific providers that support reasoning effort.',
			type: 'text',
			placeholder: 'Enter reasoning effort',
			defaultValue: 'medium'
		},
		{
			key: 'logit_bias',
			label: 'logit_bias',
			tooltip: 'Boosting or penalizing specific tokens for constrained responses. Bias values will be clamped between -100 and 100 (inclusive). (Default: none)',
			type: 'text',
			placeholder: 'Enter comma-separated "token:bias_value" pairs (example: 5432:100, 413:-100)',
			defaultValue: ''
		},
		{
			key: 'max_tokens',
			label: 'Max Tokens (num_predict)',
			tooltip: 'This option sets the maximum number of tokens the model can generate in its response. Increasing this limit allows the model to provide longer answers, but it may also increase the likelihood of unhelpful or irrelevant content being generated.',
			type: 'range',
			placeholder: 'Enter max tokens',
			min: '-2',
			max: '131072',
			step: '1',
			defaultValue: 128
		},
		{
			key: 'top_k',
			label: 'Top K',
			tooltip: 'Reduces the probability of generating nonsense. A higher value (e.g. 100) will give more diverse answers, while a lower value (e.g. 10) will be more conservative.',
			type: 'range',
			placeholder: 'Enter Top K',
			min: '0',
			max: '1000',
			step: '0.5',
			defaultValue: 40
		},
		{
			key: 'top_p',
			label: 'Top P',
			tooltip: 'Works together with top-k. A higher value (e.g., 0.95) will lead to more diverse text, while a lower value (e.g., 0.5) will generate more focused and conservative text.',
			type: 'range',
			placeholder: 'Enter Top P',
			step: '0.05',
			min: '0',
			max: '1',
			defaultValue: 0.9
		},
		{
			key: 'min_p',
			label: 'Min P',
			tooltip: 'Alternative to the top_p, and aims to ensure a balance of quality and variety. The parameter p represents the minimum probability for a token to be considered, relative to the probability of the most likely token. For example, with p=0.05 and the most likely token having a probability of 0.9, logits with a value less than 0.045 are filtered out.',
			type: 'range',
			placeholder: 'Enter Min P',
			step: '0.05',
			min: '0',
			max: '1',
			defaultValue: 0.0
		},
		{
			key: 'frequency_penalty',
			label: 'Frequency Penalty',
			tooltip: 'Sets a scaling bias against tokens to penalize repetitions, based on how many times they have appeared. A higher value (e.g., 1.5) will penalize repetitions more strongly, while a lower value (e.g., 0.9) will be more lenient. At 0, it is disabled.',
			type: 'range',
			placeholder: 'Enter frequency penalty',
			step: '0.05',
			min: '-2',
			max: '2',
			defaultValue: 1.1
		},
		{
			key: 'presence_penalty',
			label: 'Presence Penalty',
			tooltip: 'Sets a flat bias against tokens that have appeared at least once. A higher value (e.g., 1.5) will penalize repetitions more strongly, while a lower value (e.g., 0.9) will be more lenient. At 0, it is disabled.',
			type: 'range',
			placeholder: 'Enter presence penalty',
			step: '0.05',
			min: '-2',
			max: '2',
			defaultValue: 0.0
		},
		// Mirostat parameters
		{
			key: 'mirostat',
			label: 'Mirostat',
			tooltip: 'Enable Mirostat sampling for controlling perplexity.',
			type: 'range',
			placeholder: 'Enter mirostat',
			min: '0',
			max: '2',
			step: '1',
			defaultValue: 0
		},
		{
			key: 'mirostat_eta',
			label: 'Mirostat Eta',
			tooltip: 'Influences how quickly the algorithm responds to feedback from the generated text. A lower learning rate will result in slower adjustments, while a higher learning rate will make the algorithm more responsive.',
			type: 'range',
			placeholder: 'Enter mirostat eta',
			step: '0.05',
			min: '0',
			max: '1',
			defaultValue: 0.1
		},
		{
			key: 'mirostat_tau',
			label: 'Mirostat Tau',
			tooltip: 'Controls the balance between coherence and diversity of the output. A lower value will result in more focused and coherent text.',
			type: 'range',
			placeholder: 'Enter mirostat tau',
			step: '0.5',
			min: '0',
			max: '10',
			defaultValue: 5.0
		},
		// Repeat penalty parameters  
		{
			key: 'repeat_penalty',
			label: 'Repeat Penalty',
			tooltip: 'Control the repetition of token sequences in the generated text. A higher value (e.g., 1.5) will penalize repetitions more strongly, while a lower value (e.g., 1.1) will be more lenient. At 1, it is disabled.',
			type: 'range',
			placeholder: 'Enter repeat penalty',
			step: '0.05',
			min: '-2',
			max: '2',
			defaultValue: 1.1
		},
		{
			key: 'repeat_last_n',
			label: 'Repeat Last N',
			tooltip: 'Sets how far back for the model to look back to prevent repetition.',
			type: 'range',
			placeholder: 'Enter repeat last n',
			min: '-1',
			max: '128',
			step: '1',
			defaultValue: 64
		},
		// Advanced sampling parameters
		{
			key: 'tfs_z',
			label: 'TFS Z',
			tooltip: 'Tail free sampling is used to reduce the impact of less probable tokens from the output. A higher value (e.g., 2.0) will reduce the impact more, while a value of 1.0 disables this setting.',
			type: 'range',
			placeholder: 'Enter TFS Z',
			step: '0.05',
			min: '0',
			max: '2',
			defaultValue: 1
		},
		// Admin/System parameters
		{
			key: 'use_mmap',
			label: 'use_mmap',
			tooltip: 'Enable Memory Mapping (mmap) to load model data. This option allows the system to use disk storage as an extension of RAM by treating disk files as if they were in RAM. This can improve model performance by allowing for faster data access. However, it may not work correctly with all systems and can consume a significant amount of disk space.',
			type: 'switch',
			defaultValue: true,
			adminOnly: true
		},
		{
			key: 'use_mlock',
			label: 'use_mlock',
			tooltip: "Enable Memory Locking (mlock) to prevent model data from being swapped out of RAM. This option locks the model's working set of pages into RAM, ensuring that they will not be swapped out to disk. This can help maintain performance by avoiding page faults and ensuring fast data access.",
			type: 'switch',
			defaultValue: true,
			adminOnly: true
		},
		{
			key: 'think',
			label: 'think',
			tooltip: 'This option enables or disables the use of the reasoning feature in Ollama, which allows the model to think before generating a response. When enabled, the model can take a moment to process the conversation context and generate a more thoughtful response.',
			type: 'tristate',
			defaultValue: true,
			suffix: 'Ollama'
		},
		{
			key: 'format',
			label: 'format',
			tooltip: 'The format to return a response in. Format can be json or a JSON schema.',
			type: 'textarea',
			placeholder: 'e.g. "json" or a JSON schema',
			defaultValue: 'json',
			suffix: 'Ollama'
		},
		{
			key: 'num_keep',
			label: 'num_keep',
			tooltip: 'This option controls how many tokens are preserved when refreshing the context. For example, if set to 2, the last 2 tokens of the conversation context will be retained. Preserving context can help maintain the continuity of a conversation, but it may reduce the ability to respond to new topics.',
			type: 'range',
			placeholder: 'Enter num keep',
			min: '-1',
			max: '10240000',
			step: '1',
			defaultValue: 24,
			suffix: 'Ollama'
		},
		{
			key: 'num_ctx',
			label: 'num_ctx',
			tooltip: 'Sets the size of the context window used to generate the next token.',
			type: 'range',
			placeholder: 'Enter num ctx',
			min: '-1',
			max: '10240000',
			step: '1',
			defaultValue: 2048,
			suffix: 'Ollama'
		},
		{
			key: 'num_batch',
			label: 'num_batch',
			tooltip: 'The batch size determines how many text requests are processed together at once. A higher batch size can increase the performance and speed of the model, but it also requires more memory.',
			type: 'range',
			placeholder: 'Enter num batch',
			min: '256',
			max: '8192',
			step: '256',
			defaultValue: 512,
			suffix: 'Ollama'
		},
		{
			key: 'num_thread',
			label: 'num_thread',
			tooltip: 'Set the number of worker threads used for computation. This option controls how many threads are used to process incoming requests concurrently. Increasing this value can improve performance under high concurrency workloads but may also consume more CPU resources.',
			type: 'range',
			placeholder: 'Enter num thread',
			min: '1',
			max: '256',
			step: '1',
			defaultValue: 2,
			suffix: 'Ollama',
			adminOnly: true
		},
		{
			key: 'num_gpu',
			label: 'num_gpu',
			tooltip: 'Set the number of layers, which will be off-loaded to GPU. Increasing this value can significantly improve performance for models that are optimized for GPU acceleration but may also consume more power and GPU resources.',
			type: 'range',
			placeholder: 'Enter num gpu',
			min: '0',
			max: '256',
			step: '1',
			defaultValue: 0,
			suffix: 'Ollama',
			adminOnly: true
		},
		{
			key: 'keep_alive',
			label: 'keep_alive',
			tooltip: 'This option controls how long the model will stay loaded into memory following the request (default: 5m)',
			type: 'text',
			placeholder: "e.g. '30s','10m'. Valid time units are 's', 'm', 'h'.",
			defaultValue: '5m',
			suffix: 'Ollama',
			adminOnly: true
		}
	];

	// DRY: Unified parameter toggle function
	function toggleParameter(config: any) {
		const { key, type, defaultValue } = config;
		
		if (type === 'tristate') {
			params[key] = (params?.[key] ?? null) === null ? defaultValue : params[key] ? false : null;
		} else if (type === 'function_calling') {
			params[key] = (params?.[key] ?? null) === null ? defaultValue : null;
		} else {
			params[key] = (params?.[key] ?? null) === null ? defaultValue : null;
		}
	}

	// DRY: Unified button label function
	function getButtonLabel(config: any) {
		const { key, type } = config;
		const value = params?.[key] ?? null;
		
		if (type === 'tristate') {
			if (value === true) return 'On';
			if (value === false) return 'Off';
			return 'Default';
		} else if (type === 'function_calling') {
			return value === 'native' ? 'Native' : 'Default';
		} else {
			return value === null ? 'Default' : 'Custom';
		}
	}
</script>

<!-- The entire template is now one clean loop. -->
<!-- All rendering logic is derived from the `config` object in each iteration. -->
<div style="--g:0.25rem; --size:0.75rem"
	class="pb-safe-bottom">
	{#each allParameters as config (config.key)}
		{#if !config.adminOnly || admin}
			<div style="--py:0.125rem; --w:100%; --jc:space-between">
				<!-- Header Row (Label, Tooltip, and Toggle Button) -->
				<Tooltip content={$i18n.t(config.tooltip)} placement="top-start" className="inline-tooltip">
					<div style="--d:flex; --w:100%; --jc:space-between; --ai:center">
						<div style="--as:center; --size:0.75rem; --weight:500">
							{$i18n.t(config.label)}
							{#if config.suffix}
								<span style="--c:var(--color-gray-500, #9b9b9b); --pl:0.25rem">({$i18n.t(config.suffix)})</span>
							{/if}
						</div>
						<button
							style="--p:0.25rem; --px:0.75rem; --size:0.75rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --fs:0; --oe:none"
							type="button"
							on:click={() => toggleParameter(config)}
						>
							<span style="--ml:0.5rem; --as:center">{$i18n.t(getButtonLabel(config))}</span>
						</button>
					</div>
				</Tooltip>

				<!-- Input Control Row (Dynamically Rendered) -->
				{#if (params[config.key] ?? null) !== null}
					<div style="--d:flex; --mt:0.375rem; --g:0.5rem; --ai:center">
						<!-- This `if/else if` block is the dynamic rendering engine. -->
						{#if config.type === 'text'}
							<input
								style="--size:0.875rem; --w:100%; --bgc:transparent; --oe:2px solid transparent; --oe:none"
								type="text"
								placeholder={$i18n.t(config.placeholder ?? '')}
								bind:value={params[config.key]}
								autocomplete="off"
							/>
						{:else if config.type === 'number'}
							<input
								style="--size:0.875rem; --w:100%; --bgc:transparent; --oe:2px solid transparent; --oe:none"
								type="number"
								placeholder={$i18n.t(config.placeholder ?? '')}
								bind:value={params[config.key]}
								min={config.min}
								max={config.max}
								step={config.step}
								autocomplete="off"
							/>
						{:else if config.type === 'textarea'}
							<Textarea
								className="w-full text-sm bg-transparent outline-hidden"
								placeholder={$i18n.t(config.placeholder ?? '')}
								bind:value={params[config.key]}
							/>
						{:else if config.type === 'switch'}
							<div style="--w:100%; --pr:0.25rem; --d:flex; --jc:space-between; --ai:center">
								<div style="--size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">
									{params[config.key] ? 'Enabled' : 'Disabled'}
								</div>
								<div style="--pr:0.5rem">
									<Switch bind:state={params[config.key]} />
								</div>
							</div>
						{:else if config.type === 'range'}
							<div style="--fx:1 1 0%">
								<input
									type="range"
									style="--w:100%; --h:0.5rem; --radius:0.5rem; appearance:none; --cur:pointer; --bgc:var(--color-gray-200, #e3e3e3); --dark-bgc:var(--color-gray-700, #4e4e4e)"
									bind:value={params[config.key]}
									min={config.min}
									max={config.max}
									step={config.step}
								/>
							</div>
							<div>
								<input
									type="number"
									style="--bgc:transparent; --ta:center; --w:3.5rem; --size:0.875rem"
									bind:value={params[config.key]}
									min={config.min}
									max={config.max}
									step={config.step}
								/>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		{/if}
	{/each}

	<!-- Custom Parameters Section -->
	{#if custom && admin}
		<div style="--d:flex; --fd:column; --jc:center">
			{#each Object.keys(params?.custom_params ?? {}) as key}
				<div style="--py:0.125rem; --w:100%; --jc:space-between; --mb:0.25rem">
					<div style="--d:flex; --w:100%; --jc:space-between">
						<div style="--as:center; --size:0.75rem; --weight:500">
							<input
								type="text"
								style="--size:0.75rem; --w:100%; --bgc:transparent; --oe:2px solid transparent"
								placeholder={$i18n.t('Custom Parameter Name')}
								value={key}
								on:change={(e) => {
									const newKey = e?.target?.value?.trim();
									if (newKey && newKey !== key) {
										params.custom_params[newKey] = params.custom_params[key];
										delete params.custom_params[key];
										params = {
											...params,
											custom_params: { ...params.custom_params }
										};
									}
								}}
							/>
						</div>
						<button
							style="--p:0.25rem; --px:0.75rem; --size:0.75rem; --d:flex; --radius:0.125rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --fs:0; --oe:none"
							type="button"
							on:click={() => {
								delete params.custom_params[key];
								params = {
									...params,
									custom_params: { ...params.custom_params }
								};
							}}
						>
							{$i18n.t('Remove')}
						</button>
					</div>
					<div style="--d:flex; --mt:0.125rem; --g:0.5rem">
						<div style="--fx:1 1 0%">
							<input
								bind:value={params.custom_params[key]}
								type="text"
								style="--size:0.875rem; --w:100%; --bgc:transparent; --oe:none; --oe:2px solid transparent"
								placeholder={$i18n.t('Custom Parameter Value')}
							/>
						</div>
					</div>
				</div>
			{/each}

			<button
				style="--d:flex; --g:0.5rem; --ai:center; --w:100%; --ta:center; --jc:center; --mt:0.25rem; --mb:1.25rem"
				type="button"
				on:click={() => {
					params.custom_params = (params?.custom_params ?? {}) || {};
					params.custom_params['custom_param_name'] = 'custom_param_value';
				}}
			>
				<div>
					<Plus />
				</div>
				<div>{$i18n.t('Add Custom Parameter')}</div>
			</button>
		</div>
	{/if}
</div>
