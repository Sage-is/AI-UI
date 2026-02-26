<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { getCodeExecutionConfig, setCodeExecutionConfig } from '$lib/apis/configs';

	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let config = null;

	let engines = ['pyodide', 'jupyter'];

	const submitHandler = async () => {
		const res = await setCodeExecutionConfig(localStorage.token, config);
	};

	onMount(async () => {
		const res = await getCodeExecutionConfig(localStorage.token);

		if (res) {
			config = res;
		}
	});
</script>

<form
	style="--d:flex; --fd:column; --h:100%; --jc:space-between; --g:0.75rem; --size:0.875rem"
	on:submit|preventDefault={async () => {
		await submitHandler();
		saveHandler();
	}}
>
	<div style="--g:0.75rem; --ofy:scroll; --h:100%"
	class="scrollbar-hidden">
		{#if config}
			<div>
				<div style="--mb:0.875rem">
					<div style="--mb:0.625rem; --size:1rem; --weight:500">{$i18n.t('General')}</div>

					<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

					<div style="--mb:0.625rem">
						<div style="--d:flex; --w:100%; --jc:space-between">
							<div style="--as:center; --size:0.75rem; --weight:500">
								{$i18n.t('Enable Code Execution')}
							</div>

							<Switch bind:state={config.ENABLE_CODE_EXECUTION} />
						</div>
					</div>

					<div style="--mb:0.625rem">
						<div style="--d:flex; --w:100%; --jc:space-between">
							<div style="--as:center; --size:0.75rem; --weight:500">{$i18n.t('Code Execution Engine')}</div>
							<div style="--d:flex; --ai:center; --pos:relative">
								<select
									style="--dark-bgc:var(--color-gray-900); --w:fit-content; --pr:2rem; --radius:0.125rem; --px:0.5rem; --p:0.25rem; --size:0.75rem; --bgc:transparent; --oe:none; --ta:right"
									bind:value={config.CODE_EXECUTION_ENGINE}
									placeholder={$i18n.t('Select a engine')}
									required
								>
									<option disabled selected value="">{$i18n.t('Select a engine')}</option>
									{#each engines as engine}
										<option value={engine}>{engine}</option>
									{/each}
								</select>
							</div>
						</div>

						{#if config.CODE_EXECUTION_ENGINE === 'jupyter'}
							<div style="--c:var(--color-gray-500); --size:0.75rem">
								{$i18n.t(
									'Warning: Jupyter execution enables arbitrary code execution, posing severe security risks—proceed with extreme caution.'
								)}
							</div>
						{/if}
					</div>

					{#if config.CODE_EXECUTION_ENGINE === 'jupyter'}
						<div style="--mb:0.625rem; --d:flex; --fd:column; --g:0.375rem; --w:100%">
							<div style="--size:0.75rem; --weight:500">
								{$i18n.t('Jupyter URL')}
							</div>

							<div style="--d:flex; --w:100%">
								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --size:0.875rem; --py:0.125rem; --bgc:transparent; --oe:none"
	class="placeholder:text-gray-300 dark:placeholder:text-gray-700"
										type="text"
										placeholder={$i18n.t('Enter Jupyter URL')}
										bind:value={config.CODE_EXECUTION_JUPYTER_URL}
										autocomplete="off"
									/>
								</div>
							</div>
						</div>

						<div style="--mb:0.625rem; --d:flex; --fd:column; --g:0.375rem; --w:100%">
							<div style="--d:flex; --g:0.5rem; --w:100%; --ai:center; --jc:space-between">
								<div style="--size:0.75rem; --weight:500">
									{$i18n.t('Jupyter Auth')}
								</div>

								<div>
									<select
										style="--dark-bgc:var(--color-gray-900); --w:fit-content; --pr:2rem; --radius:0.125rem; --px:0.5rem; --p:0.25rem; --size:0.75rem; --bgc:transparent; --oe:none; --ta:left"
										bind:value={config.CODE_EXECUTION_JUPYTER_AUTH}
										placeholder={$i18n.t('Select an auth method')}
									>
										<option selected value="">{$i18n.t('None')}</option>
										<option value="token">{$i18n.t('Token')}</option>
										<option value="password">{$i18n.t('Password')}</option>
									</select>
								</div>
							</div>

							{#if config.CODE_EXECUTION_JUPYTER_AUTH}
								<div style="--d:flex; --w:100%; --g:0.5rem">
									<div style="--fx:1 1 0%">
										{#if config.CODE_EXECUTION_JUPYTER_AUTH === 'password'}
											<SensitiveInput
												type="text"
												placeholder={$i18n.t('Enter Jupyter Password')}
												bind:value={config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD}
												autocomplete="off"
											/>
										{:else}
											<SensitiveInput
												type="text"
												placeholder={$i18n.t('Enter Jupyter Token')}
												bind:value={config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN}
												autocomplete="off"
											/>
										{/if}
									</div>
								</div>
							{/if}
						</div>

						<div style="--d:flex; --g:0.5rem; --w:100%; --ai:center; --jc:space-between">
							<div style="--size:0.75rem; --weight:500">
								{$i18n.t('Code Execution Timeout')}
							</div>

							<div class="">
								<Tooltip content={$i18n.t('Enter timeout in seconds')}>
									<input
										style="--dark-bgc:var(--color-gray-900); --w:fit-content; --radius:0.125rem; --px:0.5rem; --p:0.25rem; --size:0.75rem; --bgc:transparent; --oe:none; --ta:right"
										type="number"
										bind:value={config.CODE_EXECUTION_JUPYTER_TIMEOUT}
										placeholder={$i18n.t('e.g. 60')}
										autocomplete="off"
									/>
								</Tooltip>
							</div>
						</div>
					{/if}
				</div>

				<div style="--mb:0.875rem">
					<div style="--mb:0.625rem; --size:1rem; --weight:500">{$i18n.t('Code Interpreter')}</div>

					<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

					<div style="--mb:0.625rem">
						<div style="--d:flex; --w:100%; --jc:space-between">
							<div style="--as:center; --size:0.75rem; --weight:500">
								{$i18n.t('Enable Code Interpreter')}
							</div>

							<Switch bind:state={config.ENABLE_CODE_INTERPRETER} />
						</div>
					</div>

					{#if config.ENABLE_CODE_INTERPRETER}
						<div style="--mb:0.625rem">
							<div style="--d:flex; --w:100%; --jc:space-between">
								<div style="--as:center; --size:0.75rem; --weight:500">
									{$i18n.t('Code Interpreter Engine')}
								</div>
								<div style="--d:flex; --ai:center; --pos:relative">
									<select
										style="--dark-bgc:var(--color-gray-900); --w:fit-content; --pr:2rem; --radius:0.125rem; --px:0.5rem; --p:0.25rem; --size:0.75rem; --bgc:transparent; --oe:none; --ta:right"
										bind:value={config.CODE_INTERPRETER_ENGINE}
										placeholder={$i18n.t('Select a engine')}
										required
									>
										<option disabled selected value="">{$i18n.t('Select a engine')}</option>
										{#each engines as engine}
											<option value={engine}>{engine}</option>
										{/each}
									</select>
								</div>
							</div>

							{#if config.CODE_INTERPRETER_ENGINE === 'jupyter'}
								<div style="--c:var(--color-gray-500); --size:0.75rem">
									{$i18n.t(
										'Warning: Jupyter execution enables arbitrary code execution, posing severe security risks—proceed with extreme caution.'
									)}
								</div>
							{/if}
						</div>

						{#if config.CODE_INTERPRETER_ENGINE === 'jupyter'}
							<div style="--mb:0.625rem; --d:flex; --fd:column; --g:0.375rem; --w:100%">
								<div style="--size:0.75rem; --weight:500">
									{$i18n.t('Jupyter URL')}
								</div>

								<div style="--d:flex; --w:100%">
									<div style="--fx:1 1 0%">
										<input
											style="--w:100%; --size:0.875rem; --py:0.125rem; --bgc:transparent; --oe:none"
	class="placeholder:text-gray-300 dark:placeholder:text-gray-700"
											type="text"
											placeholder={$i18n.t('Enter Jupyter URL')}
											bind:value={config.CODE_INTERPRETER_JUPYTER_URL}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div style="--mb:0.625rem; --d:flex; --fd:column; --g:0.375rem; --w:100%">
								<div style="--d:flex; --g:0.5rem; --w:100%; --ai:center; --jc:space-between">
									<div style="--size:0.75rem; --weight:500">
										{$i18n.t('Jupyter Auth')}
									</div>

									<div>
										<select
											style="--dark-bgc:var(--color-gray-900); --w:fit-content; --pr:2rem; --radius:0.125rem; --px:0.5rem; --p:0.25rem; --size:0.75rem; --bgc:transparent; --oe:none; --ta:left"
											bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH}
											placeholder={$i18n.t('Select an auth method')}
										>
											<option selected value="">{$i18n.t('None')}</option>
											<option value="token">{$i18n.t('Token')}</option>
											<option value="password">{$i18n.t('Password')}</option>
										</select>
									</div>
								</div>

								{#if config.CODE_INTERPRETER_JUPYTER_AUTH}
									<div style="--d:flex; --w:100%; --g:0.5rem">
										<div style="--fx:1 1 0%">
											{#if config.CODE_INTERPRETER_JUPYTER_AUTH === 'password'}
												<SensitiveInput
													type="text"
													placeholder={$i18n.t('Enter Jupyter Password')}
													bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD}
													autocomplete="off"
												/>
											{:else}
												<SensitiveInput
													type="text"
													placeholder={$i18n.t('Enter Jupyter Token')}
													bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN}
													autocomplete="off"
												/>
											{/if}
										</div>
									</div>
								{/if}
							</div>

							<div style="--d:flex; --g:0.5rem; --w:100%; --ai:center; --jc:space-between">
								<div style="--size:0.75rem; --weight:500">
									{$i18n.t('Code Execution Timeout')}
								</div>

								<div class="">
									<Tooltip content={$i18n.t('Enter timeout in seconds')}>
										<input
											style="--dark-bgc:var(--color-gray-900); --w:fit-content; --radius:0.125rem; --px:0.5rem; --p:0.25rem; --size:0.75rem; --bgc:transparent; --oe:none; --ta:right"
											type="number"
											bind:value={config.CODE_INTERPRETER_JUPYTER_TIMEOUT}
											placeholder={$i18n.t('e.g. 60')}
											autocomplete="off"
										/>
									</Tooltip>
								</div>
							</div>
						{/if}

						<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

						<div>
							<div style="--py:0.125rem; --w:100%">
								<div style="--mb:0.625rem; --size:0.75rem; --weight:500">
									{$i18n.t('Code Interpreter Prompt Template')}
								</div>

								<Tooltip
									content={$i18n.t(
										'Leave empty to use the default prompt, or enter a custom prompt'
									)}
									placement="top-start"
								>
									<Textarea
										bind:value={config.CODE_INTERPRETER_PROMPT_TEMPLATE}
										placeholder={$i18n.t(
											'Leave empty to use the default prompt, or enter a custom prompt'
										)}
									/>
								</Tooltip>
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>
	<div style="--d:flex; --jc:flex-end; --pt:0.75rem; --size:0.875rem; --weight:500">
		<button
			style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
