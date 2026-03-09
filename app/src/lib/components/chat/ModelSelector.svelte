<script lang="ts">
	import { models, showSettings, settings, user, mobile, config, temporaryChatEnabled } from '$lib/stores';
	import { onMount, tick, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import Selector from './ModelSelector/Selector.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Switch from '../common/Switch.svelte';
	import ChatBubbleOval from '../icons/ChatBubbleOval.svelte';

	import { updateUserSettings } from '$lib/apis/users';
	const i18n = getContext('i18n');

	export let selectedModels = [''];
	export let disabled = false;

	export let showSetDefault = true;

	const saveDefaultModel = async () => {
		const hasEmptyModel = selectedModels.filter((it) => it === '');
		if (hasEmptyModel.length) {
			toast.error($i18n.t('Choose a model before saving...'));
			return;
		}
		settings.set({ ...$settings, models: selectedModels });
		await updateUserSettings(localStorage.token, { ui: $settings });

		toast.success($i18n.t('Default model updated'));
	};

	const pinModelHandler = async (modelId) => {
		let pinnedModels = $settings?.pinnedModels ?? [];

		if (pinnedModels.includes(modelId)) {
			pinnedModels = pinnedModels.filter((id) => id !== modelId);
		} else {
			pinnedModels = [...new Set([...pinnedModels, modelId])];
		}

		settings.set({ ...$settings, pinnedModels: pinnedModels });
		await updateUserSettings(localStorage.token, { ui: $settings });
	};

	$: if (selectedModels.length > 0 && $models.length > 0) {
		selectedModels = selectedModels.map((model) =>
			$models.map((m) => m.id).includes(model) ? model : ''
		);
	}

	$: isAlreadyDefault = selectedModels.length === ($settings?.models ?? ['']).length &&
		selectedModels.every((m, i) => m === ($settings?.models ?? [''])[i]);

	$: showTemporaryChatControl = $user?.role === 'user'
		? ($user?.permissions?.chat?.temporary ?? true) &&
			!($user?.permissions?.chat?.temporary_enforced ?? false)
		: true;
</script>

<div style="--d:flex; --fd:column; --w:100%; --ai:flex-start">
	{#each selectedModels as selectedModel, selectedModelIdx}
		<div style="--d:flex; --w:100%"
	class="max-w-fit">
			<div style="--of:hidden; --w:100%">
				<div style="--maxw:100%"
	class="{($settings?.highContrastMode ?? false) ? 'm-1' : 'mr-1'}">
					<Selector
						id={`${selectedModelIdx}`}
						placeholder={$i18n.t('Select a model')}
						items={$models.map((model) => ({
							value: model.id,
							label: model.name,
							model: model
						}))}
						{pinModelHandler}
						bind:value={selectedModel}
					/>
				</div>
			</div>

			{#if $user?.role === 'admin' || ($user?.permissions?.chat?.multiple_models ?? true)}
				{#if selectedModelIdx === 0}
					<div
						style="--as:center; --mx:0.25rem; --translatey:-0.5px"
	class="disabled:text-gray-600 disabled:hover:text-gray-600"
					>
						<Tooltip content={$i18n.t('Add Model')}>
							<button
								class=" "
								{disabled}
								on:click={() => {
									selectedModels = [...selectedModels, ''];
								}}
								aria-label="Add Model"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="2"
									stroke="currentColor"
									style="--w:0.875rem; --h:0.875rem"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m6-6H6" />
								</svg>
							</button>
						</Tooltip>
					</div>
				{:else}
					<div
						style="--as:center; --mx:0.25rem; --translatey:-0.5px"
	class="disabled:text-gray-600 disabled:hover:text-gray-600"
					>
						<Tooltip content={$i18n.t('Remove Model')}>
							<button
								{disabled}
								on:click={() => {
									selectedModels.splice(selectedModelIdx, 1);
									selectedModels = selectedModels;
								}}
								aria-label="Remove Model"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="2"
									stroke="currentColor"
									style="--w:0.75rem; --h:0.75rem"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 12h-15" />
								</svg>
							</button>
						</Tooltip>
					</div>
				{/if}
			{/if}
		</div>
	{/each}
</div>

{#if showSetDefault}
	<div
		style="--pos:absolute; --ta:left; --mt:-0.6rem; --ml:0.4rem; --size:0.7rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400); {isAlreadyDefault ? '--d:none;' : ''}"
	class="font-primary"
	>
		<button on:click={saveDefaultModel}> {$i18n.t('Set as default')}</button>
	</div>
{/if}

{#if showTemporaryChatControl}
	<div style="--mt:0.25rem; --ml:0.25rem">
		<button
			style="--d:flex; --jc:space-between; --ai:center; --g:0.5rem; --size:0.7rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-400); --cur:pointer; --bgc:transparent; --oe:none"
			class="font-primary"
			on:click={async () => {
				temporaryChatEnabled.set(!$temporaryChatEnabled);
				await goto('/');
				const newChatButton = document.getElementById('new-chat-button');
				setTimeout(() => {
					newChatButton?.click();
				}, 0);
				if ($temporaryChatEnabled) {
					history.replaceState(null, '', '?temporary-chat=true');
				} else {
					history.replaceState(null, '', location.pathname);
				}
			}}
		>
			<div style="--d:flex; --g:0.375rem; --ai:center">
				<ChatBubbleOval className="size-3" strokeWidth="2.5" />
				{$i18n.t('Temporary Chat')}
			</div>
			<Switch state={$temporaryChatEnabled} />
		</button>
	</div>
{/if}
