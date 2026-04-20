<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import panzoom, { type PanZoom } from 'panzoom';
	import Icon from '$lib/components/Icon.svelte';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;


	export let show = false;
	export let src = '';
	export let alt = '';

	let mounted = false;

	let previewElement = null;

	let instance: PanZoom;

	let sceneParentElement: HTMLElement;
	let sceneElement: HTMLElement;

	$: if (sceneElement) {
		instance = panzoom(sceneElement, {
			bounds: true,
			boundsPadding: 0.1,

			zoomSpeed: 0.065
		});
	}
	const resetPanZoomViewport = () => {
		instance.moveTo(0, 0);
		instance.zoomAbs(0, 0, 1);
		console.log(instance.getTransform());
	};

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			console.log('Escape');
			show = false;
		}
	};

	onMount(() => {
		mounted = true;
	});

	$: if (show && previewElement) {
		document.body.appendChild(previewElement);
		window.addEventListener('keydown', handleKeyDown);
		document.body.style.overflow = 'hidden';
	} else if (previewElement) {
		window.removeEventListener('keydown', handleKeyDown);
		document.body.removeChild(previewElement);
		document.body.style.overflow = 'unset';
	}

	onDestroy(() => {
		show = false;

		if (previewElement) {
			document.body.removeChild(previewElement);
		}
	});
</script>

{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		bind:this={previewElement}
		style="--pos:fixed; --top:0; --right:0; --left:0; --bottom:0; --bgc:#000; --c:#fff; --w:100%; --minh:100vh; --h:100vh; --d:flex; --jc:center; --z:9999; --of:hidden; overscroll-behavior:contain"
	class="modal"
	>
		<div style="--pos:absolute; --left:0; --w:100%; --d:flex; --jc:space-between; --us:none; --z:20">
			<div>
				<button
					style="--p:1.2rem"
					on:pointerdown={(e) => {
						e.stopImmediatePropagation();
						e.preventDefault();
						show = false;
					}}
					on:click={(e) => {
						show = false;
					}}
				>
					<Icon name="x-mark" strokeWidth="2" className={'size-6'} />
				</button>
			</div>

			<div>
				<button
					style="--p:1.2rem; --z:999"
					on:click={() => {
						if (src.startsWith('data:image/')) {
							const base64Data = src.split(',')[1];
							const blob = new Blob([Uint8Array.from(atob(base64Data), (c) => c.charCodeAt(0))], {
								type: 'image/png'
							});

							const mimeType = blob.type || 'image/png';
							// create file name based on the MIME type, alt should be a valid file name with extension
							const fileName = alt
								? `${alt.replaceAll('.', '')}.${mimeType.split('/')[1]}`
								: 'download.png';

							// Use FileSaver to save the blob
							saveAs(blob, fileName);
							return;
						} else if (src.startsWith('blob:')) {
							// Handle blob URLs
							fetch(src)
								.then((response) => response.blob())
								.then((blob) => {
									// detect the MIME type from the blob
									const mimeType = blob.type || 'image/png';

									// Create a new Blob with the correct MIME type
									const blobWithType = new Blob([blob], { type: mimeType });

									// create file name based on the MIME type, alt should be a valid file name with extension
									const fileName = alt
										? `${alt.replaceAll('.', '')}.${mimeType.split('/')[1]}`
										: 'download.png';

									// Use FileSaver to save the blob
									saveAs(blobWithType, fileName);
								})
								.catch((error) => {
									console.error('Error downloading blob:', error);
								});
							return;
						} else if (
							src.startsWith('/') ||
							src.startsWith('http://') ||
							src.startsWith('https://')
						) {
							// Handle remote URLs
							fetch(src)
								.then((response) => response.blob())
								.then((blob) => {
									// detect the MIME type from the blob
									const mimeType = blob.type || 'image/png';

									// Create a new Blob with the correct MIME type
									const blobWithType = new Blob([blob], { type: mimeType });

									// create file name based on the MIME type, alt should be a valid file name with extension
									const fileName = alt
										? `${alt.replaceAll('.', '')}.${mimeType.split('/')[1]}`
										: 'download.png';

									// Use FileSaver to save the blob
									saveAs(blobWithType, fileName);
								})
								.catch((error) => {
									console.error('Error downloading remote image:', error);
								});
							return;
						}
					}}
				>
					<Icon name="download-fill-20" className="size-6" />
				</button>
			</div>
		</div>
		<div style="--d:flex; --h:100%; --maxh:100%; --jc:center; --ai:center; --z:0">
			<img
				bind:this={sceneElement}
				{src}
				{alt}
				style="--mx:auto; --h:100%; --objf:scale-down; --us:none"
				draggable="false"
			/>
		</div>
	</div>
{/if}
