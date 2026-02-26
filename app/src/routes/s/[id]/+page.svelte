<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import dayjs from 'dayjs';

	import { settings, chatId, WEBUI_NAME, models, config } from '$lib/stores';
	import { convertMessagesToHistory, createMessagesList } from '$lib/utils';

	import { getChatByShareId, cloneSharedChatById } from '$lib/apis/chats';

	import Messages from '$lib/components/chat/Messages.svelte';
	import Navbar from '$lib/components/layout/Navbar.svelte';

	import { getUserById, getUserSettings } from '$lib/apis/users';
	import { getModels } from '$lib/apis';
	import { toast } from 'svelte-sonner';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	const i18n = getContext('i18n');
	dayjs.extend(localizedFormat);

	let loaded = false;

	let autoScroll = true;
	let processing = '';
	let messagesContainerElement: HTMLDivElement;

	// let chatId = $page.params.id;
	let showModelSelector = false;
	let selectedModels = [''];

	let chat = null;
	let user = null;

	let title = '';
	let files = [];

	let messages = [];
	let history = {
		messages: {},
		currentId: null
	};

	$: messages = createMessagesList(history, history.currentId);

	$: if ($page.params.id) {
		(async () => {
			if (await loadSharedChat()) {
				await tick();
				loaded = true;
			} else {
				await goto('/');
			}
		})();
	}

	//////////////////////////
	// Web functions
	//////////////////////////

	const loadSharedChat = async () => {
		const userSettings = await getUserSettings(localStorage.token).catch((error) => {
			console.error(error);
			return null;
		});

		if (userSettings) {
			settings.set(userSettings.ui);
		} else {
			let localStorageSettings = {} as Parameters<(typeof settings)['set']>[0];

			try {
				localStorageSettings = JSON.parse(localStorage.getItem('settings') ?? '{}');
			} catch (e: unknown) {
				console.error('Failed to parse settings from localStorage', e);
			}

			settings.set(localStorageSettings);
		}

		await models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
		await chatId.set($page.params.id);
		chat = await getChatByShareId(localStorage.token, $chatId).catch(async (error) => {
			await goto('/');
			return null;
		});

		if (chat) {
			user = await getUserById(localStorage.token, chat.user_id).catch((error) => {
				console.error(error);
				return null;
			});

			const chatContent = chat.chat;

			if (chatContent) {
				console.log(chatContent);

				selectedModels =
					(chatContent?.models ?? undefined) !== undefined
						? chatContent.models
						: [chatContent.models ?? ''];
				history =
					(chatContent?.history ?? undefined) !== undefined
						? chatContent.history
						: convertMessagesToHistory(chatContent.messages);
				title = chatContent.title;

				autoScroll = true;
				await tick();

				if (messages.length > 0 && messages.at(-1)?.id && messages.at(-1)?.id in history.messages) {
					history.messages[messages.at(-1)?.id].done = true;
				}
				await tick();

				return true;
			} else {
				return null;
			}
		}
	};

	const cloneSharedChat = async () => {
		if (!chat) return;

		const res = await cloneSharedChatById(localStorage.token, chat.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			goto(`/c/${res.id}`);
		}
	};
</script>

<svelte:head>
	<title>
		{title
			? `${title.length > 30 ? `${title.slice(0, 30)}...` : title} • ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

{#if loaded}
	<div
		style="--h:100vh; --maxh:100dvh; --w:100%; --d:flex; --fd:column; --c:var(--color-gray-700); --dark-c:var(--color-gray-100); --bgc:#fff; --dark-bgc:var(--color-gray-900)"
	>
		<div style="--d:flex; --fd:column; --fx:1 1 auto; --jc:center; --pos:relative">
			<div style="--d:flex; --fd:column; --w:100%; --fx:1 1 auto; --of:auto; --h:0" id="messages-container">
				<div
					style="--pt:1.25rem; --px:0.5rem; --w:100%; --mx:auto"
	class="{($settings?.widescreenMode ?? null)
						? 'max-w-full'
						: 'max-w-5xl'}"
				>
					<div style="--px:0.75rem">
						<div style="--size:1.5rem; --weight:600; --line-clamp:1">
							{title}
						</div>

						<div style="--d:flex; --size:0.875rem; --jc:space-between; --ai:center; --mt:0.25rem">
							<div style="--c:var(--color-gray-400)">
								{dayjs(chat.chat.timestamp).format('LLL')}
							</div>
						</div>
					</div>
				</div>

				<div style="--h:100%; --w:100%; --d:flex; --fd:column; --py:0.5rem">
					<div style="--w:100%">
						<Messages
							className="h-full flex pt-4 pb-8 "
							{user}
							chatId={$chatId}
							readOnly={true}
							{selectedModels}
							{processing}
							bind:history
							bind:messages
							bind:autoScroll
							bottomPadding={files.length > 0}
							sendPrompt={() => {}}
							continueResponse={() => {}}
							regenerateResponse={() => {}}
						/>
					</div>
				</div>
			</div>

			<div
				style="--pos:absolute; --bottom:0; --right:0; --left:0; --d:flex; --jc:center; --w:100%; --bgi:linear-gradient(180deg, var(--tw-gradient-stops)); --tw-gradient-from:transparent; --tw-gradient-to:#fff; --dark-tw-gradient-to:var(--color-gray-900)"
			>
				<div style="--pb:1.25rem">
					<button
						style="--px:1rem; --py:0.5rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
						on:click={cloneSharedChat}
					>
						{$i18n.t('Clone Chat')}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
