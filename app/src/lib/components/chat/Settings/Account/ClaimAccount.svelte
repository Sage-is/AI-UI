<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import { user, config } from '$lib/stores';
	import { claimAccount, getSessionUser } from '$lib/apis/auths';

	dayjs.extend(relativeTime);

	const i18n = getContext('i18n');

	let email = '';
	let password = '';
	let passwordConfirm = '';
	let loading = false;
	let now = dayjs();
	let timer: ReturnType<typeof setInterval>;

	$: tempInfo = $user?.info?.temporary ?? {};
	$: claimed = tempInfo.claimed === true;
	$: expiresAt = tempInfo.expires_at ? dayjs(tempInfo.expires_at * 1000) : null;
	$: expired = expiresAt ? expiresAt.isBefore(now) : false;
	$: timeRemaining = expiresAt ? expiresAt.from(now, true) : null;
	$: signupEnabled = $config?.features?.enable_signup ?? false;

	const claimHandler = async () => {
		if (password !== passwordConfirm) {
			toast.error($i18n.t("The passwords you entered don't quite match. Please double-check and try again."));
			password = '';
			passwordConfirm = '';
			return;
		}

		if (password.length < 8) {
			toast.error($i18n.t('Password must be at least 8 characters'));
			return;
		}

		loading = true;

		try {
			const res = await claimAccount(email, password);

			if (res) {
				toast.success($i18n.t('Account claimed! Your request is now under review.'));

				const sessionUser = await getSessionUser().catch(() => null);
				if (sessionUser) {
					await user.set(sessionUser);
				}
			}
		} catch (error: any) {
			toast.error(`${error.detail || error}`);
		} finally {
			loading = false;
		}
	};

	onMount(() => {
		timer = setInterval(() => {
			now = dayjs();
		}, 30000);
	});

	onDestroy(() => {
		if (timer) clearInterval(timer);
	});
</script>

<div style="--d:flex; --fd:column; --g:0.5rem; --size:0.8rem">
	<!-- Countdown timer - always shown for temp accounts with expiry -->
	{#if expiresAt}
		<div style="--d:flex; --ai:center; --g:0.5rem">
			<div style="--size:0.6rem; --weight:500; {expired ? '--c:#ef4444' : '--c:var(--color-gray-500)'}">
				{#if expired}
					{$i18n.t('Your temporary access has expired')}
				{:else}
					{$i18n.t('Temporary access expires in')}
					<span style="--weight:600; --c:var(--color-gray-900); --dark-c:#fff">{timeRemaining}</span>
				{/if}
			</div>
		</div>
	{/if}

	{#if claimed}
		<!-- State: Claimed, awaiting review -->
		<div style="--d:flex; --fd:column; --g:0.2rem">
			<div style="--weight:600; --size:0.8rem; --c:var(--color-gray-900); --dark-c:#fff">
				{$i18n.t('Account Under Review')}
			</div>
			<div style="--size:0.6rem; --c:var(--color-gray-500)">
				{$i18n.t("Your account claim has been submitted and is awaiting approval. You can continue using the app during your remaining demo period. Once approved, you'll have full permanent access.")}
			</div>
			{#if expiresAt && !expired}
				<div style="--size:0.6rem; --c:var(--color-gray-500); --mt:0.2rem">
					{$i18n.t('If your demo period ends before approval, your access may be paused until an administrator reviews your account.')}
				</div>
			{/if}
		</div>
	{:else if signupEnabled}
		<!-- State: Not claimed, signups enabled - show claim form -->
		<form
			style="--d:flex; --fd:column"
			on:submit|preventDefault={claimHandler}
		>
			<div style="--d:flex; --fd:column; --g:0.2rem; --mb:0.5rem">
				<div style="--weight:600; --size:0.8rem; --c:var(--color-gray-900); --dark-c:#fff">
					{$i18n.t('Set Up Permanent Account')}
				</div>
				<div style="--size:0.6rem; --c:var(--color-gray-500)">
					{$i18n.t('You have a temporary account. Set an email and password so you can sign in again and request permanent access.')}
				</div>
			</div>

			<div style="--d:flex; --fd:column; --g:0.4rem; --py:0.4rem">
				<div style="--d:flex; --fd:column; --w:100%">
					<div style="--mb:0.2rem; --size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Email')}</div>
					<div style="--fx:1 1 0%">
						<input
							style="--w:100%; --bgc:transparent; --dark-c:var(--color-gray-300); --oe:none"
							class="placeholder:opacity-30"
							type="email"
							bind:value={email}
							placeholder={$i18n.t('Enter your email')}
							autocomplete="email"
							required
						/>
					</div>
				</div>

				<div style="--d:flex; --fd:column; --w:100%">
					<div style="--mb:0.2rem; --size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Password')}</div>
					<div style="--fx:1 1 0%">
						<input
							style="--w:100%; --bgc:transparent; --size:0.8rem; --dark-c:var(--color-gray-300); --oe:none"
							class="placeholder:opacity-30"
							type="password"
							bind:value={password}
							placeholder={$i18n.t('Enter a password')}
							autocomplete="new-password"
							required
						/>
					</div>
				</div>

				<div style="--d:flex; --fd:column; --w:100%">
					<div style="--mb:0.2rem; --size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Confirm Password')}</div>
					<div style="--fx:1 1 0%">
						<input
							style="--w:100%; --bgc:transparent; --size:0.8rem; --dark-c:var(--color-gray-300); --oe:none"
							class="placeholder:opacity-30"
							type="password"
							bind:value={passwordConfirm}
							placeholder={$i18n.t('Confirm your password')}
							autocomplete="off"
							required
						/>
					</div>
				</div>
			</div>

			<div style="--mt:0.5rem; --d:flex; --jc:flex-end">
				<button
					style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
					type="submit"
					disabled={loading}
				>
					{$i18n.t('Claim Account')}
				</button>
			</div>
		</form>
	{:else}
		<!-- State: Not claimed, signups disabled - countdown only -->
		<div style="--d:flex; --fd:column; --g:0.2rem">
			<div style="--weight:600; --size:0.8rem; --c:var(--color-gray-900); --dark-c:#fff">
				{$i18n.t('Temporary Account')}
			</div>
			<div style="--size:0.6rem; --c:var(--color-gray-500)">
				{$i18n.t('You are using a temporary account. New account registration is currently closed. Please contact an administrator if you would like to request permanent access.')}
			</div>
		</div>
	{/if}
</div>
