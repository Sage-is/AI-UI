<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { Pane, PaneGroup, PaneResizer } from 'paneforge';

	import { onDestroy, onMount, tick, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { chatId, showSidebar, socket, user, settings } from '$lib/stores';
	import { getChannelById, getChannelMessages, getChannelParticipants, sendMessage } from '$lib/apis/spaces';

	import Messages from './Messages.svelte';
	import MessageInput from '../chat/MessageInput.svelte';
	import Navbar from './Navbar.svelte';
	import Drawer from '../common/Drawer.svelte';
	import EllipsisVertical from '../icons/EllipsisVertical.svelte';
	import Thread from './Thread.svelte';

	const i18n = getContext('i18n');

	export let id = '';

	let scrollEnd = true;
	let messagesContainerElement = null;

	let top = false;

	let channel = null;
	let messages = null;

	let threadId = null;

	let prompt = '';
	let files = [];

	let typingUsers = [];
	let typingUsersTimeout = {};

	let thinkingAgents = [];
	let thinkingAgentsTimeout = {};

	let participants = { users: [], agents: [] };

	$: if (id) {
		initHandler();
	}

	const scrollToBottom = () => {
		if (messagesContainerElement) {
			messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
		}
	};

	const initHandler = async () => {
		top = false;
		messages = null;
		channel = null;
		threadId = null;

		prompt = '';
		files = [];

		typingUsers = [];
		typingUsersTimeout = {};
		thinkingAgents = [];
		thinkingAgentsTimeout = {};

		channel = await getChannelById(localStorage.token, id).catch((error) => {
			return null;
		});

		if (channel) {
			messages = await getChannelMessages(localStorage.token, id, 0);

			// Load participants for @mention autocomplete
			participants = await getChannelParticipants(localStorage.token, id).catch(() => ({
				users: [],
				agents: []
			}));

			if (messages) {
				scrollToBottom();

				if (messages.length < 50) {
					top = true;
				}
			}
		} else {
			goto('/');
		}
	};

	const channelEventHandler = async (event) => {
		if (event.channel_id === id) {
			const type = event?.data?.type ?? null;
			const data = event?.data?.data ?? null;

			if (type === 'message') {
				if ((data?.parent_id ?? null) === null) {
					// Skip if already added optimistically
					if (!messages.find((m) => m.id === data.id)) {
						messages = [data, ...messages];
					}

					if (typingUsers.find((user) => user.id === event.user.id)) {
						typingUsers = typingUsers.filter((user) => user.id !== event.user.id);
					}

					await tick();
					if (scrollEnd) {
						scrollToBottom();
					}
				}
			} else if (type === 'message:update') {
				const idx = messages.findIndex((message) => message.id === data.id);

				if (idx !== -1) {
					messages[idx] = data;
				}
			} else if (type === 'message:delete') {
				messages = messages.filter((message) => message.id !== data.id);
			} else if (type === 'message:reply') {
				const idx = messages.findIndex((message) => message.id === data.id);

				if (idx !== -1) {
					messages[idx] = data;
				}
			} else if (type.includes('message:reaction')) {
				const idx = messages.findIndex((message) => message.id === data.id);
				if (idx !== -1) {
					messages[idx] = data;
				}
			} else if (type === 'thinking') {
				const agentKey = data?.agent?.model_id || data?.agent?.name;
				if (data?.thinking) {
					if (!thinkingAgents.find((a) => (a.model_id || a.name) === agentKey)) {
						thinkingAgents = [...thinkingAgents, data.agent];
					}
					// Auto-clear after 30s safety net
					if (thinkingAgentsTimeout[agentKey]) {
						clearTimeout(thinkingAgentsTimeout[agentKey]);
					}
					thinkingAgentsTimeout[agentKey] = setTimeout(() => {
						thinkingAgents = thinkingAgents.filter(
							(a) => (a.model_id || a.name) !== agentKey
						);
					}, 30000);
				} else {
					thinkingAgents = thinkingAgents.filter(
						(a) => (a.model_id || a.name) !== agentKey
					);
					if (thinkingAgentsTimeout[agentKey]) {
						clearTimeout(thinkingAgentsTimeout[agentKey]);
					}
				}
			} else if (type === 'typing' && event.message_id === null) {
				if (event.user.id === $user?.id) {
					return;
				}

				typingUsers = data.typing
					? [
							...typingUsers,
							...(typingUsers.find((user) => user.id === event.user.id)
								? []
								: [
										{
											id: event.user.id,
											name: event.user.name
										}
									])
						]
					: typingUsers.filter((user) => user.id !== event.user.id);

				if (typingUsersTimeout[event.user.id]) {
					clearTimeout(typingUsersTimeout[event.user.id]);
				}

				typingUsersTimeout[event.user.id] = setTimeout(() => {
					typingUsers = typingUsers.filter((user) => user.id !== event.user.id);
				}, 5000);
			}
		}
	};

	const submitHandler = async (content) => {
		if (!content && files.length === 0) {
			return;
		}

		const messageContent = ($settings?.richTextInput ?? true)
			? content.replaceAll('\n\n', '\n')
			: content;

		const res = await sendMessage(localStorage.token, id, {
			content: messageContent,
			data: { files: files.length > 0 ? files : undefined }
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			// Optimistic add — message appears instantly
			messages = [
				{
					...res,
					user: {
						id: $user.id,
						name: $user.name,
						role: $user.role,
						profile_image_url: $user.profile_image_url
					},
					reply_count: 0,
					latest_reply_at: null,
					reactions: []
				},
				...messages
			];
			prompt = '';
			files = [];
			scrollToBottom();
		}
	};

	const onChange = async () => {
		$socket?.emit('channel-events', {
			channel_id: id,
			message_id: null,
			data: {
				type: 'typing',
				data: {
					typing: true
				}
			}
		});
	};

	let mediaQuery;
	let largeScreen = false;

	onMount(() => {
		if ($chatId) {
			chatId.set('');
		}

		$socket?.on('channel-events', channelEventHandler);

		mediaQuery = window.matchMedia('(min-width: 1024px)');

		const handleMediaQuery = async (e) => {
			if (e.matches) {
				largeScreen = true;
			} else {
				largeScreen = false;
			}
		};

		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);
	});

	onDestroy(() => {
		$socket?.off('channel-events', channelEventHandler);
	});
</script>

<svelte:head>
	<title>#{channel?.name ?? 'Channel'} • Sage.is AI</title>
</svelte:head>

<div
	style="--h:100vh; --maxh:100dvh; --tdn:200ms;
		--ttf:cubic-bezier(0.4, 0, 0.2, 1); --w:100%;
		--maxw:100%; --d:flex; --fd:column;
		{$showSidebar ? '--maxw:calc(100% - 280px)' : ''}"
	id="channel-container"
>
	<PaneGroup direction="horizontal" style="--w:100%; --h:100%">
		<Pane defaultSize={50} minSize={50} style="--h:100%; --d:flex; --fd:column; --w:100%; --pos:relative">
			<Navbar {channel} onRefresh={initHandler} />

			<div style="--fx:1 1 0%; --ofy:auto">
				{#if channel}
					<div
						style="--pb:0.625rem; --maxw:100%; --z:10; --w:100%; --h:100%; --pt:1.5rem; --fx:1 1 0%; --d:flex; --fd:column-reverse; --of:auto"
	class="scrollbar-hidden"
						id="messages-container"
						bind:this={messagesContainerElement}
						on:scroll={(e) => {
							scrollEnd = Math.abs(messagesContainerElement.scrollTop) <= 50;
						}}
					>
						{#key id}
							<Messages
								{channel}
								{messages}
								{top}
								onThread={(id) => {
									threadId = id;
								}}
								onLoad={async () => {
									const newMessages = await getChannelMessages(
										localStorage.token,
										id,
										messages.length
									);

									messages = [...messages, ...newMessages];

									if (newMessages.length < 50) {
										top = true;
										return;
									}
								}}
							/>
						{/key}
					</div>
				{/if}
			</div>

			<div style="--pb:0.5rem; --px:0.625rem">
				{#if thinkingAgents.length > 0 || typingUsers.length > 0}
					<div style="--size:0.65rem; --px:1rem; --mb:0.25rem">
						{#if thinkingAgents.length > 0}
							<div>
								<span style="--weight:500; --c:var(--color-blue-600); --dark-c:var(--color-blue-400)">
									{thinkingAgents.map((a) => a.name).join(', ')}
								</span>
								{$i18n.t('is thinking...')}
							</div>
						{/if}
						{#if typingUsers.length > 0}
							<div>
								<span style="--weight:500; --c:#000; --dark-c:#fff">
									{typingUsers.map((user) => user.name).join(', ')}
								</span>
								{$i18n.t('is typing...')}
							</div>
						{/if}
					</div>
				{/if}

				<MessageInput
					bind:prompt
					bind:files
					placeholder={$i18n.t('Send a Message')}
					selectedModels={['']}
					history={{}}
					stopResponse={() => {}}
					createMessagePair={() => {}}
					{onChange}
					on:submit={async (e) => {
						await submitHandler(e.detail);
					}}
				/>
			</div>
		</Pane>

		{#if !largeScreen}
			{#if threadId !== null}
				<Drawer
					show={threadId !== null}
					onClose={() => {
						threadId = null;
					}}
				>
					<div style="--h:100%"
	class="{threadId !== null ? ' h-screen  w-full' : 'px-6 py-4'}">
						<Thread
							{threadId}
							{channel}
							onClose={() => {
								threadId = null;
							}}
						/>
					</div>
				</Drawer>
			{/if}
		{:else if threadId !== null}
			<PaneResizer
				style="--pos:relative; --d:flex; --w:3px; --ai:center; --jc:center; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850)"
	class="bg-background group"
			>
				<div style="--z:10; --d:flex; --h:1.75rem; --w:1.2rem; --ai:center; --jc:center"
	class="rounded-xs">
					<EllipsisVertical className="size-4 invisible group-hover:visible" />
				</div>
			</PaneResizer>

			<Pane defaultSize={50} minSize={30} style="--h:100%; --w:100%">
				<div style="--h:100%; --w:100%; --shadow:5">
					<Thread
						{threadId}
						{channel}
						onClose={() => {
							threadId = null;
						}}
					/>
				</div>
			</Pane>
		{/if}
	</PaneGroup>
</div>
