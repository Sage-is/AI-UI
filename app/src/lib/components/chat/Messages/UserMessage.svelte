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
	<div style="--fx:1 1 auto; --w:0; --maxw:100%; --pl:0.25rem">
		{#if !($settings?.chatBubble ?? true)}
			<div>
				<Name>
					{#if message.user}
						{$i18n.t('You')}
						<span style="--c:var(--color-gray-500); --size:0.875rem; --weight:500">{message?.user ?? ''}</span>
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
					<div style="--mb:0.25rem; --w:100%; --d:flex; --fd:column; --jc:flex-end; --ofx:auto; --g:0.25rem; --fw:wrap">
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
					<div style="--w:100%; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-800); --radius:1.5rem; --px:1.25rem; --py:0.6rem; --mb:0.5rem">
						{#if (editedFiles ?? []).length > 0}
							<div style="--d:flex; --ai:center; --fw:wrap; --g:0.5rem; --mx:-0.5rem; --mb:0.25rem">
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
											<div style="--pos:absolute; --top:-0.25rem; --right:-0.25rem">
												<button
													style="--bgc:#fff; --c:#000;  --bc:#fff; --radius:9999px; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="invisible group-hover:visible"
													type="button"
													on:click={() => {
														editedFiles.splice(fileIdx, 1);

														editedFiles = editedFiles;
													}}
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 20 20"
														fill="currentColor"
														style="--w:1rem; --h:1rem"
													>
														<path
															d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
														/>
													</svg>
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

						<div style="--mt:0.5rem; --mb:0.25rem; --d:flex; --jc:space-between; --size:0.875rem; --weight:500">
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

							<div style="--d:flex; --g:0.375rem">
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
											style="--as:center; --p:0.25rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-dark-c:#fff; --hvr-c:#000; --radius:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
											on:click={() => {
												showPreviousMessage(message);
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
												stroke-width="2.5"
												style="--w:0.875rem; --h:0.875rem"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M15.75 19.5 8.25 12l7.5-7.5"
												/>
											</svg>
										</button>

										{#if messageIndexEdit}
											<div
												style="--size:0.875rem; --d:flex; --jc:center; --weight:600; --as:center; --dark-c:var(--color-gray-100); --minw:fit-content"
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
												style="--size:0.875rem; --ls:0.1em; --weight:600; --as:center; --dark-c:var(--color-gray-100); --minw:fit-content"
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
											style="--as:center; --p:0.25rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-dark-c:#fff; --hvr-c:#000; --radius:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
											on:click={() => {
												showNextMessage(message);
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
												stroke-width="2.5"
												style="--w:0.875rem; --h:0.875rem"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="m8.25 4.5 7.5 7.5-7.5 7.5"
												/>
											</svg>
										</button>
									</div>
								{/if}
							{/if}
							{#if !readOnly}
								<Tooltip content={$i18n.t('Edit')} placement="bottom">
									<button
										style="--p:0.375rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="invisible group-hover:visible edit-user-message-button"
										on:click={() => {
											editMessageHandler();
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="2.3"
											stroke="currentColor"
											style="--w:1rem; --h:1rem"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
											/>
										</svg>
									</button>
								</Tooltip>
							{/if}

							<Tooltip content={$i18n.t('Copy')} placement="bottom">
								<button
									style="--p:0.375rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.5rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="invisible group-hover:visible"
									on:click={() => {
										copyToClipboard(message.content);
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="2.3"
										stroke="currentColor"
										style="--w:1rem; --h:1rem"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184"
										/>
									</svg>
								</button>
							</Tooltip>

							{#if !readOnly && (!isFirstMessage || siblings.length > 1)}
								<Tooltip content={$i18n.t('Delete')} placement="bottom">
									<button
										style="--p:0.25rem; --radius:0.125rem; --hvr-dark-c:#fff; --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="invisible group-hover:visible"
										on:click={() => {
											showDeleteConfirm = true;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="2"
											stroke="currentColor"
											style="--w:1rem; --h:1rem"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
											/>
										</svg>
									</button>
								</Tooltip>
							{/if}

							{#if $settings?.chatBubble ?? true}
								{#if siblings.length > 1}
									<div style="--d:flex; --as:center" dir="ltr">
										<button
											style="--as:center; --p:0.25rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-dark-c:#fff; --hvr-c:#000; --radius:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
											on:click={() => {
												showPreviousMessage(message);
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
												stroke-width="2.5"
												style="--w:0.875rem; --h:0.875rem"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M15.75 19.5 8.25 12l7.5-7.5"
												/>
											</svg>
										</button>

										{#if messageIndexEdit}
											<div
												style="--size:0.875rem; --d:flex; --jc:center; --weight:600; --as:center; --dark-c:var(--color-gray-100); --minw:fit-content"
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
												style="--size:0.875rem; --ls:0.1em; --weight:600; --as:center; --dark-c:var(--color-gray-100); --minw:fit-content"
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
											style="--as:center; --p:0.25rem; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --hvr-dark-c:#fff; --hvr-c:#000; --radius:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
											on:click={() => {
												showNextMessage(message);
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
												stroke-width="2.5"
												style="--w:0.875rem; --h:0.875rem"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="m8.25 4.5 7.5 7.5-7.5 7.5"
												/>
											</svg>
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
		margin: 0 0 0 0.25rem;
	}

</style>