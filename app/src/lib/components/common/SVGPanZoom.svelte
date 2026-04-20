<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { toast } from 'svelte-sonner';

	import panzoom, { type PanZoom } from 'panzoom';
	import DOMPurify from 'dompurify';

	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { copyToClipboard } from '$lib/utils';

	import Tooltip from './Tooltip.svelte';
	import Icon from '$lib/components/Icon.svelte';

	export let className = '';
	export let svg = '';
	export let content = '';

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

	const downloadAsSVG = () => {
		const svgBlob = new Blob([svg], { type: 'image/svg+xml' });
		saveAs(svgBlob, `diagram.svg`);
	};
</script>

<div bind:this={sceneParentElement} style="--pos:relative"
	class="{className}">
	<div bind:this={sceneElement} style="--d:flex; --h:100%; --maxh:100%; --jc:center; --ai:center">
		{@html svg}
	</div>

	{#if content}
		<div style="--pos:absolute; --top:0.2rem; --right:0.2rem">
			<div style="--d:flex; --g:0.2rem">
				<Tooltip content={$i18n.t('Download as SVG')}>
					<button
						style="--p:0.4rem; --radius:0.5rem;  --bc:var(--color-gray-100); --dark-bs:none; --dark-bgc:var(--color-gray-850); --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={() => {
							downloadAsSVG();
						}}
					>
						<Icon name="arrow-down-tray" className=" size-4" />
					</button>
				</Tooltip>

				<Tooltip content={$i18n.t('Reset view')}>
					<button
						style="--p:0.4rem; --radius:0.5rem;  --bc:var(--color-gray-100); --dark-bs:none; --dark-bgc:var(--color-gray-850); --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={() => {
							resetPanZoomViewport();
						}}
					>
						<Icon name="reset" className=" size-4" />
					</button>
				</Tooltip>

				<Tooltip content={$i18n.t('Copy to clipboard')}>
					<button
						style="--p:0.4rem; --radius:0.5rem;  --bc:var(--color-gray-100); --dark-bs:none; --dark-bgc:var(--color-gray-850); --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={() => {
							copyToClipboard(content);
							toast.success($i18n.t('Copied to clipboard'));
						}}
					>
						<Icon name="clipboard" className=" size-4" strokeWidth="1.5" />
					</button>
				</Tooltip>
			</div>
		</div>
	{/if}
</div>
