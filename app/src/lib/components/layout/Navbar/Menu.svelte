<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { DropdownMenu } from 'bits-ui';
	import { getContext } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import jsPDF from 'jspdf';
	import html2canvas from 'html2canvas-pro';

	import { downloadChatAsPDF } from '$lib/apis/utils';
	import { copyToClipboard, createMessagesList } from '$lib/utils';

	import {
		showOverview,
		showControls,
		showArtifacts,
		mobile,
		temporaryChatEnabled,
		theme,
		user,
		settings
	} from '$lib/stores';
	import { flyAndScale } from '$lib/utils/transitions';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tags from '$lib/components/chat/Tags.svelte';
					import { getChatById } from '$lib/apis/chats';

	const i18n = getContext('i18n');

	export let shareEnabled: boolean = false;
	export let shareHandler: Function;
	export let downloadHandler: Function;
	export let hasShareTargets: boolean = false;

	// export let tagHandler: Function;

	export let chat;
	export let onClose: Function = () => {};

	const getChatAsText = async () => {
		const history = chat.chat.history;
		const messages = createMessagesList(history, history.currentId);
		const chatText = messages.reduce((a, message, i, arr) => {
			return `${a}### ${message.role.toUpperCase()}\n${message.content}\n\n`;
		}, '');

		return chatText.trim();
	};

	const downloadTxt = async () => {
		const chatText = await getChatAsText();

		let blob = new Blob([chatText], {
			type: 'text/plain'
		});

		saveAs(blob, `chat-${chat.chat.title}.txt`);
	};

	const downloadPdf = async () => {
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

			const chatText = await getChatAsText();

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
					y += lineHeight * 0.5;
				}
				// Add empty line at paragraph breaks
				y += lineHeight * 0.1;
			}

			doc.save(`chat-${chat.chat.title}.pdf`);
		}
	};

	const downloadJSONExport = async () => {
		if (chat.id) {
			let chatObj = null;

			if (chat.id === 'local' || $temporaryChatEnabled) {
				chatObj = chat;
			} else {
				chatObj = await getChatById(localStorage.token, chat.id);
			}

			let blob = new Blob([JSON.stringify([chatObj])], {
				type: 'application/json'
			});
			saveAs(blob, `chat-export-${Date.now()}.json`);
		}
	};
</script>

<Dropdown
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
	<slot />

	<div slot="content">
		<DropdownMenu.Content
			style="--w:100%; --maxw:200px; --radius:0.6rem; --px:0.2rem; --py:0.4rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:4"
			sideOffset={8}
			side="bottom"
			align="end"
			transition={flyAndScale}
		>
			<!-- <DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem"
				on:click={async () => {
					await showSettings.set(!$showSettings);
				}}
			>
				<Icon name="cog6" className="size-4" />
				<div style="--d:flex; --ai:center">{$i18n.t('Settings')}</div>
			</DropdownMenu.Item> -->

			{#if $mobile}
				<DropdownMenu.Item
					style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem; --us:none; --w:100%"
					id="chat-controls-button"
					on:click={async () => {
						await showControls.set(true);
						await showOverview.set(false);
						await showArtifacts.set(false);
					}}
				>
					<Icon name="adjustments-horizontal" className=" size-4" strokeWidth="0.5" />
					<div style="--d:flex; --ai:center">{$i18n.t('Controls')}</div>
				</DropdownMenu.Item>
			{/if}

			{#if !$temporaryChatEnabled && ($user?.role === 'admin' || ($user.permissions?.chat?.share ?? true))}
				<DropdownMenu.Item
					style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem; --us:none; --w:100%"
					id="chat-share-button"
					on:click={() => {
						shareHandler();
					}}
				>
					{#if hasShareTargets}
						<!-- Circled share icon when already shared -->
						<Icon name="share-nodes-outline" className="size-[1.2rem]" />
						<div style="--d:flex; --ai:center; --c:var(--color-green-600); --dark-c:var(--color-green-400)">{$i18n.t('Shared')}</div>
					{:else}
						<Icon name="share" className="size-4" />
						<div style="--d:flex; --ai:center">{$i18n.t('Share')}</div>
					{/if}
				</DropdownMenu.Item>
			{/if}

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem; --us:none; --w:100%"
				id="chat-overview-button"
				on:click={async () => {
					await showControls.set(true);
					await showOverview.set(true);
					await showArtifacts.set(false);
				}}
			>
				<Icon name="map" className=" size-4" strokeWidth="1.5" />
				<div style="--d:flex; --ai:center">{$i18n.t('Overview')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem; --us:none; --w:100%"
				id="chat-overview-button"
				on:click={async () => {
					await showControls.set(true);
					await showArtifacts.set(true);
					await showOverview.set(false);
				}}
			>
				<Icon name="cube" className=" size-4" strokeWidth="1.5" />
				<div style="--d:flex; --ai:center">{$i18n.t('Artifacts')}</div>
			</DropdownMenu.Item>

			<DropdownMenu.Sub>
				<DropdownMenu.SubTrigger
					style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem; --us:none; --w:100%"
				>
					<Icon name="download" className="size-4" />

					<div style="--d:flex; --ai:center">{$i18n.t('Download')}</div>
				</DropdownMenu.SubTrigger>
				<DropdownMenu.SubContent
					style="--w:100%; --radius:0.6rem; --px:0.2rem; --py:0.4rem; --z:50; --bgc:#fff; --dark-bgc:var(--color-gray-850); --dark-c:#fff; --shadow:4"
					transition={flyAndScale}
					sideOffset={8}
				>
					{#if $user?.role === 'admin' || ($user.permissions?.chat?.export ?? true)}
						<DropdownMenu.Item
							style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem; --us:none; --w:100%"
							on:click={() => {
								downloadJSONExport();
							}}
						>
							<div style="--d:flex; --ai:center; --line-clamp:1">{$i18n.t('Export chat (.json)')}</div>
						</DropdownMenu.Item>
					{/if}
					<DropdownMenu.Item
						style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem; --us:none; --w:100%"
						on:click={() => {
							downloadTxt();
						}}
					>
						<div style="--d:flex; --ai:center; --line-clamp:1">{$i18n.t('Plain text (.txt)')}</div>
					</DropdownMenu.Item>

					<DropdownMenu.Item
						style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem; --us:none; --w:100%"
						on:click={() => {
							downloadPdf();
						}}
					>
						<div style="--d:flex; --ai:center; --line-clamp:1">{$i18n.t('PDF document (.pdf)')}</div>
					</DropdownMenu.Item>
				</DropdownMenu.SubContent>
			</DropdownMenu.Sub>

			<DropdownMenu.Item
				style="--d:flex; --g:0.5rem; --ai:center; --px:0.6rem; --py:0.5rem; --size:0.8rem; --cur:pointer; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --radius:0.4rem; --us:none; --w:100%"
				id="chat-copy-button"
				on:click={async () => {
					const res = await copyToClipboard(await getChatAsText()).catch((e) => {
						console.error(e);
					});

					if (res) {
						toast.success($i18n.t('Copied to clipboard'));
					}
				}}
			>
				<Icon name="clipboard" className=" size-4" strokeWidth="1.5" />
				<div style="--d:flex; --ai:center">{$i18n.t('Copy')}</div>
			</DropdownMenu.Item>

			{#if !$temporaryChatEnabled}
				<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.125rem" />

				<div style="--d:flex; --p:0.2rem">
					<Tags chatId={chat.id} />
				</div>
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
