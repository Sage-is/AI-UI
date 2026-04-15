<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';

	import { updateUserById } from '$lib/apis/users';

	import Modal from '$lib/components/common/Modal.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import relativeTime from 'dayjs/plugin/relativeTime';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();
	dayjs.extend(localizedFormat);
	dayjs.extend(relativeTime);

	export let show = false;
	export let selectedUser;
	export let sessionUser;

	let _user = {
		profile_image_url: '',
		role: 'pending',
		name: '',
		email: '',
		password: ''
	};

	let expiresAt = '';

	$: if (_user.role === 'temporary' && _user.info?.temporary?.expires_at) {
		// Convert epoch seconds to datetime-local format
		expiresAt = dayjs(_user.info.temporary.expires_at * 1000).format('YYYY-MM-DDTHH:mm');
	} else if (_user.role === 'temporary' && !_user.info?.temporary?.expires_at) {
		// Default to 24h from now for new temporary users
		expiresAt = dayjs().add(24, 'hour').format('YYYY-MM-DDTHH:mm');
	}

	const submitHandler = async () => {
		const userData = { ..._user };

		// If temporary role, set the expires_at in info
		if (userData.role === 'temporary' && expiresAt) {
			const expiresEpoch = Math.floor(new Date(expiresAt).getTime() / 1000);
			userData.info = {
				...(userData.info || {}),
				temporary: {
					...(userData.info?.temporary || {}),
					expires_at: expiresEpoch
				}
			};
		}

		const res = await updateUserById(localStorage.token, selectedUser.id, userData).catch(
			(error) => {
				toast.error(`${error}`);
			}
		);

		if (res) {
			dispatch('save');
			show = false;
		}
	};

	onMount(() => {
		if (selectedUser) {
			_user = selectedUser;
			_user.password = '';
		}
	});
</script>

<Modal size="sm" bind:show>
	<div style="--bgc: var(--white); --p:1.5rem; --br:1rem; --w:100%; --maxw:500px">
		<div style="--d:flex; --jc:space-between; ">
			<div style="--size:1.125rem; --weight:500; --as:center">{$i18n.t('Edit User')}</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<Icon name="x-mark" strokeWidth="2" className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%;">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<form
					style="--d:flex; --fd:column; --w:100%"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div style="--d:flex; --ai:center; --radius:0.4rem; --py:0.5rem; --w:100%">
						<div style="--as:center; --mr:1.2rem">
							<img
								src={selectedUser.profile_image_url}
								style="--maxw:55px; --objf:cover; --radius:9999px"
								alt="User profile"
							/>
						</div>

						<div>
							<div style="--as:center; --tt:capitalize; --weight:600">{selectedUser.name}</div>

							<div style="--size:0.6rem; --c:var(--color-gray-500)">
								{$i18n.t('Created at')}
								{dayjs(selectedUser.created_at * 1000).format('LL')}
							</div>
						</div>
					</div>

					<div style="--pt:0.6rem; --pb:1.2rem">
						<div style="--d:flex; --fd:column; --g:0.4rem">
							<div style="--d:flex; --fd:column; --w:100%">
								<div style="--mb:0.2rem; --size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Role')}</div>

								<div style="--fx:1 1 0%">
									<select
										style="--w:100%; --dark-bgc:var(--color-gray-900); --size:0.8rem; --bgc:transparent; --oe:none"
	class="disabled:text-gray-500 dark:disabled:text-gray-500"
										bind:value={_user.role}
										disabled={_user.id == sessionUser.id}
										required
									>
										<option value="admin">{$i18n.t('Admin')}</option>
										<option value="facilitator">{$i18n.t('Facilitator')}</option>
										<option value="user">{$i18n.t('User')}</option>
										<option value="temporary">{$i18n.t('Temporary')}</option>
										<option value="pending">{$i18n.t('Pending')}</option>
									</select>
								</div>
							</div>

							{#if _user.role === 'temporary'}
								<div style="--d:flex; --fd:column; --w:100%">
									<div style="--mb:0.2rem; --size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Account Expires')}</div>

									<div style="--fx:1 1 0%">
										<input
											style="--w:100%; --size:0.8rem; --bgc:transparent; --oe:none"
											type="datetime-local"
											bind:value={expiresAt}
										/>
									</div>
									{#if expiresAt}
										<div style="--size:0.625rem; --c:var(--color-gray-500); --mt:0.125rem">
											{dayjs(expiresAt).fromNow()}
											{#if dayjs(expiresAt).isBefore(dayjs())}
												<span style="--c:#ef4444">({$i18n.t('expired')})</span>
											{/if}
										</div>
									{/if}
								</div>
							{/if}

							<div style="--d:flex; --fd:column; --w:100%">
								<div style="--mb:0.2rem; --size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Email')}</div>

								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --size:0.8rem; --bgc:transparent; --oe:none"
	class="disabled:text-gray-500 dark:disabled:text-gray-500"
										type="email"
										bind:value={_user.email}
										placeholder={$i18n.t('Enter Email')}
										autocomplete="off"
										required
									/>
								</div>
							</div>

							<div style="--d:flex; --fd:column; --w:100%">
								<div style="--mb:0.2rem; --size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Name')}</div>

								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --size:0.8rem; --bgc:transparent; --oe:none"
										type="text"
										bind:value={_user.name}
										placeholder={$i18n.t('Enter Name')}
										autocomplete="off"
										required
									/>
								</div>
							</div>

							<div style="--d:flex; --fd:column; --w:100%">
								<div style="--mb:0.2rem; --size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('New Password')}</div>

								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --size:0.8rem; --bgc:transparent; --oe:none"
										type="password"
										placeholder={$i18n.t('Enter New Password')}
										bind:value={_user.password}
										autocomplete="new-password"
									/>
								</div>
							</div>
						</div>

						<div style="--d:flex; --jc:flex-end; --pt:0.6rem; --size:0.8rem; --weight:500">
							<button
								style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.2rem; --ai:center"
								type="submit"
							>
								{$i18n.t('Save')}
							</button>
						</div>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		/* display: none; <- Crashes Chrome on hover */
		-webkit-appearance: none;
		margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
	}

	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}

	input[type='number'] {
		-moz-appearance: textfield; /* Firefox */
	}
</style>
