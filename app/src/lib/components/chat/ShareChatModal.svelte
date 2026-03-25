<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { models, config, sharedByMeChats, sharedWithMeChats } from '$lib/stores';

	import { toast } from 'svelte-sonner';
	import { deleteSharedChatById, getChatById, shareChatById } from '$lib/apis/chats';
	import { shareChatWithTargets, getChatShareTargets, getChatsSharedByMe, getChatsSharedWithMe } from '$lib/apis/chat-shares';
	import { copyToClipboard } from '$lib/utils';

	import Modal from '../common/Modal.svelte';
	import Link from '../icons/Link.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ShareTargetPicker from './ShareTargetPicker.svelte';
	import ShareTargetList from './ShareTargetList.svelte';

	export let chatId;

	let chat = null;
	let shareUrl = null;
	let selectedTargets = [];
	let existingTargets = [];
	let sharing = false;
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

	const shareWithTargets = async () => {
		if (selectedTargets.length === 0) return;
		sharing = true;
		try {
			await shareChatWithTargets(localStorage.token, chatId, selectedTargets);
			toast.success($i18n.t('Chat shared successfully'));
			selectedTargets = [];
			await loadExistingTargets();
			await refreshSidebarShares();
		} catch (err) {
			toast.error(err?.detail ?? $i18n.t('Failed to share chat'));
		}
		sharing = false;
	};

	const refreshSidebarShares = async () => {
		try { sharedByMeChats.set(await getChatsSharedByMe(localStorage.token)); } catch {}
		try { sharedWithMeChats.set(await getChatsSharedWithMe(localStorage.token)); } catch {}
	};

	const loadExistingTargets = async () => {
		try {
			existingTargets = await getChatShareTargets(localStorage.token, chatId);
		} catch {
			existingTargets = [];
		}
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
				await loadExistingTargets();
			} else {
				chat = null;
				existingTargets = [];
				console.log(chat);
			}
		})();
	}
</script>

<Modal bind:show size="md">
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300); --px:1.2rem; --pt:1rem; --pb:0.5rem">
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
			<div style="--px:1.2rem; --pb:1.2rem; --d:flex; --fd:column; --g:0.2rem">
				<!-- Link sharing section -->
				<details open>
					<summary style="--cur:pointer; --d:flex; --ai:center; --g:0.5rem; --py:0.5rem; --size:0.8125rem; --weight:600; --c:var(--color-gray-700); --dark-c:var(--color-gray-300); --us:none; --ls:normal">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" style="--w:0.8rem; --h:0.8rem">
							<path stroke-linecap="round" stroke-linejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
						</svg>
						{$i18n.t('Link')}
					</summary>
					<div style="--pt:0.2rem; --pb:0.5rem; --pl:1.375rem">
						<div style="--size:0.8rem; --dark-c:var(--color-gray-300); --mb:0.2rem">
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
							<div style="--d:flex; --fd:column; --ai:flex-end; --g:0.2rem; --mt:0.6rem">
								<div style="--d:flex; --g:0.2rem">
									{#if $config?.features.enable_community_sharing}
										<button
											style="--as:center; --d:flex; --ai:center; --g:0.2rem; --px:0.8rem; --py:0.5rem; --size:0.8rem; --weight:500; --bgc:var(--color-gray-100); --hvr-bgc:var(--color-gray-200); --c:var(--color-gray-800); --dark-bgc:var(--color-gray-850); --dark-c:#fff; --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
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
										style="--as:center; --d:flex; --ai:center; --g:0.2rem; --px:0.8rem; --py:0.5rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
										type="button"
										id="copy-and-share-chat-button"
										on:click={async () => {
											const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);

											if (isSafari) {
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
				</details>

				<!-- People & Groups sharing section -->
				<details open>
					<summary style="--cur:pointer; --d:flex; --ai:center; --g:0.5rem; --py:0.5rem; --size:0.8125rem; --weight:600; --c:var(--color-gray-700); --dark-c:var(--color-gray-300); --us:none; --ls:normal; --bt:1px solid var(--color-gray-100); --dark-bt:1px solid var(--color-gray-800); --pt:0.6rem">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" style="--w:0.8rem; --h:0.8rem">
							<path stroke-linecap="round" stroke-linejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" />
						</svg>
						{$i18n.t('People & Groups')}
						{#if existingTargets.length > 0}
							<span style="--px:0.4rem; --py:0.0625rem; --radius:9999px; --size:0.6875rem; --weight:500; --bgc:var(--color-green-100); --c:var(--color-green-700); --dark-bgc:var(--color-green-900); --dark-c:var(--color-green-300)">
								{existingTargets.length}
							</span>
						{/if}
					</summary>
					<div style="--pt:0.5rem; --pb:0.5rem; --pl:1.375rem; --d:flex; --fd:column; --g:0.6rem">
						<ShareTargetPicker bind:selectedTargets />

						{#if existingTargets.length > 0}
							<ShareTargetList {chatId} bind:targets={existingTargets} />
						{/if}

						<div style="--d:flex; --jc:flex-end; --pt:0.2rem">
							<button
								style="--d:flex; --ai:center; --g:0.2rem; --px:0.8rem; --py:0.5rem; --size:0.8rem; --weight:500; --radius:9999px; --tn:all 150ms ease; {selectedTargets.length > 0 && !sharing ? '--bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100)' : '--bgc:var(--color-gray-200); --c:var(--color-gray-400); --dark-bgc:var(--color-gray-800); --dark-c:var(--color-gray-600); --cur:not-allowed'}"
								type="button"
								disabled={selectedTargets.length === 0 || sharing}
								on:click={shareWithTargets}
							>
								{#if sharing}
									{$i18n.t('Sharing...')}
								{:else}
									{$i18n.t('Share')}
								{/if}
							</button>
						</div>
					</div>
				</details>
			</div>
		{/if}
	</div>
</Modal>

<style>
	details > summary {
		list-style: none;
	}
	details > summary::-webkit-details-marker {
		display: none;
	}
	details > summary::before {
		content: '▶';
		display: inline-block;
		font-size: 0.5rem;
		transition: transform 150ms ease;
		margin-right: 0.125rem;
	}
	details[open] > summary::before {
		transform: rotate(90deg);
	}
</style>
