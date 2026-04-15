<script lang="ts">
	import { marked } from 'marked';
	import Icon from '$lib/components/Icon.svelte';

	import { getContext, tick } from 'svelte';
	import dayjs from '$lib/dayjs';

	import { mobile, settings, user } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import type { Branding } from '$lib/apis/configs';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { copyToClipboard, sanitizeResponseContent } from '$lib/utils';
			import ModelItemMenu from './ModelItemMenu.svelte';
		import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let selectedModelIdx: number = -1;
	export let item: any = {};
	export let index: number = -1;
	export let value: string = '';

	export let unloadModelHandler: (modelValue: string) => void = () => {};
	export let pinModelHandler: (modelId: string) => void = () => {};

	export let branding: Branding | null = null;

	export let onClick: () => void = () => {};

	const copyLinkHandler = async (model) => {
		const baseUrl = window.location.origin;
		const res = await copyToClipboard(`${baseUrl}/?model=${encodeURIComponent(model.id)}`);

		if (res) {
			toast.success($i18n.t('Copied link to clipboard'));
		} else {
			toast.error($i18n.t('Failed to copy link'));
		}
	};

	let showMenu = false;
</script>

<button
	aria-roledescription="model-item"
	aria-label={item.label}
	style="--d:flex; --w:100%; --ta:left; --weight:500; --line-clamp:1; --us:none; --ai:center; --radius:var(--button-border-radius, 0.5rem); --py:0.5rem; --pl:0.6rem; --pr:0.4rem; --size:0.8rem; --bg:var(--white); --br: 1rem; --shadow:6; --oe:none; --tn:all 150ms cubic-bezier(0.4, 0, 0.2, 1); --tdn:75ms; --hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-800); --radius:0.5rem; --cur:pointer; --m:0.2em 0"
	class="group/item data-highlighted:bg-muted {index ===
	selectedModelIdx
		? 'bg-gray-100 dark:bg-gray-800 group-hover:bg-transparent'
		: ''}"
	data-arrow-selected={index === selectedModelIdx}
	data-value={item.value}
	on:click={() => {
		onClick();
	}}
