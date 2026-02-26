<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { flyAndScale } from '$lib/utils/transitions';
	import { fade, fly, slide } from 'svelte/transition';
	import { isApp } from '$lib/stores';

	export let show = false;
	export let className = '';
	export let onClose = () => {};

	let modalElement = null;
	let mounted = false;

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape' && isTopModal()) {
			console.log('Escape');
			show = false;
		}
	};

	const isTopModal = () => {
		const modals = document.getElementsByClassName('modal');
		return modals.length && modals[modals.length - 1] === modalElement;
	};

	onMount(() => {
		mounted = true;
	});

	$: if (show && modalElement) {
		document.body.appendChild(modalElement);
		window.addEventListener('keydown', handleKeyDown);
		document.body.style.overflow = 'hidden';
	} else if (modalElement) {
		onClose();
		window.removeEventListener('keydown', handleKeyDown);

		if (document.body.contains(modalElement)) {
			document.body.removeChild(modalElement);
			document.body.style.overflow = 'unset';
		}
	}

	onDestroy(() => {
		show = false;
		if (modalElement) {
			if (document.body.contains(modalElement)) {
				document.body.removeChild(modalElement);
				document.body.style.overflow = 'unset';
			}
		}
	});
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->

<div
	bind:this={modalElement}
	style="--pos:fixed; --right:0; --left:0; --bottom:0; --bgc:rgb(0 0 0 / 0.6); --w:100%; --h:100vh; --maxh:100dvh; --d:flex; --jc:center; --z:999; --of:hidden; overscroll-behavior:contain"
	class="modal {$isApp
		? ' ml-[4.5rem] max-w-[calc(100%-4.5rem)]'
		: ''}"
	in:fly={{ y: 100, duration: 100 }}
	on:mousedown={() => {
		show = false;
	}}
>
	<div
		style="--mt:auto; --w:100%; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-900); --dark-c:var(--color-gray-100); --maxh:100dvh; --ofy:auto"
	class="{className} scrollbar-hidden"
		on:mousedown={(e) => {
			e.stopPropagation();
		}}
	>
		<slot />
	</div>
</div>

<style>
	.modal-content {
		animation: scaleUp 0.1s ease-out forwards;
	}

	@keyframes scaleUp {
		from {
			transform: scale(0.985);
			opacity: 0;
		}
		to {
			transform: scale(1);
			opacity: 1;
		}
	}
</style>
