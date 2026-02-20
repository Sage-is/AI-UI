<script lang="ts">
	import { getAdminDetails } from '$lib/apis/auths';
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { userSignOut } from '$lib/apis/auths';

	const i18n = getContext('i18n');

	let adminDetails = null;

	$: tempInfo = $user?.info?.temporary ?? {};
	$: claimed = tempInfo.claimed === true;

	onMount(async () => {
		adminDetails = await getAdminDetails(localStorage.token).catch((err) => {
			console.error(err);
			return null;
		});
	});
</script>

<div style="--pos:fixed; --w:100%; --h:100%; --d:flex; --z:999">
	<div
		style="--pos:absolute; --w:100%; --h:100%; backdrop-filter:blur(16px); --bgc:rgb(255 255 255 / 0.1); --dark-bgc:rgb(23 23 23 / 0.5); --d:flex; --jc:center"
	>
		<div style="--m:auto; --pb:2.5rem; --d:flex; --fd:column; --jc:center">
			<div style="--maxw:28rem">
				<div style="--ta:center; --dark-c:#fff; --size:1.5rem; --weight:500; --z:50">
					{#if claimed}
						{$i18n.t('Demo Period Ended')}
					{:else}
						{$i18n.t('Temporary Access Expired')}
					{/if}
				</div>

				<div
					style="--mt:1rem; --ta:center; --size:0.875rem; --dark-c:var(--color-gray-200, #e3e3e3); --w:100%"
				>
					{#if claimed}
						{$i18n.t(
							'Your demo period has ended, but your account claim is still being reviewed. An administrator will be in touch once your account has been approved.'
						)}
					{:else}
						{$i18n.t(
							"Your temporary access has expired. If you'd like to continue using this service, please contact an administrator to request a permanent account."
						)}
					{/if}
				</div>

				{#if adminDetails}
					<div style="--mt:1rem; --size:0.875rem; --weight:500; --ta:center">
						<div>{$i18n.t('Admin')}: {adminDetails.name} ({adminDetails.email})</div>
					</div>
				{/if}

				<div style="--mt:1.5rem; --mx:auto; --pos:relative; --w:fit-content" class="group">
					<button
						style="--pos:relative; --z:20; --d:flex; --px:1.25rem; --py:0.5rem; --radius:9999px; --bgc:#fff; --b:1px solid; --bc:var(--color-gray-100, #ececec); --dark-bs:none; --hvr-bgc:var(--color-gray-100, #ececec); --c:var(--color-gray-700, #4e4e4e); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --weight:500; --size:0.875rem"
						on:click={async () => {
							location.href = '/';
						}}
					>
						{$i18n.t('Check Again')}
					</button>

					<button
						style="--size:0.75rem; --ta:center; --w:100%; --mt:0.5rem; --c:var(--color-gray-400, #b4b4b4); --td:underline"
						on:click={async () => {
							await userSignOut();
							user.set(undefined);
							location.href = '/auth';
						}}>{$i18n.t('Sign Out')}</button
					>
				</div>
			</div>
		</div>
	</div>
</div>
