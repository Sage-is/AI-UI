<script lang="ts">
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import { getTimeRange } from '$lib/utils';

	dayjs.extend(localizedFormat);

	export let chats = [];

	let chatList = null;

	const init = async () => {
		if (chats.length === 0) {
			chatList = [];
		} else {
			chatList = chats.map((chat) => ({
				...chat,
				time_range: getTimeRange(chat.updated_at)
			}));
		}
	};

	$: if (chats) {
		init();
	}
</script>

{#if chatList}
	<div style="--ta:left; --size:0.875rem; --w:100%; --mb:0.75rem">
		{#if chatList.length === 0}
			<div
				style="--size:0.75rem; --c:var(--color-gray-500, #9b9b9b); --dark-c:var(--color-gray-400, #b4b4b4); --ta:center; --px:1.25rem; --minh:5rem; --w:100%; --h:100%; --d:flex; --jc:center; --ai:center"
			>
				{$i18n.t('No chats found')}
			</div>
		{/if}

		{#each chatList as chat, idx (chat.id)}
			{#if (idx === 0 || (idx > 0 && chat.time_range !== chatList[idx - 1].time_range)) && chat?.time_range}
				<div
					style="--w:100%; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b); --dark-c:var(--color-gray-500, #9b9b9b); --weight:500; --pb:0.5rem; --px:0.5rem"
	class="{idx === 0
						? ''
						: 'pt-5'}"
				>
					{$i18n.t(chat.time_range)}
					<!-- localisation keys for time_range to be recognized from the i18next parser (so they don't get automatically removed):
							{$i18n.t('Today')}
							{$i18n.t('Yesterday')}
							{$i18n.t('Previous 7 days')}
							{$i18n.t('Previous 30 days')}
							{$i18n.t('January')}
							{$i18n.t('February')}
							{$i18n.t('March')}
							{$i18n.t('April')}
							{$i18n.t('May')}
							{$i18n.t('June')}
							{$i18n.t('July')}
							{$i18n.t('August')}
							{$i18n.t('September')}
							{$i18n.t('October')}
							{$i18n.t('November')}
							{$i18n.t('December')}
							-->
				</div>
			{/if}

			<a
				style="--w:100%; --d:flex; --jc:space-between; --ai:center; --radius:0.5rem; --size:0.875rem; --py:0.5rem; --px:0.75rem; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-850, #262626)"
				draggable="false"
				href={`/c/${chat.id}`}
				on:click={() => (show = false)}
			>
				<div style="text-overflow:ellipsis; --line-clamp:1; --w:100%; --fb-sm:60%">
					{chat?.title}
				</div>

				<div style="--d:none; --d-sm:flex; --fb-sm:40%; --ai:center; --jc:flex-end">
					<div style="--c:var(--color-gray-500, #9b9b9b); --dark-c:var(--color-gray-400, #b4b4b4); --size:0.75rem">
						{dayjs(chat?.updated_at * 1000).calendar()}
					</div>
				</div>
			</a>
		{/each}

		<!-- {#if !allChatsLoaded && loadHandler}
		<Loader
			on:visible={(e) => {
				if (!chatListLoading) {
					loadHandler();
				}
			}}
		>
			<div style="--w:100%; --d:flex; --jc:center; --py:0.25rem; --size:0.75rem; animation:pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; --ai:center; --g:0.5rem">
				<Spinner className=" size-4" />
				<div class=" ">Loading...</div>
			</div>
		</Loader>
	{/if} -->
	</div>
{/if}
