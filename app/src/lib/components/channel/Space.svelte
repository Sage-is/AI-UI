<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { Pane, PaneGroup, PaneResizer } from 'paneforge';

	import { onDestroy, onMount, tick, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { chatId, showSidebar, socket, user, settings } from '$lib/stores';
	import { getSpaceById, getSpaceMessages, getSpaceParticipants, sendMessage } from '$lib/apis/spaces';

	import Messages from './Messages.svelte';
	import MessageInput from '../chat/MessageInput.svelte';
	import Navbar from './Navbar.svelte';
	import Drawer from '../common/Drawer.svelte';
	import EllipsisVertical from '../icons/EllipsisVertical.svelte';
	import Thread from './Thread.svelte';
	import IndicatorStack from './IndicatorStack.svelte';

	const i18n = getContext('i18n');

	/** The space ID from the route parameter. */
	export let id = '';

	let scrollEnd = true;
	let messagesContainerElement = null;

	let top = false;

	/** Current space data (loaded from API). */
	let space = null;
	let messages = null;

	let threadId = null;

	let prompt = '';
	let files = [];

	let typingUsers = [];
	let typingUsersTimeout = {};

	let thinkingAgents = [];
	let thinkingAgentsTimeout = {};

	/** Participants (users + agents) for @mention autocomplete. */
	let participants = { users: [], agents: [] };

	$: if (id) {
		initHandler();
	}

	/** Scroll to the newest messages. In column-reverse layout, scrollTop = 0 is the visual bottom. */
	const scrollToBottom = () => {
		if (messagesContainerElement) {
			messagesContainerElement.scrollTop = 0;
		}
	};

	/** Load space data, messages, and participants from the API. */
	const initHandler = async () => {
		top = false;
		messages = null;
		space = null;
		threadId = null;

		prompt = '';
		files = [];

		typingUsers = [];
		typingUsersTimeout = {};
		thinkingAgents = [];
		thinkingAgentsTimeout = {};

		space = await getSpaceById(localStorage.token, id).catch((error) => {
			return null;
		});

		if (space) {
			messages = await getSpaceMessages(localStorage.token, id, 0);

			// Load participants for @mention autocomplete
			// TODO: Show a user-facing error (toast or inline alert) when participant
			// loading fails, instead of silently falling back to empty lists.
			// The fallback keeps the space functional but hides the failure from the user.
			participants = await getSpaceParticipants(localStorage.token, id).catch((err) => {
				console.error('[Space] Failed to load participants:', err);
				return { users: [], agents: [] };
			});

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

	/**
	 * Handle real-time events for this space (new messages, edits, reactions, typing, etc.).
	 */
	const spaceEventHandler = async (event) => {
		if (event.space_id === id) {
			const type = event?.data?.type ?? null;
			const data = event?.data?.data ?? null;

			if (type === 'message') {
				if ((data?.parent_id ?? null) === null) {
					// Deduplicate — skip if already in the list
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
					// Safety net: auto-clear if backend never sends thinking:false.
					// 60s allows for slower models (was 30s, too aggressive).
					if (thinkingAgentsTimeout[agentKey]) {
						clearTimeout(thinkingAgentsTimeout[agentKey]);
					}
					thinkingAgentsTimeout[agentKey] = setTimeout(() => {
						thinkingAgents = thinkingAgents.filter(
							(a) => (a.model_id || a.name) !== agentKey
						);
					}, 120000);
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

	/** Post a message to the space. Input is cleared immediately; the socket event adds the message to the list. */
	const submitHandler = async (content) => {
		if (!content && files.length === 0) {
			return;
		}

		const messageContent = ($settings?.richTextInput ?? true)
			? content.replaceAll('\n\n', '\n')
			: content;

		// Capture files before clearing input for responsive UX
		const messageFiles = files.length > 0 ? files : undefined;
		prompt = '';
		files = [];

		await sendMessage(localStorage.token, id, {
			content: messageContent,
			data: { files: messageFiles }
		}).catch((error) => {
			toast.error(`${error}`);
		});

		// Socket event (spaceEventHandler) adds the message and scrolls.
		// No optimistic add needed — the socket event arrives nearly instantly
		// (backend emits it before returning the HTTP response).
	};

	/** Emit a typing indicator to the space. */
	const onChange = async () => {
		$socket?.emit('space-events', {
			space_id: id,
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

	// Reactive socket registration — re-registers when socket becomes available.
	$: if ($socket) {
		$socket.off('space-events', spaceEventHandler);
		$socket.on('space-events', spaceEventHandler);
	}

	onMount(() => {
		if ($chatId) {
			chatId.set('');
		}

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
		$socket?.off('space-events', spaceEventHandler);
	});
</script>

<svelte:head>
	<title>#{space?.name ?? 'Space'} • Sage.is AI</title>
</svelte:head>

<div
	style="--h:100vh; --maxh:100dvh; --tdn:200ms;
		--ttf:cubic-bezier(0.4, 0, 0.2, 1); --w:100%;
		--maxw:100%; --d:flex; --fd:column;
		{$showSidebar ? '--maxw:calc(100% - 280px)' : ''}"
	id="space-container"
>
	<PaneGroup direction="horizontal" style="--w:100%; --h:100%">
		<Pane defaultSize={50} minSize={50} style="--h:100%; --d:flex; --fd:column; --w:100%; --pos:relative">
				<Navbar {space} onRefresh={initHandler} />

			<div style="--fx:1 1 0%; --ofy:auto">
				{#if space}
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
								{space}
								{messages}
								{top}
								onThread={(id) => {
									threadId = id;
								}}
								onLoad={async () => {
									const newMessages = await getSpaceMessages(
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
				<IndicatorStack {thinkingAgents} {typingUsers} />

				<MessageInput
					bind:prompt
					bind:files
					placeholder={$i18n.t('Send a Message')}
					selectedModels={['']}
					history={{}}
					voiceModeEnabled={false}
					spaceParticipants={participants}
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
							{space}
							{participants}
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
						{space}
						{participants}
						onClose={() => {
							threadId = null;
						}}
					/>
				</div>
			</Pane>
		{/if}
	</PaneGroup>
</div>
