<script lang="ts">
	import DOMPurify from 'dompurify';

	import { onMount, getContext, createEventDispatcher, onDestroy, tick } from 'svelte';
	import * as FocusTrap from 'focus-trap';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { fade } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';
	import { marked } from 'marked';

	export let title = '';
	export let message = '';

	export let cancelLabel = $i18n.t('Cancel');
	export let confirmLabel = $i18n.t('Confirm');

	export let onConfirm = () => {};

	export let input = false;
	export let inputPlaceholder = '';
	export let inputValue = '';

	export let show = false;

	$: if (show) {
		init();
	}

	let modalElement = null;
	let mounted = false;

	let focusTrap: FocusTrap.FocusTrap | null = null;

	const init = () => {
		inputValue = '';
	};

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			console.log('Escape');
			show = false;
		}

		if (event.key === 'Enter') {
			console.log('Enter');
			confirmHandler();
		}
	};

	const confirmHandler = async () => {
		show = false;
		await tick();
		await onConfirm();
		dispatch('confirm', inputValue);
	};

	onMount(() => {
		mounted = true;
	});

	$: if (mounted) {
		if (show && modalElement) {
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
	<div
		bind:this={modalElement}
		style="--pos:fixed; --top:0; --right:0; --left:0; --bottom:0; --bgc:rgb(0 0 0 / 0.6); --w:100%; --h:100vh; --maxh:100dvh; --d:flex; --jc:center; --z:99999999; --of:hidden; overscroll-behavior:contain"
		in:fade={{ duration: 10 }}
		on:mousedown={() => {
			show = false;
		}}
	>
		<div
			style="--m:auto; --radius:1rem; --maxw:100%; --w:32rem; --mx:0.5rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-950); --maxh:100dvh"
	class="shadow-3xl"
			in:flyAndScale
			on:mousedown={(e) => {
				e.stopPropagation();
			}}
		>
			<div style="--px:1.75rem; --py:1.5rem; --d:flex; --fd:column">
				<div style="--size:1.125rem; --weight:600; --dark-c:var(--color-gray-200); --mb:0.625rem">
					{#if title !== ''}
						{title}
					{:else}
						{$i18n.t('Confirm your action')}
					{/if}
				</div>

				<slot>
					<div style="--size:0.875rem; --c:var(--color-gray-500); --fx:1 1 0%">
						{#if message !== ''}
							{@const html = DOMPurify.sanitize(marked.parse(message))}
							{@html html}
						{:else}
							{$i18n.t('This action cannot be undone. Do you wish to continue?')}
						{/if}

						{#if input}
							<textarea
								bind:value={inputValue}
								placeholder={inputPlaceholder ? inputPlaceholder : $i18n.t('Enter your message')}
								style="--w:100%; --mt:0.5rem; --radius:0.5rem; --px:1rem; --py:0.5rem; --size:0.875rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-900); --oe:none; resize:none"
								rows="3"
								required
							/>
						{/if}
					</div>
				</slot>

				<div style="--mt:1.5rem; --d:flex; --jc:space-between; --g:0.375rem">
					<button
						style="--bgc:var(--color-gray-100); --hvr-bgc:var(--color-gray-200); --c:var(--color-gray-800); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --dark-c:#fff; --weight:500; --w:100%; --py:0.625rem; --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={() => {
							show = false;
							dispatch('cancel');
						}}
						type="button"
					>
						{cancelLabel}
					</button>
					<button
						style="--bgc:var(--color-gray-900); --hvr-bgc:var(--color-gray-850); --c:var(--color-gray-100); --dark-bgc:var(--color-gray-100); --hvr-dark-bgc:#fff; --dark-c:var(--color-gray-800); --weight:500; --w:100%; --py:0.625rem; --radius:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
						on:click={() => {
							confirmHandler();
						}}
						type="button"
					>
						{confirmLabel}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

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
