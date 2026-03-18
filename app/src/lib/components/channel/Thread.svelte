<script lang="ts">
	import { goto } from '$app/navigation';

	import { socket, user } from '$lib/stores';

	import { getChannelThreadMessages, sendMessage } from '$lib/apis/spaces';

	import XMark from '$lib/components/icons/XMark.svelte';
	import MessageInput from './MessageInput.svelte';
	import Messages from './Messages.svelte';
	import { onDestroy, onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';

	export let threadId = null;
	export let channel = null;

	export let onClose = () => {};

	let messages = null;
	let top = false;

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

		typingUsers = [];
		typingUsersTimeout = {};

		if (channel) {
			messages = await getChannelThreadMessages(localStorage.token, channel.id, threadId);

			if (messages.length < 50) {
				top = true;
			}

			await tick();
			scrollToBottom();
		} else {
			goto('/');
		}
	};

	const channelEventHandler = async (event) => {
		console.debug(event);
		if (event.channel_id === channel.id) {
			const type = event?.data?.type ?? null;
			const data = event?.data?.data ?? null;

			if (type === 'message') {
				if ((data?.parent_id ?? null) === threadId) {
					if (messages) {
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

	const submitHandler = async ({ content, data }) => {
		if (!content && (data?.files ?? []).length === 0) {
			return;
		}

		const res = await sendMessage(localStorage.token, channel.id, {
			parent_id: threadId,
			content: content,
			data: data
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
	};

	const onChange = async () => {
		$socket?.emit('channel-events', {
			channel_id: channel.id,
			message_id: threadId,
			data: {
				type: 'typing',
				data: {
					typing: true
				}
			}
		});
	};

	onMount(() => {
		$socket?.on('channel-events', channelEventHandler);
	});

	onDestroy(() => {
		$socket?.off('channel-events', channelEventHandler);
	});
</script>

{#if channel}
	<div style="--d:flex; --fd:column; --w:100%; --h:100%; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850)">
		<div style="--d:flex; --ai:center; --jc:space-between; --px:0.875rem; --pt:0.6rem">
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
				{channel}
				{messages}
				{top}
				thread={true}
				onLoad={async () => {
					const newMessages = await getChannelThreadMessages(
						localStorage.token,
						channel.id,
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
				<MessageInput id={threadId} {typingUsers} {onChange} onSubmit={submitHandler} />
			</div>
		</div>
	</div>
{/if}
