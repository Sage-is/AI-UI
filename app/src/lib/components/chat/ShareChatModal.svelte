<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { models, config } from '$lib/stores';

	import { toast } from 'svelte-sonner';
	import { deleteSharedChatById, getChatById, shareChatById } from '$lib/apis/chats';
	import { copyToClipboard } from '$lib/utils';

	import Modal from '../common/Modal.svelte';
	import Link from '../icons/Link.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let chatId;

	let chat = null;
	let shareUrl = null;
	const i18n = getContext('i18n');

	const shareLocalChat = async () => {
		const _chat = chat;

		const sharedChat = await shareChatById(localStorage.token, chatId);
		shareUrl = `${window.location.origin}/s/${sharedChat.id}`;
		console.log(shareUrl);
		chat = await getChatById(localStorage.token, chatId);

		return shareUrl;
	};

	const shareChat = async () => {
		const _chat = chat.chat;
		console.log('share', _chat);

		toast.success($i18n.t('Redirecting you to Sage.is AI Community'));
		const url = 'https://sage.is';
		// const url = 'http://localhost:5173';

		const tab = await window.open(`${url}/chats/upload`, '_blank');
		window.addEventListener(
			'message',
			(event) => {
				if (event.origin !== url) return;
				if (event.data === 'loaded') {
					tab.postMessage(
						JSON.stringify({
							chat: _chat,
							models: $models.filter((m) => _chat.models.includes(m.id))
						}),
						'*'
					);
				}
			},
			false
		);
	};

	export let show = false;

	const isDifferentChat = (_chat) => {
		if (!chat) {
			return true;
		}
		if (!_chat) {
			return false;
		}
		return chat.id !== _chat.id || chat.share_id !== _chat.share_id;
	};

	$: if (show) {
		(async () => {
			if (chatId) {
				const _chat = await getChatById(localStorage.token, chatId);
				if (isDifferentChat(_chat)) {
					chat = _chat;
				}
			} else {
				chat = null;
				console.log(chat);
			}
		})();
	}
</script>

<Modal bind:show size="md">
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300, #cdcdcd); --px:1.25rem; --pt:1rem; --pb:0.125rem">
			<div style="--size:1.125rem; --weight:500; --as:center">{$i18n.t('Share Chat')}</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		{#if chat}
			<div style="--px:1.25rem; --pt:1rem; --pb:1.25rem; --w:100%; --d:flex; --fd:column; --jc:center">
				<div style="--size:0.875rem; --dark-c:var(--color-gray-300, #cdcdcd); --mb:0.25rem">
					{#if chat.share_id}
						<a href="/s/{chat.share_id}" target="_blank"
							>{$i18n.t('You have shared this chat')}
							<span style="--td:underline">{$i18n.t('before')}</span>.</a
						>
						{$i18n.t('Click here to')}
						<button
							style="--td:underline"
							on:click={async () => {
								const res = await deleteSharedChatById(localStorage.token, chatId);

								if (res) {
									chat = await getChatById(localStorage.token, chatId);
								}
							}}
							>{$i18n.t('delete this link')}
						</button>
						{$i18n.t('and create a new shared link.')}
					{:else}
						{$i18n.t(
							"Messages you send after creating your link won't be shared. Users with the URL will be able to view the shared chat."
						)}
					{/if}
				</div>

				<div style="--d:flex; --jc:flex-end">
					<div style="--d:flex; --fd:column; --ai:flex-end; --g:0.25rem; --mt:0.75rem">
						<div style="--d:flex; --g:0.25rem">
							{#if $config?.features.enable_community_sharing}
								<button
									style="--as:center; --d:flex; --ai:center; --g:0.25rem; --px:0.875rem; --py:0.5rem; --size:0.875rem; --weight:500; --bgc:var(--color-gray-100, #ececec); --hvr-bgc:var(--color-gray-200, #e3e3e3); --c:var(--color-gray-800, #333); --dark-bgc:var(--color-gray-850, #262626); --dark-c:#fff; --hvr-dark-bgc:var(--color-gray-800, #333); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
									type="button"
									on:click={() => {
										shareChat();
										show = false;
									}}
								>
									{$i18n.t('Share to Sage.is AI Community')}
								</button>
							{/if}

							<button
								style="--as:center; --d:flex; --ai:center; --g:0.25rem; --px:0.875rem; --py:0.5rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900, #171717); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100, #ececec); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
								type="button"
								id="copy-and-share-chat-button"
								on:click={async () => {
									const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);

									if (isSafari) {
										// Oh, Safari, you're so special, let's give you some extra love and attention
										console.log('isSafari');

										const getUrlPromise = async () => {
											const url = await shareLocalChat();
											return new Blob([url], { type: 'text/plain' });
										};

										navigator.clipboard
											.write([
												new ClipboardItem({
													'text/plain': getUrlPromise()
												})
											])
											.then(() => {
												console.log('Async: Copying to clipboard was successful!');
												return true;
											})
											.catch((error) => {
												console.error('Async: Could not copy text: ', error);
												return false;
											});
									} else {
										copyToClipboard(await shareLocalChat());
									}

									toast.success($i18n.t('Copied shared chat URL to clipboard!'));
									show = false;
								}}
							>
								<Link />

								{#if chat.share_id}
									{$i18n.t('Update and Copy Link')}
								{:else}
									{$i18n.t('Copy Link')}
								{/if}
							</button>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>
</Modal>
