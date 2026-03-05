<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { updateUserPassword } from '$lib/apis/auths';

	const i18n = getContext('i18n');

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
				$i18n.t(`The passwords you entered don't quite match. Please double-check and try again.`)
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
	<details>
		<summary style="--d:flex; --ai:center; --g:0.5rem; --cur:pointer; --us:none; --py:0.25rem;">
			<span style="--weight:500">{$i18n.t('Password')}</span>
			<details style="--d:inline; --size:0.75rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500); --w: 80%; --b:0;
					--m: auto;"
				on:click|stopPropagation
			>
				<summary style="--cur:pointer; --us:none;">
					{$i18n.t('Why change my password?')} &#9662;
				</summary>
				<div style="--mt:0.375rem; --lh:1.5; --size:0.8rem">
					<p style="--mb:0.375rem">
						{$i18n.t('Changing your password regularly helps keep your account secure — especially if you think someone else may have seen it, or if you used the same password on another site that was compromised.')}
					</p>
					<p>
						{$i18n.t("Pick something you haven't used before, and make sure it's hard to guess. A mix of words, numbers, and symbols works well — or try a passphrase like a short sentence only you would know.")}
					</p>
				</div>
			</details>
			<span style="--ml:auto; --size:0.75rem; --weight:500; --c:var(--color-gray-400)">&#9662;</span>
		</summary>

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
				style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:background-color 150ms; --radius:9999px"
			>
				{$i18n.t('Update password')}
			</button>
		</div>
	</details>
</form>
