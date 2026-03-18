<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { models, config, toolServers, tools } from '$lib/stores';

	import { toast } from 'svelte-sonner';
	import { deleteSharedChatById, getChatById, shareChatById } from '$lib/apis/chats';
	import { copyToClipboard } from '$lib/utils';

	import Modal from '../common/Modal.svelte';
	import Link from '../icons/Link.svelte';
	import Collapsible from '../common/Collapsible.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	export let selectedToolIds = [];

	let selectedTools = [];

	$: selectedTools = ($tools ?? []).filter((tool) => selectedToolIds.includes(tool.id));

	const i18n = getContext('i18n');
</script>

<Modal bind:show size="md">
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300); --px:1.2rem; --pt:1rem; --pb:0.125rem">
			<div style="--size:1.125rem; --weight:500; --as:center">{$i18n.t('Available Tools')}</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		{#if selectedTools.length > 0}
			{#if $toolServers.length > 0}
				<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300); --px:1.2rem; --pb:0.2rem">
					<div style="--size:1rem; --weight:500; --as:center">{$i18n.t('Tools')}</div>
				</div>
			{/if}

			<div style="--px:1.2rem; --pb:0.6rem; --w:100%; --d:flex; --fd:column; --jc:center">
				<div style="--size:0.8rem; --dark-c:var(--color-gray-300); --mb:0.2rem">
					{#each selectedTools as tool}
						<Collapsible buttonClassName="w-full mb-0.5">
							<div>
								<div style="--size:0.8rem; --weight:500; --dark-c:var(--color-gray-100); --c:var(--color-gray-800)">
									{tool?.name}
								</div>

								{#if tool?.meta?.description}
									<div style="--size:0.6rem; --c:var(--color-gray-500)">
										{tool?.meta?.description}
									</div>
								{/if}
							</div>

							<!-- <div slot="content">
							{JSON.stringify(tool, null, 2)}
						</div> -->
						</Collapsible>
					{/each}
				</div>
			</div>
		{/if}

		{#if $toolServers.length > 0}
			<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300); --px:1.2rem; --pb:0.125rem">
				<div style="--size:1rem; --weight:500; --as:center">{$i18n.t('Tool Servers')}</div>
			</div>

			<div style="--px:1.2rem; --pb:1.2rem; --w:100%; --d:flex; --fd:column; --jc:center">
				<div style="--size:0.6rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300); --mb:0.5rem">
					{$i18n.t('Sage.is AI can use tools provided by any OpenAPI server.')} <br /><a
						style="--td:underline"
						href="https://github.com/open-webui/openapi-servers"
						target="_blank">{$i18n.t('Learn more about OpenAPI tool servers.')}</a
					>
				</div>
				<div style="--size:0.8rem; --dark-c:var(--color-gray-300); --mb:0.2rem">
					{#each $toolServers as toolServer}
						<Collapsible buttonClassName="w-full" chevron>
							<div>
								<div style="--size:0.8rem; --weight:500; --dark-c:var(--color-gray-100); --c:var(--color-gray-800)">
									{toolServer?.openapi?.info?.title} - v{toolServer?.openapi?.info?.version}
								</div>

								<div style="--size:0.6rem; --c:var(--color-gray-500)">
									{toolServer?.openapi?.info?.description}
								</div>

								<div style="--size:0.6rem; --c:var(--color-gray-500)">
									{toolServer?.url}
								</div>
							</div>

							<div slot="content">
								{#each toolServer?.specs ?? [] as tool_spec}
									<div style="--my:0.2rem">
										<div style="--weight:500; --c:var(--color-gray-800); --dark-c:var(--color-gray-100)">
											{tool_spec?.name}
										</div>

										<div>
											{tool_spec?.description}
										</div>
									</div>
								{/each}
							</div>
						</Collapsible>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</Modal>
