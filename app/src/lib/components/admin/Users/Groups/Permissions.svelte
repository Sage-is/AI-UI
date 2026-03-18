<script lang="ts">
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	// Default values for permissions
	const defaultPermissions = {
		workshop: {
			models: false,
			knowledge: false,
			prompts: false,
			tools: false
		},
		sharing: {
			public_models: false,
			public_knowledge: false,
			public_prompts: false,
			public_tools: false
		},
		chat: {
			controls: true,
			file_upload: true,
			delete: true,
			edit: true,
			share: true,
			export: true,
			stt: true,
			tts: true,
			call: true,
			multiple_models: true,
			temporary: true,
			temporary_enforced: false
		},
		features: {
			direct_tool_servers: false,
			web_search: true,
			image_generation: true,
			code_interpreter: true,
			notes: true
		}
	};

	export let permissions = {};

	// Reactive statement to ensure all fields are present in `permissions`
	$: {
		permissions = fillMissingProperties(permissions, defaultPermissions);
	}

	function fillMissingProperties(obj: any, defaults: any) {
		return {
			...defaults,
			...obj,
			workshop: { ...defaults.workshop, ...obj.workshop },
			sharing: { ...defaults.sharing, ...obj.sharing },
			chat: { ...defaults.chat, ...obj.chat },
			features: { ...defaults.features, ...obj.features }
		};
	}

	onMount(() => {
		permissions = fillMissingProperties(permissions, defaultPermissions);
	});
</script>

