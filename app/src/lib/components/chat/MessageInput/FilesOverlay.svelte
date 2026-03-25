<script lang="ts">
	import { showSidebar } from '$lib/stores';
	import AddFilesPlaceholder from '$lib/components/AddFilesPlaceholder.svelte';

	export let show = false;
	let overlayElement = null;

	$: if (show && overlayElement) {
		document.body.appendChild(overlayElement);
		document.body.style.overflow = 'hidden';
	} else if (overlayElement) {
		document.body.removeChild(overlayElement);
		document.body.style.overflow = 'unset';
	}
</script>

{#if show}
	<div
		bind:this={overlayElement}
		style="--pos:fixed; --pos:fixed; --top:0; --right:0; --bottom:0; --w:100%; --h:100%; --d:flex; --z:9999; touch-action:none; --pe:none"
	class="{$showSidebar
			? 'left-0 md:left-[260px] md:w-[calc(100%-260px)]'
			: 'left-0'}"
		id="dropzone"
		role="region"
		aria-label="Drag and Drop Container"
	>
		<div style="--pos:absolute; --w:100%; --h:100%; backdrop-filter:blur(4px); --bgc:rgb(51 51 51 / 0.4); --d:flex; --jc:center">
			<div style="--m:auto; --pt:16rem; --d:flex; --fd:column; --jc:center">
				<div style="--maxw:28rem">
					<AddFilesPlaceholder />
				</div>
			</div>
		</div>
	</div>
{/if}
