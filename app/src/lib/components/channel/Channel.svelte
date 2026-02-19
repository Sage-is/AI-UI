<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { Pane, PaneGroup, PaneResizer } from 'paneforge';

	import { onDestroy, onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';

	import { chatId, showSidebar, socket, user } from '$lib/stores';
	import { getChannelById, getChannelMessages, sendMessage } from '$lib/apis/spaces';

	import Messages from './Messages.svelte';
	import MessageInput from './MessageInput.svelte';
	import Navbar from './Navbar.svelte';
	import Drawer from '../common/Drawer.svelte';
	import EllipsisVertical from '../icons/EllipsisVertical.svelte';
	import Thread from './Thread.svelte';

	export let id = '';

	let scrollEnd = true;
	let messagesContainerElement = null;

	let top = false;

	let channel = null;
	let messages = null;

	let threadId = null;

	let typingUsers = [];
	let typingUsersTimeout = {};

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

		typingUsers = [];
		typingUsersTimeout = {};

		channel = await getChannelById(localStorage.token, id).catch((error) => {
			return null;
		});

		if (channel) {
			messages = await getChannelMessages(localStorage.token, id, 0);

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
					messages = [data, ...messages];

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

	const submitHandler = async ({ content, data }) => {
		if (!content && (data?.files ?? []).length === 0) {
			return;
		}

		const res = await sendMessage(localStorage.token, id, { content: content, data: data }).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (res) {
			messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
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
		{$showSidebar ? '--maxw:calc(100% - 260px)' : ''}"
	id="channel-container"
>
	<PaneGroup direction="horizontal" style="--w:100%; --h:100%">
		<Pane defaultSize={50} minSize={50} style="--h:100%; --d:flex; --fd:column; --w:100%; --pos:relative">
			<Navbar {channel} />

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

			<div style="--pb:1rem; --px:0.625rem">
				<MessageInput
					id="root"
					{typingUsers}
					{onChange}
					onSubmit={submitHandler}
					{scrollToBottom}
					{scrollEnd}
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
				style="--pos:relative; --d:flex; --w:3px; --ai:center; --jc:center; --bgc:var(--color-gray-50, #f9f9f9); --dark-bgc:var(--color-gray-850, #262626)"
	class="bg-background group"
			>
				<div style="--z:10; --d:flex; --h:1.75rem; --w:1.25rem; --ai:center; --jc:center"
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
