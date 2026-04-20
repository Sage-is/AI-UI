<script lang="ts">
	import dayjs from 'dayjs';
	import { toast } from 'svelte-sonner';
	import { tick, getContext, onMount } from 'svelte';

	import { models, settings } from '$lib/stores';
	import { user as _user } from '$lib/stores';
	import { copyToClipboard as _copyToClipboard, formatDate } from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import Name from './Name.svelte';
	import ProfileImage from './ProfileImage.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Markdown from './Markdown.svelte';
	import Image from '$lib/components/common/Image.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');
	dayjs.extend(localizedFormat);

	export let user;

	export let history;
	export let messageId;

	export let siblings;

	export let gotoMessage: Function;
	export let showPreviousMessage: Function;
	export let showNextMessage: Function;

	export let editMessage: Function;
	export let deleteMessage: Function;

	export let isFirstMessage: boolean;
	export let readOnly: boolean;

	let showDeleteConfirm = false;

	let messageIndexEdit = false;

	let edit = false;
	let editedContent = '';
	let editedFiles = [];

	let messageEditTextAreaElement: HTMLTextAreaElement;

	let message = JSON.parse(JSON.stringify(history.messages[messageId]));
	$: if (history.messages) {
		if (JSON.stringify(message) !== JSON.stringify(history.messages[messageId])) {
			message = JSON.parse(JSON.stringify(history.messages[messageId]));
		}
	}

	const copyToClipboard = async (text) => {
		const res = await _copyToClipboard(text);
		if (res) {
			toast.success($i18n.t('Copying to clipboard was successful!'));
		}
	};

	const editMessageHandler = async () => {
		edit = true;
		editedContent = message.content;
		editedFiles = message.files;

		await tick();

		if (messageEditTextAreaElement) {
			messageEditTextAreaElement.style.height = '';
			messageEditTextAreaElement.style.height = `${messageEditTextAreaElement.scrollHeight}px`;

			messageEditTextAreaElement?.focus();
		}
	};

	const editMessageConfirmHandler = async (submit = true) => {
		editMessage(message.id, { content: editedContent, files: editedFiles }, submit);

		edit = false;
		editedContent = '';
		editedFiles = [];
	};

	const cancelEditMessage = () => {
		edit = false;
		editedContent = '';
		editedFiles = [];
	};

	const deleteMessageHandler = async () => {
		deleteMessage(message.id);
	};

	onMount(() => {
		// console.log('UserMessage mounted');
	});
</script>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete message?')}
	on:confirm={() => {
		deleteMessageHandler();
	}}
/>

<div
	style="--d:flex; --w:100%"
	class="user-message group"
	dir={$settings.chatDirection}
	id="message-{message.id}"