<div>
	<!-- <div>
		<div style="--mb:0.5rem; --size:0.8rem; --weight:500">{$i18n.t('Model Permissions')}</div>

		<div style="--mb:0.5rem">
			<div style="--d:flex; --jc:space-between; --ai:center; --size:0.6rem; --pr:0.5rem">
				<div style="--size:0.6rem; --weight:500">{$i18n.t('Model Filtering')}</div>

				<Switch bind:state={permissions.model.filter} />
			</div>
		</div>

		{#if permissions.model.filter}
			<div style="--mb:0.5rem">
				<div style="--g:0.4rem">
					<div style="--d:flex; --fd:column; --w:100%">
						<div style="--mb:0.2rem; --d:flex; --jc:space-between">
							<div style="--size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Model IDs')}</div>
						</div>

						{#if model_ids.length > 0}
							<div style="--d:flex; --fd:column">
								{#each model_ids as modelId, modelIdx}
									<div style="--d:flex; --g:0.5rem; --w:100%; --jc:space-between; --ai:center">
										<div style="--size:0.8rem; --fx:1 1 0%; --radius:0.5rem">
											{modelId}
										</div>
										<div style="--fs:0">
											<button
												type="button"
												on:click={() => {
													model_ids = model_ids.filter((_, idx) => idx !== modelIdx);
												}}
											>
												<Minus strokeWidth="2" className="size-3.5" />
											</button>
										</div>
									</div>
								{/each}
							</div>
						{:else}
							<div style="--c:var(--color-gray-500); --size:0.6rem; --ta:center; --py:0.5rem; --px:2.5rem">
								{$i18n.t('No model IDs')}
							</div>
						{/if}
					</div>
				</div>
				<hr style="--bc:var(--color-gray-100); --dark-bc:rgb(78 78 78 / 0.1); --mt:0.625rem; --mb:0.2rem; --w:100%" />

				<div style="--d:flex; --ai:center">
					<select
						style="--w:100%; --py:0.2rem; --size:0.8rem; --radius:0.5rem; --bgc:transparent; --oe:none"
	class="{selectedModelId
							? ''
							: 'text-gray-500'} placeholder:text-gray-300 dark:placeholder:text-gray-700"
						bind:value={selectedModelId}
					>
						<option value="">{$i18n.t('Select a model')}</option>
						{#each $models.filter((m) => m?.owned_by !== 'arena') as model}
							<option value={model.id} style="--bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-700)">{model.name}</option>
						{/each}
					</select>

					<div>
						<button
							type="button"
							on:click={() => {
								if (selectedModelId && !permissions.model.model_ids.includes(selectedModelId)) {
									permissions.model.model_ids = [...permissions.model.model_ids, selectedModelId];
									selectedModelId = '';
								}
							}}
						>
							<Plus className="size-3.5" strokeWidth="2" />
						</button>
					</div>
				</div>
			</div>
		{/if}

		<div style="--g:0.2rem; --mb:0.6rem">
			<div class="">
				<div style="--d:flex; --jc:space-between; --ai:center; --size:0.6rem">
					<div style="--size:0.6rem; --weight:500">{$i18n.t('Default Model')}</div>
				</div>
			</div>

			<div style="--fx:1 1 0%; --mr:0.5rem">
				<select
					style="--w:100%; --bgc:transparent; --oe:none; --py:0.125rem; --size:0.8rem"
					bind:value={permissions.model.default_id}
					placeholder="Select a model"
				>
					<option value="" disabled selected>{$i18n.t('Select a model')}</option>
					{#each permissions.model.filter ? $models.filter( (model) => filterModelIds.includes(model.id) ) : $models.filter((model) => model.id) as model}
						<option value={model.id} style="--bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-700)">{model.name}</option>
					{/each}
				</select>
			</div>
		</div>
	</div>

	<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" /> -->

	<div>
		<div style="--mb:0.5rem; --size:0.8rem; --weight:500">{$i18n.t('Workshop Permissions')}</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Models Access')}
			</div>
			<Switch bind:state={permissions.workshop.models} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Knowledge Access')}
			</div>
			<Switch bind:state={permissions.workshop.knowledge} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Prompts Access')}
			</div>
			<Switch bind:state={permissions.workshop.prompts} />
		</div>

		<div class=" ">
			<Tooltip
				className=" flex w-full justify-between my-2 pr-2"
				content={$i18n.t(
					'Warning: Enabling this will allow users to upload arbitrary code on the server.'
				)}
				placement="top-start"
			>
				<div style="--as:center; --size:0.6rem; --weight:500">
					{$i18n.t('Tools Access')}
				</div>
				<Switch bind:state={permissions.workshop.tools} />
			</Tooltip>
		</div>
	</div>

	<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

	<div>
		<div style="--mb:0.5rem; --size:0.8rem; --weight:500">{$i18n.t('Sharing Permissions')}</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Models Public Sharing')}
			</div>
			<Switch bind:state={permissions.sharing.public_models} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Knowledge Public Sharing')}
			</div>
			<Switch bind:state={permissions.sharing.public_knowledge} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Prompts Public Sharing')}
			</div>
			<Switch bind:state={permissions.sharing.public_prompts} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Tools Public Sharing')}
			</div>
			<Switch bind:state={permissions.sharing.public_tools} />
		</div>
	</div>

	<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

	<div>
		<div style="--mb:0.5rem; --size:0.8rem; --weight:500">{$i18n.t('Chat Permissions')}</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Allow File Upload')}
			</div>

			<Switch bind:state={permissions.chat.file_upload} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Allow Chat Controls')}
			</div>

			<Switch bind:state={permissions.chat.controls} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Allow Chat System Prompt')}
			</div>

			<Switch bind:state={permissions.chat.system_prompt} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Allow Chat Delete')}
			</div>

			<Switch bind:state={permissions.chat.delete} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Allow Chat Edit')}
			</div>

			<Switch bind:state={permissions.chat.edit} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Allow Chat Share')}
			</div>

			<Switch bind:state={permissions.chat.share} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Allow Chat Export')}
			</div>

			<Switch bind:state={permissions.chat.export} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Allow Speech to Text')}
			</div>

			<Switch bind:state={permissions.chat.stt} />
		</div>
		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Allow Text to Speech')}
			</div>

			<Switch bind:state={permissions.chat.tts} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Allow Call')}
			</div>

			<Switch bind:state={permissions.chat.call} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Allow Multiple Models in Chat')}
			</div>

			<Switch bind:state={permissions.chat.multiple_models} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Allow Temporary Chat')}
			</div>

			<Switch bind:state={permissions.chat.temporary} />
		</div>

		{#if permissions.chat.temporary}
			<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
				<div style="--as:center; --size:0.6rem; --weight:500">
					{$i18n.t('Enforce Temporary Chat')}
				</div>

				<Switch bind:state={permissions.chat.temporary_enforced} />
			</div>
		{/if}
	</div>

	<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

	<div>
		<div style="--mb:0.5rem; --size:0.8rem; --weight:500">{$i18n.t('Features Permissions')}</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Direct Tool Servers')}
			</div>

			<Switch bind:state={permissions.features.direct_tool_servers} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Web Search')}
			</div>

			<Switch bind:state={permissions.features.web_search} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Image Generation')}
			</div>

			<Switch bind:state={permissions.features.image_generation} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Code Interpreter')}
			</div>

			<Switch bind:state={permissions.features.code_interpreter} />
		</div>

		<div style="--d:flex; --w:100%; --jc:space-between; --my:0.5rem; --pr:0.5rem">
			<div style="--as:center; --size:0.6rem; --weight:500">
				{$i18n.t('Notes')}
			</div>

			<Switch bind:state={permissions.features.notes} />
		</div>
	</div>
</div>
