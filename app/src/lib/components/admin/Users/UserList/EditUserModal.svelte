<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';

	import { updateUserById } from '$lib/apis/users';

	import Modal from '$lib/components/common/Modal.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import XMark from '$lib/components/icons/XMark.svelte';

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
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300, #cdcdcd); --px:1.25rem; --pt:1rem; --pb:0.5rem">
			<div style="--size:1.125rem; --weight:500; --as:center">{$i18n.t('Edit User')}</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --g-md:1rem; --dark-c:var(--color-gray-200, #e3e3e3)">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<form
					style="--d:flex; --fd:column; --w:100%"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div style="--d:flex; --ai:center; --radius:0.375rem; --px:1.25rem; --py:0.5rem; --w:100%">
						<div style="--as:center; --mr:1.25rem">
							<img
								src={selectedUser.profile_image_url}
								style="--maxw:55px; --objf:cover; --radius:9999px"
								alt="User profile"
							/>
						</div>

						<div>
							<div style="--as:center; --tt:capitalize; --weight:600">{selectedUser.name}</div>

							<div style="--size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">
								{$i18n.t('Created at')}
								{dayjs(selectedUser.created_at * 1000).format('LL')}
							</div>
						</div>
					</div>

					<div style="--px:1.25rem; --pt:0.75rem; --pb:1.25rem">
						<div style="--d:flex; --fd:column; --g:0.375rem">
							<div style="--d:flex; --fd:column; --w:100%">
								<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">{$i18n.t('Role')}</div>

								<div style="--fx:1 1 0%">
									<select
										style="--w:100%; --dark-bgc:var(--color-gray-900, #171717); --size:0.875rem; --bgc:transparent; --oe:none"
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
									<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">{$i18n.t('Account Expires')}</div>

									<div style="--fx:1 1 0%">
										<input
											style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
											type="datetime-local"
											bind:value={expiresAt}
										/>
									</div>
									{#if expiresAt}
										<div style="--size:0.625rem; --c:var(--color-gray-500, #9b9b9b); --mt:0.125rem">
											{dayjs(expiresAt).fromNow()}
											{#if dayjs(expiresAt).isBefore(dayjs())}
												<span style="--c:#ef4444">({$i18n.t('expired')})</span>
											{/if}
										</div>
									{/if}
								</div>
							{/if}

							<div style="--d:flex; --fd:column; --w:100%">
								<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">{$i18n.t('Email')}</div>

								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
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
								<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">{$i18n.t('Name')}</div>

								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
										type="text"
										bind:value={_user.name}
										placeholder={$i18n.t('Enter Name')}
										autocomplete="off"
										required
									/>
								</div>
							</div>

							<div style="--d:flex; --fd:column; --w:100%">
								<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">{$i18n.t('New Password')}</div>

								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
										type="password"
										placeholder={$i18n.t('Enter New Password')}
										bind:value={_user.password}
										autocomplete="new-password"
									/>
								</div>
							</div>
						</div>

						<div style="--d:flex; --jc:flex-end; --pt:0.75rem; --size:0.875rem; --weight:500">
							<button
								style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900, #171717); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100, #ececec); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.25rem; --ai:center"
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