>
	{#if !($settings?.chatBubble ?? true)}
		<div class={`shrink-0 ltr:mr-3 rtl:ml-3 mt-1`}>
			<ProfileImage
				src={message.user
					? ($models.find((m) => m.id === message.user)?.info?.meta?.profile_image_url ??
						`${WEBUI_BASE_URL}/static/user.png`)
					: (user?.profile_image_url ?? `${WEBUI_BASE_URL}/static/user.png`)}
				className={'size-8 user-message-profile-image'}
			/>
		</div>
	{/if}
	<div style="--fx:1 1 auto; --w:0; --maxw:100%; --pl:0.2rem">
		{#if !($settings?.chatBubble ?? true)}
			<div>
				<Name>
					{#if message.user}
						{$i18n.t('You')}
						<span style="--c:var(--color-gray-500); --size:0.8rem; --weight:500">{message?.user ?? ''}</span>
					{:else if $settings.showUsername || $_user.name !== user.name}
						{user.name}
					{:else}
						{$i18n.t('You')}
					{/if}

					{#if message.timestamp}
						<div
							style="--as:center; --size:0.6rem; --c:var(--color-gray-400); --weight:500; --ml:0.125rem; --translatey:1px"
	class="invisible group-hover:visible first-letter:capitalize"
						>
							<Tooltip content={dayjs(message.timestamp * 1000).format('LLLL')}>
								<span style="--line-clamp:1">{formatDate(message.timestamp * 1000)}</span>
							</Tooltip>
						</div>
					{/if}
				</Name>
			</div>
		{:else if message.timestamp}
			<div style="--d:flex; --jc:flex-end; --pr:0.5rem; --size:0.6rem">
				<div
					style="--size:0.65rem; --c:var(--color-gray-400); --weight:500; --mb:0.125rem"
	class="invisible group-hover:visible first-letter:capitalize"
				>
					<Tooltip content={dayjs(message.timestamp * 1000).format('LLLL')}>
						<span style="--line-clamp:1">{formatDate(message.timestamp * 1000)}</span>
					</Tooltip>
				</div>
			</div>
		{/if}

		<div style="--w:100%; --minw:100%"
	class="chat- {message.role} markdown-prose">
			{#if edit !== true}
				{#if message.files}
					<div style="--mb:0.2rem; --w:100%; --d:flex; --fd:column; --jc:flex-end; --ofx:auto; --g:0.2rem; --fw:wrap">
						{#each message.files as file}
							<div class={($settings?.chatBubble ?? true) ? 'self-end' : ''}>
								{#if file.type === 'image'}
									<Image src={file.url} imageClassName=" max-h-96 rounded-lg" />
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
			{/if}

			{#if message.content !== ''}
				{#if edit === true}
					<div style="--w:100%; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-800); --radius:1.5rem; --px:1.2rem; --py:0.6rem; --mb:0.5rem">
						{#if (editedFiles ?? []).length > 0}
							<div style="--d:flex; --ai:center; --fw:wrap; --g:0.5rem; --mx:-0.5rem; --mb:0.2rem">
								{#each editedFiles as file, fileIdx}
									{#if file.type === 'image'}
										<div style="--pos:relative"
	class="group">
											<div style="--pos:relative; --d:flex; --ai:center">
												<Image
													src={file.url}
													alt="input"
													imageClassName=" size-14 rounded-xl object-cover"
												/>
											</div>
											<div style="--pos:absolute; --top:-0.2rem; --right:-0.2rem">
												<button
													style="--bgc:#fff; --c:#000;  --bc:#fff; --radius:9999px; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="invisible group-hover:visible"
													type="button"
													on:click={() => {
														editedFiles.splice(fileIdx, 1);

														editedFiles = editedFiles;
													}}
												>
													<Icon name="x-mark" className="size-4" />
												</button>
											</div>
										</div>
									{:else}
										<FileItem
											item={file}
											name={file.name}
											type={file.type}
											size={file?.size}
											loading={file.status === 'uploading'}
											dismissible={true}
											edit={true}
											on:dismiss={async () => {
												editedFiles.splice(fileIdx, 1);

												editedFiles = editedFiles;
											}}
											on:click={() => {
												console.log(file);
											}}
										/>
									{/if}
								{/each}
							</div>
						{/if}

						<div style="--maxh:24rem; --of:auto">
							<textarea
								id="message-edit-{message.id}"
								bind:this={messageEditTextAreaElement}
								style="--bgc:transparent; --oe:none; --w:100%; resize:none"
								bind:value={editedContent}
								on:input={(e) => {
									e.target.style.height = '';
									e.target.style.height = `${e.target.scrollHeight}px`;
								}}
								on:keydown={(e) => {
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
						</div>

						<div style="--mt:0.5rem; --mb:0.2rem; --d:flex; --jc:space-between; --size:0.8rem; --weight:500">
							<div>
								<button
									id="save-edit-message-button"
									style="--px:1rem; --py:0.5rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700);  --bc:var(--color-gray-100); --dark-bc:var(--color-gray-700); --c:var(--color-gray-700); --dark-c:var(--color-gray-200); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:1.5rem"
									on:click={() => {
										editMessageConfirmHandler(false);
									}}
								>
									{$i18n.t('Save')}
								</button>
							</div>

							<div style="--d:flex; --g:0.4rem">
								<button
									id="close-edit-message-button"
									style="--px:1rem; --py:0.5rem; --bgc:#fff; --dark-bgc:var(--color-gray-900); --hvr-bgc:var(--color-gray-100); --c:var(--color-gray-800); --dark-c:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:1.5rem"
									on:click={() => {
										cancelEditMessage();
									}}
								>
									{$i18n.t('Cancel')}
								</button>

								<button
									id="confirm-edit-message-button"
									style="--px:1rem; --py:0.5rem; --bgc:var(--color-gray-900); --dark-bgc:#fff; --hvr-bgc:var(--color-gray-850); --c:var(--color-gray-100); --dark-c:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:1.5rem"
									on:click={() => {
										editMessageConfirmHandler();
									}}
								>
									{$i18n.t('Send')}
								</button>
							</div>
						</div>
					</div>
				{:else}
					<div style="--w:100%">
						<div style="--d:flex"
	class="{($settings?.chatBubble ?? true) ? 'justify-end pb-1' : 'w-full'}">
							<div
								style="--radius:1.5rem"
	class="{($settings?.chatBubble ?? true)
									? `max-w-[90%] px-5 py-2  bg-gray-50 dark:bg-gray-850 ${
											message.files ? 'rounded-tr-lg' : ''
										}`
									: ' w-full'}"
							>
								{#if message.content}
									<Markdown id={message.id} content={message.content} />
								{/if}
							</div>
						</div>

						<div
							style="--d:flex; --c:var(--color-gray-600); --dark-c:var(--color-gray-500)"
	class="{($settings?.chatBubble ?? true)
								? 'justify-end'
								: ''}"
						>
							{#if !($settings?.chatBubble ?? true)}
								{#if siblings.length > 1}
									<div style="--d:flex; --as:center" dir="ltr">
										<button
											style="--as:center; --p:0.2rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-dark-c:#fff; --hvr-c:#000; --radius:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
											on:click={() => {
												showPreviousMessage(message);
											}}
										>
											<Icon name="chevron-left" className="size-[0.8rem]" strokeWidth="2.5" />
										</button>

										{#if messageIndexEdit}
											<div
												style="--size:0.8rem; --d:flex; --jc:center; --weight:600; --as:center; --dark-c:var(--color-gray-100); --minw:fit-content"
											>
												<input
													id="message-index-input-{message.id}"
													type="number"
													value={siblings.indexOf(message.id) + 1}
													min="1"
													max={siblings.length}
													on:focus={(e) => {
														e.target.select();
													}}
													on:blur={(e) => {
														gotoMessage(message, e.target.value - 1);
														messageIndexEdit = false;
													}}
													on:keydown={(e) => {
														if (e.key === 'Enter') {
															gotoMessage(message, e.target.value - 1);
															messageIndexEdit = false;
														}
													}}
													style="--bgc:transparent; --weight:600; --as:center; --dark-c:var(--color-gray-100); --minw:fit-content; --oe:none"
												/>/{siblings.length}
											</div>
										{:else}
											<!-- svelte-ignore a11y-no-static-element-interactions -->
											<div
												style="--size:0.8rem; --ls:0.1em; --weight:600; --as:center; --dark-c:var(--color-gray-100); --minw:fit-content"
												on:dblclick={async () => {
													messageIndexEdit = true;

													await tick();
													const input = document.getElementById(
														`message-index-input-${message.id}`
													);
													if (input) {
														input.focus();
														input.select();
													}
												}}
											>
												{siblings.indexOf(message.id) + 1}/{siblings.length}
											</div>
										{/if}

										<button
											style="--as:center; --p:0.2rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-dark-c:#fff; --hvr-c:#000; --radius:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
											on:click={() => {
												showNextMessage(message);
											}}
										>
											<Icon name="chevron-right" className="size-[0.8rem]" strokeWidth="2.5" />
										</button>
									</div>
								{/if}
							{/if}
							{#if !readOnly}
								<Tooltip content={$i18n.t('Edit')} placement="bottom">
									<button
										style="--p:0.4rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="invisible group-hover:visible edit-user-message-button"
										on:click={() => {
											editMessageHandler();
										}}
									>
										<Icon name="pencil" className="size-4" strokeWidth="2.3" />
									</button>
								</Tooltip>
							{/if}

							<Tooltip content={$i18n.t('Copy')} placement="bottom">
								<button
									style="--p:0.4rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="invisible group-hover:visible"
									on:click={() => {
										copyToClipboard(message.content);
									}}
								>
									<Icon name="clipboard-doc" className="size-4" strokeWidth="2.3" />
								</button>
							</Tooltip>

							{#if !readOnly && (!isFirstMessage || siblings.length > 1)}
								<Tooltip content={$i18n.t('Delete')} placement="bottom">
									<button
										style="--p:0.2rem; --radius:0.125rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="invisible group-hover:visible"
										on:click={() => {
											showDeleteConfirm = true;
										}}
									>
										<Icon name="trash-outline" className="size-4" strokeWidth="2" />
									</button>
								</Tooltip>
							{/if}

							{#if $settings?.chatBubble ?? true}
								{#if siblings.length > 1}
									<div style="--d:flex; --as:center" dir="ltr">
										<button
											style="--as:center; --p:0.2rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-dark-c:#fff; --hvr-c:#000; --radius:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
											on:click={() => {
												showPreviousMessage(message);
											}}
										>
											<Icon name="chevron-left" className="size-[0.8rem]" strokeWidth="2.5" />
										</button>

										{#if messageIndexEdit}
											<div
												style="--size:0.8rem; --d:flex; --jc:center; --weight:600; --as:center; --dark-c:var(--color-gray-100); --minw:fit-content"
											>
												<input
													id="message-index-input-{message.id}"
													type="number"
													value={siblings.indexOf(message.id) + 1}
													min="1"
													max={siblings.length}
													on:focus={(e) => {
														e.target.select();
													}}
													on:blur={(e) => {
														gotoMessage(message, e.target.value - 1);
														messageIndexEdit = false;
													}}
													on:keydown={(e) => {
														if (e.key === 'Enter') {
															gotoMessage(message, e.target.value - 1);
															messageIndexEdit = false;
														}
													}}
													style="--bgc:transparent; --weight:600; --as:center; --dark-c:var(--color-gray-100); --minw:fit-content; --oe:none"
												/>/{siblings.length}
											</div>
										{:else}
											<!-- svelte-ignore a11y-no-static-element-interactions -->
											<div
												style="--size:0.8rem; --ls:0.1em; --weight:600; --as:center; --dark-c:var(--color-gray-100); --minw:fit-content"
												on:dblclick={async () => {
													messageIndexEdit = true;

													await tick();
													const input = document.getElementById(
														`message-index-input-${message.id}`
													);
													if (input) {
														input.focus();
														input.select();
													}
												}}
											>
												{siblings.indexOf(message.id) + 1}/{siblings.length}
											</div>
										{/if}

										<button
											style="--as:center; --p:0.2rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-dark-c:#fff; --hvr-c:#000; --radius:0.4rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
											on:click={() => {
												showNextMessage(message);
											}}
										>
											<Icon name="chevron-right" className="size-[0.8rem]" strokeWidth="2.5" />
										</button>
									</div>
								{/if}
							{/if}
						</div>
					</div>
				{/if}
			{/if}
		</div>
	</div>
</div>

<style>
	button {
		margin: 0 0 0 0.2rem;
	}

</style>