>
	<div style="--d:flex; --fd:column; --fx:1 1 0%; --g:0.4rem">
		{#if (item?.model?.tags ?? []).length > 0}
			<div
				style="--d:flex; --g:0.125rem; --as:center; --ai:flex-start; --h:100%; --w:100%; --translatey:0.5px; --ofx:auto"
	class="scrollbar-none"
			>
				{#each item.model?.tags.sort((a, b) => a.name.localeCompare(b.name)) as tag}
					<Tooltip content={tag.name} className="flex-shrink-0">
						<div
							style="--size:0.6rem; --weight:700; --px:0.2rem; --radius:0.125rem; --tt:uppercase; --bgc:rgb(155 155 155 / 0.2); --c:var(--color-gray-700); --dark-c:var(--color-gray-200)"
						>
							{tag.name}
						</div>
					</Tooltip>
				{/each}
			</div>
		{/if}

		<div style="--d:flex; --ai:center; --g:0.5rem">
			<div style="--d:flex; --ai:center; --minw:fit-content">
				<Tooltip content={$user?.role === 'admin' ? (item?.value ?? '') : ''} placement="top-start">
					<img
						src={item.model?.info?.meta?.profile_image_url ??
							branding?.logo_url ?? `${WEBUI_BASE_URL}/static/icons/favicon.png`}
						alt="Model"
						style="--radius:9999px; --w:1.2rem; --h:1.2rem; --d:flex; --ai:center"
					/>
				</Tooltip>
			</div>

			<div style="--d:flex; --ai:center">
				<Tooltip content={`${item.label} (${item.value})`} placement="top-start">
					<div style="--line-clamp:1">
						{item.label}
					</div>
				</Tooltip>
			</div>

			<div style="--fs:0; --d:flex; --ai:center; --g:0.5rem">
				{#if item.model.owned_by === 'ollama'}
					{#if (item.model.ollama?.details?.parameter_size ?? '') !== ''}
						<div style="--d:flex; --ai:center; --translatey:0.5px">
							<Tooltip
								content={`${
									item.model.ollama?.details?.quantization_level
										? item.model.ollama?.details?.quantization_level + ' '
										: ''
								}${
									item.model.ollama?.size
										? `(${(item.model.ollama?.size / 1024 ** 3).toFixed(1)}GB)`
										: ''
								}`}
								className="self-end"
							>
								<span style="--size:0.6rem; --weight:500; --c:var(--color-gray-600); --dark-c:var(--color-gray-400); --line-clamp:1"
									>{item.model.ollama?.details?.parameter_size ?? ''}</span
								>
							</Tooltip>
						</div>
					{/if}
					{#if item.model.ollama?.expires_at && new Date(item.model.ollama?.expires_at * 1000) > new Date()}
						<div style="--d:flex; --ai:center; --translatey:0.5px; --px:0.125rem">
							<Tooltip
								content={`${$i18n.t('Unloads {{FROM_NOW}}', {
									FROM_NOW: dayjs(item.model.ollama?.expires_at * 1000).fromNow()
								})}`}
								className="self-end"
							>
								<div style="--d:flex; --ai:center">
									<span style="--pos:relative; --d:flex; --w:0.5rem; --h:0.5rem">
										<span
											style="animation:ping 1s cubic-bezier(0, 0, 0.2, 1) infinite; --pos:absolute; --d:inline-flex; --h:100%; --w:100%; --radius:9999px; --bgc:#4ade80; --op:0.75"
										/>
										<span style="--pos:relative; --d:inline-flex; --radius:9999px; --w:0.5rem; --h:0.5rem; --bgc:#22c55e" />
									</span>
								</div>
							</Tooltip>
						</div>
					{/if}
				{/if}

				<!-- {JSON.stringify(item.info)} -->

				{#if item.model?.direct}
					<Tooltip content={`${$i18n.t('Direct')}`}>
						<div style="--translatey:1px">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								style="--w:0.6rem; --h:0.6rem"
							>
								<path
									fill-rule="evenodd"
									d="M2 2.75A.75.75 0 0 1 2.75 2C8.963 2 14 7.037 14 13.25a.75.75 0 0 1-1.5 0c0-5.385-4.365-9.75-9.75-9.75A.75.75 0 0 1 2 2.75Zm0 4.5a.75.75 0 0 1 .75-.75 6.75 6.75 0 0 1 6.75 6.75.75.75 0 0 1-1.5 0C8 10.35 5.65 8 2.75 8A.75.75 0 0 1 2 7.25ZM3.5 11a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					</Tooltip>
				{:else if item.model.connection_type === 'external'}
					<Tooltip content={`${$i18n.t('External')}`}>
						<div style="--translatey:1px">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								style="--w:0.6rem; --h:0.6rem"
							>
								<path
									fill-rule="evenodd"
									d="M8.914 6.025a.75.75 0 0 1 1.06 0 3.5 3.5 0 0 1 0 4.95l-2 2a3.5 3.5 0 0 1-5.396-4.402.75.75 0 0 1 1.251.827 2 2 0 0 0 3.085 2.514l2-2a2 2 0 0 0 0-2.828.75.75 0 0 1 0-1.06Z"
									clip-rule="evenodd"
								/>
								<path
									fill-rule="evenodd"
									d="M7.086 9.975a.75.75 0 0 1-1.06 0 3.5 3.5 0 0 1 0-4.95l2-2a3.5 3.5 0 0 1 5.396 4.402.75.75 0 0 1-1.251-.827 2 2 0 0 0-3.085-2.514l-2 2a2 2 0 0 0 0 2.828.75.75 0 0 1 0 1.06Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					</Tooltip>
				{/if}

				{#if item.model?.info?.meta?.description}
					<Tooltip
						content={`${marked.parse(
							sanitizeResponseContent(item.model?.info?.meta?.description).replaceAll('\n', '<br>')
						)}`}
					>
						<div style="--translatey:1px">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								style="--w:1rem; --h:1rem"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"
								/>
							</svg>
						</div>
					</Tooltip>
				{/if}
			</div>
		</div>
	</div>

	<div style="--ml:auto; --pl:0.5rem; --pr:0.2rem; --d:flex; --ai:center; --g:0.4rem; --fs:0">
		{#if $user?.role === 'admin' && item.model.owned_by === 'ollama' && item.model.ollama?.expires_at && new Date(item.model.ollama?.expires_at * 1000) > new Date()}
			<Tooltip
				content={`${$i18n.t('Eject')}`}
				className="flex-shrink-0 group-hover/item:opacity-100 opacity-0 "
			>
				<button
					style="--d:flex"
					on:click={(e) => {
						e.preventDefault();
						e.stopPropagation();
						unloadModelHandler(item.value);
					}}
				>
					<Icon name="arrow-up-tray" className="size-3" />
				</button>
			</Tooltip>
		{/if}

		<ModelItemMenu
			bind:show={showMenu}
			model={item.model}
			{pinModelHandler}
			copyLinkHandler={() => {
				copyLinkHandler(item.model);
			}}
		>
			<button
				style="--d:flex"
				on:click={(e) => {
					e.preventDefault();
					e.stopPropagation();
					showMenu = !showMenu;
				}}
			>
				<Icon name="ellipsis-horizontal" />
			</button>
		</ModelItemMenu>

		{#if value === item.value}
			<div>
				<Icon name="check" className="size-3" />
			</div>
		{/if}
	</div>
</button>
