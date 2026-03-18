<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { fade } from 'svelte/transition';

	import { flyAndScale } from '$lib/utils/transitions';
	import * as FocusTrap from 'focus-trap';
	export let show = true;
	export let size = 'md';
	export let containerClassName = 'p-3';
	export let className = 'rounded-2xl';

	let modalElement = null;
	let mounted = false;
	// Create focus trap to trap user tabs inside modal
	// https://www.w3.org/WAI/WCAG21/Understanding/focus-order.html
	// https://www.w3.org/WAI/WCAG21/Understanding/keyboard.html
	let focusTrap: FocusTrap.FocusTrap | null = null;

	const sizeToWidth = (size) => {
		if (size === 'full') {
			return 'w-full';
		}
		if (size === 'xs') {
			return 'w-[16rem]';
		} else if (size === 'sm') {
			return 'w-[30rem]';
		} else if (size === 'md') {
			return 'w-[42rem]';
		} else if (size === 'lg') {
			return 'w-[56rem]';
		} else if (size === 'xl') {
			return 'w-[70rem]';
		} else if (size === '2xl') {
			return 'w-[84rem]';
		} else if (size === '3xl') {
			return 'w-[100rem]';
		} else {
			return 'w-[56rem]';
		}
	};

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
		focusTrap = FocusTrap.createFocusTrap(modalElement);
		focusTrap.activate();
		window.addEventListener('keydown', handleKeyDown);
		document.body.style.overflow = 'hidden';
	} else if (modalElement) {
		focusTrap.deactivate();
		window.removeEventListener('keydown', handleKeyDown);
		document.body.removeChild(modalElement);
		document.body.style.overflow = 'unset';
	}

	onDestroy(() => {
		show = false;
		if (focusTrap) {
			focusTrap.deactivate();
		}
		if (modalElement) {
			document.body.removeChild(modalElement);
		}
	});
</script>

{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		bind:this={modalElement}
		aria-modal="true"
		role="dialog"
		style="--pos:fixed; --top:0; --right:0; --left:0; --bottom:0; --bgc:rgb(0 0 0 / 0.6); --w:100%; --h:100vh; --maxh:100dvh; --d:flex; --jc:center; --z:9999; --ofy:auto; overscroll-behavior:contain"
		class="modal {containerClassName}"
		in:fade={{ duration: 10 }}
		on:mousedown={() => {
			show = false;
		}}
	>
		<modal-content
			style="--p: 1rem; 
				--m:auto; 
				--maxw:100%; 
				--minh:fit-content; 
				--br:1rem; 
				--bg:var(--white); 
				--dark-bg:var(--color-gray-900);"
			class="{sizeToWidth(size)} {size !== 'full' ? 'mx-2' : ''} scrollbar-hidden {className}"
			in:flyAndScale
			on:mousedown={(e) => {
				e.stopPropagation();
			}}
		>
			<slot />
		</modal-content>
	</div>
{/if}

<style>
	.modal-content {
		padding: 1rem;
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
