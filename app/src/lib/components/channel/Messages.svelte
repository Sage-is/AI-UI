<script lang="ts">
	import { toast } from 'svelte-sonner';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import isToday from 'dayjs/plugin/isToday';
	import isYesterday from 'dayjs/plugin/isYesterday';

	dayjs.extend(relativeTime);
	dayjs.extend(isToday);
	dayjs.extend(isYesterday);
	import { tick, getContext, onMount, createEventDispatcher } from 'svelte';

	import { settings, user } from '$lib/stores';

	import Message from './Messages/Message.svelte';
	import Loader from '../common/Loader.svelte';
	import Spinner from '../common/Spinner.svelte';
	import { addReaction, deleteMessage, removeReaction, updateMessage } from '$lib/apis/spaces';

	const i18n = getContext('i18n');

	export let id = null;
	export let channel = null;
	export let messages = [];
	export let top = false;
	export let thread = false;

	export let onLoad: Function = () => {};
	export let onThread: Function = () => {};

	let messagesLoading = false;

	const loadMoreMessages = async () => {
		// scroll slightly down to disable continuous loading
		const element = document.getElementById('messages-container');
		element.scrollTop = element.scrollTop + 100;

		messagesLoading = true;

		await onLoad();

		await tick();
		messagesLoading = false;
	};
</script>

{#if messages}
	{@const messageList = messages.slice().reverse()}
	<div>
		{#if !top}
			<Loader
				on:visible={(e) => {
					console.info('visible');
					if (!messagesLoading) {
						loadMoreMessages();
					}
				}}
			>
				<div style="--w:100%; --d:flex; --jc:center; --py:0.25rem; --size:0.75rem; animation:pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; --ai:center; --g:0.5rem">
					<Spinner className=" size-4" />
					<div class=" ">Loading...</div>
				</div>
			</Loader>
		{:else if !thread}
			<div
				style="--px:1.25rem; --mx:auto"
	class="{($settings?.widescreenMode ?? null) ? 'max-w-full' : 'max-w-5xl'}"
			>
				{#if channel}
					<div style="--d:flex; --fd:column; --g:0.375rem; --pb:1.25rem; --pt:2.5rem">
						<div style="--size:1.5rem; --weight:500; --tt:capitalize">{channel.name}</div>

						<div style="--c:var(--color-gray-500)">
							{$i18n.t(
								'This channel was created on {{createdAt}}. This is the very beginning of the {{channelName}} channel.',
								{
									createdAt: dayjs(channel.created_at / 1000000).format('MMMM D, YYYY'),
									channelName: channel.name
								}
							)}
						</div>
					</div>
				{:else}
					<div style="--d:flex; --jc:center; --size:0.75rem; --ai:center; --g:0.5rem; --py:1.25rem">
						<div class=" ">Start of the channel</div>
					</div>
				{/if}

				{#if messageList.length > 0}
					<hr style="--bc:var(--color-gray-50); --dark-bc:rgb(78 78 78 / 0.2); --py:0.625rem; --w:100%" />
				{/if}
			</div>
		{/if}

		{#each messageList as message, messageIdx (id ? `${id}-${message.id}` : message.id)}
			<Message
				{message}
				{thread}
				showUserProfile={messageIdx === 0 ||
					messageList.at(messageIdx - 1)?.user_id !== message.user_id}
				onDelete={() => {
					messages = messages.filter((m) => m.id !== message.id);

					const res = deleteMessage(localStorage.token, message.channel_id, message.id).catch(
						(error) => {
							toast.error(`${error}`);
							return null;
						}
					);
				}}
				onEdit={(content) => {
					messages = messages.map((m) => {
						if (m.id === message.id) {
							m.content = content;
						}
						return m;
					});

					const res = updateMessage(localStorage.token, message.channel_id, message.id, {
						content: content
					}).catch((error) => {
						toast.error(`${error}`);
						return null;
					});
				}}
				onThread={(id) => {
					onThread(id);
				}}
				onReaction={(name) => {
					if (
						(message?.reactions ?? [])
							.find((reaction) => reaction.name === name)
							?.user_ids?.includes($user?.id) ??
						false
					) {
						messages = messages.map((m) => {
							if (m.id === message.id) {
								const reaction = m.reactions.find((reaction) => reaction.name === name);

								if (reaction) {
									reaction.user_ids = reaction.user_ids.filter((id) => id !== $user?.id);
									reaction.count = reaction.user_ids.length;

									if (reaction.count === 0) {
										m.reactions = m.reactions.filter((r) => r.name !== name);
									}
								}
							}
							return m;
						});

						const res = removeReaction(
							localStorage.token,
							message.channel_id,
							message.id,
							name
						).catch((error) => {
							toast.error(`${error}`);
							return null;
						});
					} else {
						messages = messages.map((m) => {
							if (m.id === message.id) {
								if (m.reactions) {
									const reaction = m.reactions.find((reaction) => reaction.name === name);

									if (reaction) {
										reaction.user_ids.push($user?.id);
										reaction.count = reaction.user_ids.length;
									} else {
										m.reactions.push({
											name: name,
											user_ids: [$user?.id],
											count: 1
										});
									}
								}
							}
							return m;
						});

						const res = addReaction(localStorage.token, message.channel_id, message.id, name).catch(
							(error) => {
								toast.error(`${error}`);
								return null;
							}
						);
					}
				}}
			/>
		{/each}

		<div style="--pb:1.5rem" />
	</div>
{/if}
