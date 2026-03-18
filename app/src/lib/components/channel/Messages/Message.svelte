<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import isToday from 'dayjs/plugin/isToday';
	import isYesterday from 'dayjs/plugin/isYesterday';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	dayjs.extend(relativeTime);
	dayjs.extend(isToday);
	dayjs.extend(isYesterday);
	dayjs.extend(localizedFormat);

	import { getContext, onMount } from 'svelte';
	const i18n = getContext<Writable<i18nType>>('i18n');

	onMount(async () => {
		try {
			branding = await getBranding();
		} catch (err) {
			console.error('Failed to load branding:', err);
		}
	});

	import { settings, user, shortCodesToEmojis } from '$lib/stores';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getBranding } from '$lib/apis/configs';

	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import ProfileImage from '$lib/components/chat/Messages/ProfileImage.svelte';
	import Name from '$lib/components/chat/Messages/Name.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Image from '$lib/components/common/Image.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import ProfilePreview from './Message/ProfilePreview.svelte';
	import ChatBubbleOvalEllipsis from '$lib/components/icons/ChatBubbleOvalEllipsis.svelte';
	import FaceSmile from '$lib/components/icons/FaceSmile.svelte';
	import ReactionPicker from './Message/ReactionPicker.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import { formatDate } from '$lib/utils';

	export let message;
	export let showUserProfile = true;
	export let thread = false;

	export let onDelete: Function = () => {};
	export let onEdit: Function = () => {};
	export let onThread: Function = () => {};
	export let onReaction: Function = () => {};

	let branding: { logo_url?: string; favicon_url?: string } = {};
	let showButtons = false;

	let edit = false;
	let editedContent = null;
	let showDeleteConfirmDialog = false;
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	title={$i18n.t('Delete Message')}
	message={$i18n.t('Are you sure you want to delete this message?')}
	onConfirm={async () => {
		await onDelete();
	}}
/>

