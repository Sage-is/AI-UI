<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { updateUserPassword } from '$lib/apis/auths';

	const i18n = getContext('i18n');

	let show = false;
	let currentPassword = '';
	let newPassword = '';
	let newPasswordConfirm = '';

	const updatePasswordHandler = async () => {
		if (newPassword === newPasswordConfirm) {
			const res = await updateUserPassword(currentPassword, newPassword).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				toast.success($i18n.t('Successfully updated.'));
			}

			currentPassword = '';
			newPassword = '';
			newPasswordConfirm = '';
		} else {
			toast.error(
				`The passwords you entered don't quite match. Please double-check and try again.`
			);
			newPassword = '';
			newPasswordConfirm = '';
		}
	};
</script>

<form
	style="--d:flex; --fd:column; --size:0.875rem"
	on:submit|preventDefault={() => {
		updatePasswordHandler();
	}}
>
	<div style="--d:flex; --jc:space-between; --ai:center; --size:0.875rem">
		<div style="--weight:500">{$i18n.t('Change Password')}</div>
		<button
			style="--size:0.75rem; --weight:500; --c:var(--color-gray-500)"
			type="button"
			on:click={() => {
				show = !show;
			}}>{show ? $i18n.t('Hide') : $i18n.t('Show')}</button
		>
	</div>

	{#if show}
		<div style="--py:0.625rem; --g:0.375rem">
			<div style="--d:flex; --fd:column; --w:100%">
				<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500)">{$i18n.t('Current Password')}</div>

				<div style="--fx:1 1 0%">
					<input
						style="--w:100%; --bgc:transparent; --dark-c:var(--color-gray-300); --oe:none"
	class="placeholder:opacity-30"
						type="password"
						bind:value={currentPassword}
						placeholder={$i18n.t('Enter your current password')}
						autocomplete="current-password"
						required
					/>
				</div>
			</div>

			<div style="--d:flex; --fd:column; --w:100%">
				<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500)">{$i18n.t('New Password')}</div>

				<div style="--fx:1 1 0%">
					<input
						style="--w:100%; --bgc:transparent; --size:0.875rem; --dark-c:var(--color-gray-300); --oe:none"
	class="placeholder:opacity-30"
						type="password"
						bind:value={newPassword}
						placeholder={$i18n.t('Enter your new password')}
						autocomplete="new-password"
						required
					/>
				</div>
			</div>

			<div style="--d:flex; --fd:column; --w:100%">
				<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500)">{$i18n.t('Confirm Password')}</div>

				<div style="--fx:1 1 0%">
					<input
						style="--w:100%; --bgc:transparent; --size:0.875rem; --dark-c:var(--color-gray-300); --oe:none"
	class="placeholder:opacity-30"
						type="password"
						bind:value={newPasswordConfirm}
						placeholder={$i18n.t('Confirm your new password')}
						autocomplete="off"
						required
					/>
				</div>
			</div>
		</div>

		<div style="--mt:0.75rem; --d:flex; --jc:flex-end">
			<button
				style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			>
				{$i18n.t('Update password')}
			</button>
		</div>
	{/if}
</form>
