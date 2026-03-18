<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';

	import Textarea from '$lib/components/common/Textarea.svelte';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import AccessControl from '../common/AccessControl.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import { user } from '$lib/stores';
	import { slugify } from '$lib/utils';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let onSubmit: Function;
	export let edit = false;
	export let prompt = null;
	export let clone = false;

	const i18n = getContext('i18n');

	let loading = false;

	let title = '';
	let command = '';
	let content = '';

	let accessControl = {};

	let showAccessControlModal = false;

	let hasManualEdit = false;

	$: if (!edit && !hasManualEdit) {
		command = title !== '' ? slugify(title) : '';
	}

	// Track manual edits
	function handleCommandInput(e: Event) {
		hasManualEdit = true;
	}

	const submitHandler = async () => {
		loading = true;

		if (validateCommandString(command)) {
			await onSubmit({
				title,
				command,
				content,
				access_control: accessControl
			});
		} else {
			toast.error(
				$i18n.t('Only alphanumeric characters and hyphens are allowed in the command string.')
			);
		}

		loading = false;
	};

	const validateCommandString = (inputString) => {
		// Regular expression to match only alphanumeric characters and hyphen
		const regex = /^[a-zA-Z0-9-]+$/;

		// Test the input string against the regular expression
		return regex.test(inputString);
	};

	onMount(async () => {
		if (prompt) {
			title = prompt.title;
			await tick();

			command = prompt.command.at(0) === '/' ? prompt.command.slice(1) : prompt.command;
			content = prompt.content;

			accessControl = prompt?.access_control === undefined ? {} : prompt?.access_control;
		}
	});
</script>

<AccessControlModal
	bind:show={showAccessControlModal}
	bind:accessControl
	accessRoles={['read', 'write']}
	allowPublic={$user?.permissions?.sharing?.public_prompts || $user?.role === 'admin'}
/>

<div style="--w:100%; --maxh:100%; --d:flex; --jc:center">
	<form
		style="--d:flex; --fd:column; --w:100%; --mb:2.5rem"
		on:submit|preventDefault={() => {
			submitHandler();
		}}
	>
		<div style="--my:0.5rem">
			<Tooltip
				content={`${$i18n.t('Only alphanumeric characters and hyphens are allowed')} - ${$i18n.t(
					'Activate this command by typing "/{{COMMAND}}" to chat input.',
					{
						COMMAND: command
					}
				)}`}
				placement="bottom-start"
			>
				<div style="--d:flex; --fd:column; --w:100%">
					<div style="--d:flex; --ai:center">
						<input
							style="--size:1.5rem; --weight:600; --w:100%; --bgc:transparent; --oe:none"
							placeholder={$i18n.t('Title')}
							bind:value={title}
							required
						/>

						<div style="--as:center; --fs:0">
							<button
								style="--bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --c:#000; --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --px:0.5rem; --py:0.25rem; --radius:9999px; --d:flex; --g:0.25rem; --ai:center"
								type="button"
								on:click={() => {
									showAccessControlModal = true;
								}}
							>
								<LockClosed strokeWidth="2.5" className="size-3.5" />

								<div style="--size:0.875rem; --weight:500; --fs:0">
									{$i18n.t('Access')}
								</div>
							</button>
						</div>
					</div>

					<div style="--d:flex; --g:0.125rem; --ai:center; --size:0.6rem; --c:var(--color-gray-500)">
						<div class="">/</div>
						<input
							style="--w:100%; --bgc:transparent; --oe:none"
							placeholder={$i18n.t('Command')}
							bind:value={command}
							on:input={handleCommandInput}
							required
							disabled={edit}
						/>
					</div>
				</div>
			</Tooltip>
		</div>

		<div style="--my:0.5rem">
			<div style="--d:flex; --w:100%; --jc:space-between">
				<div style="--as:center; --size:0.875rem; --weight:600">{$i18n.t('Prompt Content')}</div>
			</div>

			<div style="--mt:0.5rem">
				<div>
					<Textarea
						className="text-sm w-full bg-transparent outline-hidden overflow-y-hidden resize-none"
						placeholder={$i18n.t('Write a summary in 50 words that summarizes [topic or keyword].')}
						bind:value={content}
						rows={6}
						required
					/>
				</div>

				<div style="--size:0.6rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
					ⓘ {$i18n.t('Format your variables using brackets like this:')}&nbsp;<span
						style="--c:var(--color-gray-600); --dark-c:var(--color-gray-300); --weight:500"
						>{'{{'}{$i18n.t('variable')}{'}}'}</span
					>.
					{$i18n.t('Make sure to enclose them with')}
					<span style="--c:var(--color-gray-600); --dark-c:var(--color-gray-300); --weight:500">{'{{'}</span>
					{$i18n.t('and')}
					<span style="--c:var(--color-gray-600); --dark-c:var(--color-gray-300); --weight:500">{'}}'}</span>.
				</div>

				<div style="--size:0.6rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500); --td:underline">
					<a href="https://docs.sage.is/features/workshop/prompts" target="_blank">
						{$i18n.t('To learn more about powerful prompt variables, click here')}
					</a>
				</div>
			</div>
		</div>

		<div style="--my:1rem; --d:flex; --jc:flex-end; --pb:5rem">
			<button
				style="--size:0.875rem; --w:100%; --w-lg:fit-content; --px:1rem; --py:0.5rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem; --d:flex; --w:100%; --jc:center"
	class="{loading
					? ' cursor-not-allowed bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black'
					: 'bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black'}"
				type="submit"
				disabled={loading}
			>
				<div style="--as:center; --weight:500">{$i18n.t('Save & Create')}</div>

				{#if loading}
					<div style="--ml:0.375rem; --as:center">
						<Spinner />
					</div>
				{/if}
			</button>
		</div>
	</form>
</div>
