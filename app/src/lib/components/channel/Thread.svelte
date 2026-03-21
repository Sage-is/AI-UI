<script lang="ts">
	import { goto } from '$app/navigation';
	import { getContext } from 'svelte';

	import { settings, socket, user } from '$lib/stores';

	import { getSpaceThreadMessages, sendMessage } from '$lib/apis/spaces';

	import XMark from '$lib/components/icons/XMark.svelte';
	import MessageInput from '../chat/MessageInput.svelte';
	import Messages from './Messages.svelte';
	import { onDestroy, tick } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let threadId = null;
	export let space = null;
	export let participants: { users: any[]; agents: any[] } = { users: [], agents: [] };

	export let onClose = () => {};

	let messages = null;
	let top = false;

	let prompt = '';
	let files = [];

	let typingUsers = [];
	let typingUsersTimeout = {};

	let messagesContainerElement = null;

	$: if (threadId) {
		initHandler();
	}

	const scrollToBottom = () => {
		messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
	};

	const initHandler = async () => {
		messages = null;
		top = false;

		prompt = '';
		files = [];

		typingUsers = [];
		typingUsersTimeout = {};

		if (space) {
			messages = await getSpaceThreadMessages(localStorage.token, space.id, threadId);

			if (messages.length < 50) {
				top = true;
			}

			await tick();
			scrollToBottom();
		} else {
			goto('/');
		}
	};

	const spaceEventHandler = async (event) => {
		console.debug(event);
		if (event.space_id === space.id) {
			const type = event?.data?.type ?? null;
			const data = event?.data?.data ?? null;

			if (type === 'message') {
				if ((data?.parent_id ?? null) === threadId) {
					if (messages) {
						// Skip if already added optimistically
						if (messages.find((m) => m.id === data.id)) return;
						messages = [data, ...messages];

						if (typingUsers.find((user) => user.id === event.user.id)) {
							typingUsers = typingUsers.filter((user) => user.id !== event.user.id);
						}
					}
				}
			} else if (type === 'message:update') {
				if (messages) {
					const idx = messages.findIndex((message) => message.id === data.id);

					if (idx !== -1) {
						messages[idx] = data;
					}
				}
			} else if (type === 'message:delete') {
				if (messages) {
					messages = messages.filter((message) => message.id !== data.id);
				}
			} else if (type.includes('message:reaction')) {
				if (messages) {
					const idx = messages.findIndex((message) => message.id === data.id);
					if (idx !== -1) {
						messages[idx] = data;
					}
				}
			} else if (type === 'typing' && event.message_id === threadId) {
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

		const res = await sendMessage(localStorage.token, space.id, {
			parent_id: threadId,
			content: messageContent,
			data: { files: files.length > 0 ? files : undefined }
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			prompt = '';
			files = [];
		}
	};

	const onChange = async () => {
		$socket?.emit('space-events', {
			space_id: space.id,
			message_id: threadId,
			data: {
				type: 'typing',
				data: {
					typing: true
				}
			}
		});
	};

	// Reactive socket registration — re-registers when socket becomes available
	$: if ($socket) {
		$socket.off('space-events', spaceEventHandler);
		$socket.on('space-events', spaceEventHandler);
	}

	onDestroy(() => {
		$socket?.off('space-events', spaceEventHandler);
	});
</script>

{#if space}
	<div style="--d:flex; --fd:column; --w:100%; --h:100%; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850)">
		<div style="--d:flex; --ai:center; --jc:space-between; --px:0.8rem; --pt:0.6rem">
			<div style="--weight:500; --size:1.125rem">Thread</div>

			<div>
				<button
					style="--c:var(--color-gray-500); --hvr-c:var(--color-gray-700); --dark-c:var(--color-gray-400); --hvr-dark-c:var(--color-gray-300); --p:0.5rem"
					on:click={() => {
						onClose();
					}}
				>
					<XMark />
				</button>
			</div>
		</div>

		<div style="--maxh:100%; --w:100%; --ofy:auto; --pt:0.6rem" bind:this={messagesContainerElement}>
			<Messages
				id={threadId}
				{space}
				{messages}
				{top}
				thread={true}
				onLoad={async () => {
					const newMessages = await getSpaceThreadMessages(
						localStorage.token,
						space.id,
						threadId,
						messages.length
					);

					messages = [...messages, ...newMessages];

					if (newMessages.length < 50) {
						top = true;
						return;
					}
				}}
			/>

			<div style="--pb:1rem; --px:0.625rem">
				{#if typingUsers.length > 0}
					<div style="--size:0.65rem; --px:1rem; --mb:0.25rem">
						<span style="--weight:500; --c:#000; --dark-c:#fff">
							{typingUsers.map((user) => user.name).join(', ')}
						</span>
						{$i18n.t('is typing...')}
					</div>
				{/if}

				<MessageInput
					bind:prompt
					bind:files
					placeholder={$i18n.t('Reply in thread')}
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
		</div>
	</div>
{/if}