{#if message}
	<div
		style="--d:flex; --fd:column; --jc:space-between; --px:1.2rem; --w:100%; --mx:auto; --hvr-bgc:rgb(205 205 205 / 0.05); --hvr-dark-bgc:rgb(78 78 78 / 0.05); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --pos:relative"
	class="{showUserProfile
			? 'pt-1.5 pb-0.5'
			: ''} {($settings?.widescreenMode ?? null)
			? 'max-w-full'
			: 'max-w-5xl'} group"
	>
		{#if !edit}
			<div
				style="--pos:absolute; --right:0.2rem; --top:-0.5rem; --z:10"
	class="{showButtons ? '' : 'invisible group-hover:visible'}"
			>
				<div
					style="--d:flex; --g:0.2rem; --radius:0.5rem; --bgc:#fff; --dark-bgc:var(--color-gray-850); --shadow:3; --p:0.125rem;  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-850)"
				>
					<ReactionPicker
						onClose={() => (showButtons = false)}
						onSubmit={(name) => {
							showButtons = false;
							onReaction(name);
						}}
					>
						<Tooltip content={$i18n.t('Add Reaction')}>
							<button
								style="--hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem; --p:0.2rem"
								on:click={() => {
									showButtons = true;
								}}
							>
								<FaceSmile />
							</button>
						</Tooltip>
					</ReactionPicker>

					{#if !thread}
						<Tooltip content={$i18n.t('Reply in Thread')}>
							<button
								style="--hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem; --p:0.2rem"
								on:click={() => {
									onThread(message.id);
								}}
							>
								<ChatBubbleOvalEllipsis />
							</button>
						</Tooltip>
					{/if}

					{#if message.user_id === $user?.id || $user?.role === 'admin'}
						<Tooltip content={$i18n.t('Edit')}>
							<button
								style="--hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem; --p:0.2rem"
								on:click={() => {
									edit = true;
									editedContent = message.content;
								}}
							>
								<Pencil />
							</button>
						</Tooltip>

						<Tooltip content={$i18n.t('Delete')}>
							<button
								style="--hvr-bgc:var(--color-gray-100); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem; --p:0.2rem"
								on:click={() => (showDeleteConfirmDialog = true)}
							>
								<GarbageBin />
							</button>
						</Tooltip>
					{/if}
				</div>
			</div>
		{/if}

		<div
			style="--d:flex; --w:100%"
	class="message- {message.id}"
			id="message-{message.id}"
			dir={$settings.chatDirection}
		>
			<div
				class={`shrink-0 ${($settings?.chatDirection ?? 'LTR') === 'LTR' ? 'mr-3' : 'ml-3'} w-9`}
			>
				{#if showUserProfile}
					<ProfilePreview user={message.user}>
						<ProfileImage
							src={message.user?.profile_image_url ?? branding?.logo_url ?? `${WEBUI_BASE_URL}/static/icons/favicon.png`}
							className={'size-8 translate-y-1 ml-0.5'}
						/>
					</ProfilePreview>
				{:else}
					<!-- <div style="--w:1.75rem; --h:1.75rem; --radius:9999px; --bgc:transparent" /> -->

					{#if message.created_at}
						<div
							style="--mt:0.4rem; --d:flex; --fs:0; --ai:center; --size:0.6rem; --as:center; --v:hidden; --c:var(--color-gray-500); --weight:500"
	class="group-hover:visible first-letter:capitalize"
						>
							<Tooltip content={dayjs(message.created_at / 1000000).format('LLLL')}>
								{dayjs(message.created_at / 1000000).format('HH:mm')}
							</Tooltip>
						</div>
					{/if}
				{/if}
			</div>

			<div style="--fx:1 1 auto; --w:0; --pl:0.2rem">
				{#if showUserProfile}
					<Name>
						<div style="--as:flex-end; --size:1rem; --fs:0; --weight:500; overflow:hidden; text-overflow:ellipsis; --ws:nowrap">
							{message?.user?.name}
						</div>

						{#if message.created_at}
							<div
								style="--as:center; --size:0.6rem; --v:hidden; --c:var(--color-gray-400); --weight:500; --ml:0.125rem; --translatey:1px"
	class="group-hover:visible first-letter:capitalize"
							>
								<Tooltip content={dayjs(message.created_at / 1000000).format('LLLL')}>
									<span style="--line-clamp:1">{formatDate(message.created_at / 1000000)}</span>
								</Tooltip>
							</div>
						{/if}
					</Name>
				{/if}

				{#if (message?.data?.files ?? []).length > 0}
					<div style="--my:0.6rem; --w:100%; --d:flex; --ofx:auto; --g:0.5rem; --fw:wrap">
						{#each message?.data?.files as file}
							<div>
								{#if file.type === 'image'}
									<Image src={file.url} alt={file.name} imageClassName=" max-h-96 rounded-lg" />
								{:else}
									<FileItem
										item={file}
										url={file.url}
										name={file.name}
										type={file.type}
										size={file?.size}
										colorClassName="bg-white dark:bg-gray-850 "
									/>
								{/if}
							</div>
						{/each}
					</div>
				{/if}

				{#if edit}
					<div style="--py:0.5rem">
						<Textarea
							className=" bg-transparent outline-hidden w-full resize-none"
							bind:value={editedContent}
							onKeydown={(e) => {
								if (e.key === 'Escape') {
									document.getElementById('close-edit-message-button')?.click();
								}

								const isCmdOrCtrlPressed = e.metaKey || e.ctrlKey;
								const isEnterPressed = e.key === 'Enter';

								if (isCmdOrCtrlPressed && isEnterPressed) {
									document.getElementById('confirm-edit-message-button')?.click();
								}
							}}
						/>
						<div style="--mt:0.5rem; --mb:0.2rem; --d:flex; --jc:flex-end; --size:0.8rem; --weight:500">
							<div style="--d:flex; --g:0.4rem">
								<button
									id="close-edit-message-button"
									style="--px:1rem; --py:0.5rem; --bgc:#fff; --dark-bgc:var(--color-gray-900); --hvr-bgc:var(--color-gray-100); --c:var(--color-gray-800); --dark-c:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:1.5rem"
									on:click={() => {
										edit = false;
										editedContent = null;
									}}
								>
									{$i18n.t('Cancel')}
								</button>

								<button
									id="confirm-edit-message-button"
									style="--px:1rem; --py:0.5rem; --bgc:var(--color-gray-900); --dark-bgc:#fff; --hvr-bgc:var(--color-gray-850); --c:var(--color-gray-100); --dark-c:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:1.5rem"
									on:click={async () => {
										onEdit(editedContent);
										edit = false;
										editedContent = null;
									}}
								>
									{$i18n.t('Save')}
								</button>
							</div>
						</div>
					</div>
				{:else}
					<div style="--minw:100%"
	class="markdown-prose">
						<Markdown
							id={message.id}
							content={message.content}
						/>{#if message.created_at !== message.updated_at}<span style="--c:var(--color-gray-500); --size:10px"
								>(edited)</span
							>{/if}
					</div>

					{#if (message?.reactions ?? []).length > 0}
						<div>
							<div style="--d:flex; --ai:center; --fw:wrap; row-gap:0.4rem; --g:0.2rem; --mt:0.2rem; --mb:0.5rem">
								{#each message.reactions as reaction}
									<Tooltip content={`:${reaction.name}:`}>
										<button
											style="--d:flex; --ai:center; --g:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.6rem; --px:0.5rem; --py:0.2rem; --cur:pointer"
	class="{reaction.user_ids.includes(
												$user?.id
											)
												? ' bg-blue-300/10 outline outline-blue-500/50 outline-1'
												: 'bg-gray-300/10 dark:bg-gray-500/10 hover:outline hover:outline-gray-700/30 dark:hover:outline-gray-300/30 hover:outline-1'}"
											on:click={() => {
												onReaction(reaction.name);
											}}
										>
											{#if $shortCodesToEmojis[reaction.name]}
												<img
													src="{WEBUI_BASE_URL}/assets/emojis/{$shortCodesToEmojis[
														reaction.name
													].toLowerCase()}.svg"
													alt={reaction.name}
													style="--w:1rem; --h:1rem"
													loading="lazy"
												/>
											{:else}
												<div>
													{reaction.name}
												</div>
											{/if}

											{#if reaction.user_ids.length > 0}
												<div style="--size:0.6rem; --weight:500; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
													{reaction.user_ids?.length}
												</div>
											{/if}
										</button>
									</Tooltip>
								{/each}

								<ReactionPicker
									onSubmit={(name) => {
										onReaction(name);
									}}
								>
									<Tooltip content={$i18n.t('Add Reaction')}>
										<div
											style="--d:flex; --ai:center; --g:0.4rem; --bgc:rgb(155 155 155 / 0.1); outline-style:solid; outline-color:rgb(78 78 78 / 0.3); outline-color:rgb(205 205 205 / 0.3); outline-width:1px; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.6rem; --px:0.2rem; --py:0.2rem; --cur:pointer; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)"
										>
											<FaceSmile />
										</div>
									</Tooltip>
								</ReactionPicker>
							</div>
						</div>
					{/if}

					{#if !thread && message.reply_count > 0}
						<div style="--d:flex; --ai:center; --g:0.4rem; --mt:-0.125rem; --mb:0.4rem">
							<button
								style="--d:flex; --ai:center; --size:0.6rem; --py:0.2rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --hvr-c:var(--color-gray-700); --hvr-dark-c:var(--color-gray-300); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
								on:click={() => {
									onThread(message.id);
								}}
							>
								<span style="--weight:500; --mr:0.2rem">
									{$i18n.t('{{COUNT}} Replies', { COUNT: message.reply_count })}</span
								><span>
									{' - '}{$i18n.t('Last reply')}
									{dayjs.unix(message.latest_reply_at / 1000000000).fromNow()}</span
								>

								<span style="--ml:0.2rem">
									<ChevronRight className="size-2.5" strokeWidth="3" />
								</span>
								<!-- {$i18n.t('View Replies')} -->
							</button>
						</div>
					{/if}
				{/if}
			</div>
		</div>
	</div>
{/if}
