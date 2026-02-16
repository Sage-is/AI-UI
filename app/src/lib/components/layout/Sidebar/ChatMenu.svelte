<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext, createEventDispatcher } from 'svelte';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import jsPDF from 'jspdf';
	import html2canvas from 'html2canvas-pro';

	const dispatch = createEventDispatcher();

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Tags from '$lib/components/chat/Tags.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import Bookmark from '$lib/components/icons/Bookmark.svelte';
	import BookmarkSlash from '$lib/components/icons/BookmarkSlash.svelte';
	import {
		getChatById,
		getChatPinnedStatusById,
		toggleChatPinnedStatusById
	} from '$lib/apis/chats';
	import { chats, settings, theme, user } from '$lib/stores';
	import { createMessagesList } from '$lib/utils';
	import { downloadChatAsPDF } from '$lib/apis/utils';
	import Download from '$lib/components/icons/Download.svelte';

	const i18n = getContext('i18n');

	export let shareHandler: Function;
	export let cloneChatHandler: Function;
	export let archiveChatHandler: Function;
	export let renameHandler: Function;
	export let deleteHandler: Function;
	export let onClose: Function;

	export let chatId = '';

	let show = false;
	let pinned = false;

	const pinHandler = async () => {
		await toggleChatPinnedStatusById(localStorage.token, chatId);
		dispatch('change');
	};

	const checkPinned = async () => {
		pinned = await getChatPinnedStatusById(localStorage.token, chatId);
	};

	const getChatAsText = async (chat) => {
		const history = chat.chat.history;
		const messages = createMessagesList(history, history.currentId);
		const chatText = messages.reduce((a, message, i, arr) => {
			return `${a}### ${message.role.toUpperCase()}\n${message.content}\n\n`;
		}, '');

		return chatText.trim();
	};

	const downloadTxt = async () => {
		const chat = await getChatById(localStorage.token, chatId);
		if (!chat) {
			return;
		}

		const chatText = await getChatAsText(chat);
		let blob = new Blob([chatText], {
			type: 'text/plain'
		});

		saveAs(blob, `chat-${chat.chat.title}.txt`);
	};

	const downloadPdf = async () => {
		const chat = await getChatById(localStorage.token, chatId);

		if ($settings?.stylizedPdfExport ?? true) {
			const containerElement = document.getElementById('messages-container');

			if (containerElement) {
				try {
					const isDarkMode = document.documentElement.classList.contains('dark');
					const virtualWidth = 800; // Fixed width in px
					const pagePixelHeight = 1200; // Each slice height (adjust to avoid canvas bugs; generally 2–4k is safe)

					// Clone & style once
					const clonedElement = containerElement.cloneNode(true);
					clonedElement.classList.add('text-black');
					clonedElement.classList.add('dark:text-white');
					clonedElement.style.width = `${virtualWidth}px`;
					clonedElement.style.position = 'absolute';
					clonedElement.style.left = '-9999px'; // Offscreen
					clonedElement.style.height = 'auto';
					document.body.appendChild(clonedElement);

					// Get total height after attached to DOM
					const totalHeight = clonedElement.scrollHeight;
					let offsetY = 0;
					let page = 0;

					// Prepare PDF
					const pdf = new jsPDF('p', 'mm', 'a4');
					const imgWidth = 210; // A4 mm
					const pageHeight = 297; // A4 mm

					while (offsetY < totalHeight) {
						// For each slice, adjust scrollTop to show desired part
						clonedElement.scrollTop = offsetY;

						// Optionally: mask/hide overflowing content via CSS if needed
						clonedElement.style.maxHeight = `${pagePixelHeight}px`;
						// Only render the visible part
						const canvas = await html2canvas(clonedElement, {
							backgroundColor: isDarkMode ? '#000' : '#fff',
							useCORS: true,
							scale: 2,
							width: virtualWidth,
							height: Math.min(pagePixelHeight, totalHeight - offsetY),
							// Optionally: y offset for correct region?
							windowWidth: virtualWidth
							//windowHeight: pagePixelHeight,
						});
						const imgData = canvas.toDataURL('image/png');
						// Maintain aspect ratio
						const imgHeight = (canvas.height * imgWidth) / canvas.width;
						const position = 0; // Always first line, since we've clipped vertically

						if (page > 0) pdf.addPage();

						// Set page background for dark mode
						if (isDarkMode) {
							pdf.setFillColor(0, 0, 0);
							pdf.rect(0, 0, imgWidth, pageHeight, 'F'); // black bg
						}

						pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);

						offsetY += pagePixelHeight;
						page++;
					}

					document.body.removeChild(clonedElement);

					pdf.save(`chat-${chat.chat.title}.pdf`);
				} catch (error) {
					console.error('Error generating PDF', error);
				}
			}
		} else {
			console.log('Downloading PDF');

			const chatText = await getChatAsText(chat);

			const doc = new jsPDF();

			// Margins
			const left = 15;
			const top = 20;
			const right = 15;
			const bottom = 20;

			const pageWidth = doc.internal.pageSize.getWidth();
			const pageHeight = doc.internal.pageSize.getHeight();
			const usableWidth = pageWidth - left - right;
			const usableHeight = pageHeight - top - bottom;

			// Font size and line height
			const fontSize = 8;
			doc.setFontSize(fontSize);
			const lineHeight = fontSize * 1; // adjust if needed

			// Split the markdown into lines (handles \n)
			const paragraphs = chatText.split('\n');

			let y = top;

			for (let paragraph of paragraphs) {
				// Wrap each paragraph to fit the width
				const lines = doc.splitTextToSize(paragraph, usableWidth);

				for (let line of lines) {
					// If the line would overflow the bottom, add a new page
					if (y + lineHeight > pageHeight - bottom) {
						doc.addPage();
						y = top;
					}
					doc.text(line, left, y);
					y += lineHeight;
				}
				// Add empty line at paragraph breaks
				y += lineHeight * 0.5;
			}

			doc.save(`chat-${chat.chat.title}.pdf`);
		}
	};

	const downloadJSONExport = async () => {
		const chat = await getChatById(localStorage.token, chatId);

		if (chat) {
			let blob = new Blob([JSON.stringify([chat])], {
				type: 'application/json'
			});
			saveAs(blob, `chat-export-${Date.now()}.json`);
		}
	};

	$: if (show) {
		checkPinned();
	}
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			style="--w:100%; --maxw:200px; --radius:0.75rem; --px:0.25rem; --py:0.375rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850, #262626); --dark-c:#fff; --shadow:4"
			sideOffset={-2}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.375rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem"
				on:click={() => {
					pinHandler();
				}}
			>
				{#if pinned}
					<BookmarkSlash strokeWidth="2" />
					<div style="--d:flex; --ai:center">{$i18n.t('Unpin')}</div>
				{:else}
					<Bookmark strokeWidth="2" />
					<div style="--d:flex; --ai:center">{$i18n.t('Pin')}</div>
				{/if}
			</DropdownMenu.Item>

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.375rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem"
				on:click={() => {
					renameHandler();
				}}
			>
				<Pencil strokeWidth="2" />
				<div style="--d:flex; --ai:center">{$i18n.t('Rename')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.375rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem"
				on:click={() => {
					cloneChatHandler();
				}}
			>
				<DocumentDuplicate strokeWidth="2" />
				<div style="--d:flex; --ai:center">{$i18n.t('Clone')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.375rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem"
				on:click={() => {
					archiveChatHandler();
				}}
			>
				<ArchiveBox strokeWidth="2" />
				<div style="--d:flex; --ai:center">{$i18n.t('Archive')}</div>
			</DropdownMenu.Item>

			{#if $user?.role === 'admin' || ($user.permissions?.chat?.share ?? true)}
				<DropdownMenu.Item
					style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.375rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem"
					on:click={() => {
						shareHandler();
					}}
				>
					<Share />
					<div style="--d:flex; --ai:center">{$i18n.t('Share')}</div>
				</DropdownMenu.Item>
			{/if}

			<DropdownMenu.Sub>
				<DropdownMenu.SubTrigger
					style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem"
				>
					<Download strokeWidth="2" />

					<div style="--d:flex; --ai:center">{$i18n.t('Download')}</div>
				</DropdownMenu.SubTrigger>
				<DropdownMenu.SubContent
					style="--w:100%; --radius:0.75rem; --px:0.25rem; --py:0.375rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850, #262626); --dark-c:#fff; --shadow:4"
					transition={flyAndScale}
					sideOffset={8}
				>
					{#if $user?.role === 'admin' || ($user.permissions?.chat?.export ?? true)}
						<DropdownMenu.Item
							style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem"
							on:click={() => {
								downloadJSONExport();
							}}
						>
							<div style="--d:flex; --ai:center; --line-clamp:1">{$i18n.t('Export chat (.json)')}</div>
						</DropdownMenu.Item>
					{/if}

					<DropdownMenu.Item
						style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem"
						on:click={() => {
							downloadTxt();
						}}
					>
						<div style="--d:flex; --ai:center; --line-clamp:1">{$i18n.t('Plain text (.txt)')}</div>
					</DropdownMenu.Item>

					<DropdownMenu.Item
						style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.5rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem"
						on:click={() => {
							downloadPdf();
						}}
					>
						<div style="--d:flex; --ai:center; --line-clamp:1">{$i18n.t('PDF document (.pdf)')}</div>
					</DropdownMenu.Item>
				</DropdownMenu.SubContent>
			</DropdownMenu.Sub>
			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.75rem; --py:0.375rem; --size:0.875rem; --cur:pointer; --hvr-bgc:var(--color-gray-50, #f9f9f9); --hvr-dark-bgc:var(--color-gray-800, #333); --radius:0.375rem"
				on:click={() => {
					deleteHandler();
				}}
			>
				<GarbageBin strokeWidth="2" />
				<div style="--d:flex; --ai:center">{$i18n.t('Delete')}</div>
			</DropdownMenu.Item>

			<hr style="--bc:var(--color-gray-100, #ececec); --dark-bc:var(--color-gray-850, #262626); --my:0.125rem" />

			<div style="--d:flex; --p:0.25rem">
				<Tags
					{chatId}
					on:add={(e) => {
						dispatch('tag', {
							type: 'add',
							name: e.detail.name
						});

						show = false;
					}}
					on:delete={(e) => {
						dispatch('tag', {
							type: 'delete',
							name: e.detail.name
						});

						show = false;
					}}
					on:close={() => {
						show = false;
						onClose();
					}}
				/>
			</div>
		</DropdownMenu.Content>
	</div>
</Dropdown>
