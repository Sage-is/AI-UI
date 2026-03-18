<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';
	import { addUser } from '$lib/apis/auths';

	import { WEBUI_BASE_URL } from '$lib/constants';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import { generateInitialsImage } from '$lib/utils';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	let loading = false;
	let tab = '';
	let inputFiles;

	let _user = {
		name: '',
		email: '',
		password: '',
		role: 'user'
	};

	$: if (show) {
		_user = {
			name: '',
			email: '',
			password: '',
			role: 'user'
		};
	}

	const submitHandler = async () => {
		const stopLoading = () => {
			dispatch('save');
			loading = false;
		};

		if (tab === '') {
			loading = true;

			const res = await addUser(
				localStorage.token,
				_user.name,
				_user.email,
				_user.password,
				_user.role,
				generateInitialsImage(_user.name)
			).catch((error) => {
				toast.error(`${error}`);
			});

			if (res) {
				stopLoading();
				show = false;
			}
		} else {
			if (inputFiles) {
				loading = true;

				const file = inputFiles[0];
				const reader = new FileReader();

				reader.onload = async (e) => {
					const csv = e.target.result;
					const rows = csv.split('\n');

					let userCount = 0;

					for (const [idx, row] of rows.entries()) {
						const columns = row.split(',').map((col) => col.trim());
						console.debug(idx, columns);

						if (idx > 0) {
							if (
								columns.length === 4 &&
								['admin', 'user', 'pending'].includes(columns[3].toLowerCase())
							) {
								const res = await addUser(
									localStorage.token,
									columns[0],
									columns[1],
									columns[2],
									columns[3].toLowerCase(),
									generateInitialsImage(columns[0])
								).catch((error) => {
									toast.error(`Row ${idx + 1}: ${error}`);
									return null;
								});

								if (res) {
									userCount = userCount + 1;
								}
							} else {
								toast.error(`Row ${idx + 1}: invalid format.`);
							}
						}
					}

					toast.success(`Successfully imported ${userCount} users.`);
					inputFiles = null;
					const uploadInputElement = document.getElementById('upload-user-csv-input');

					if (uploadInputElement) {
						uploadInputElement.value = null;
					}

					stopLoading();
				};

				reader.readAsText(file, 'utf-8');
			} else {
				toast.error($i18n.t('File not found.'));
			}
		}

		loading = false;
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-300); --px:1.25rem; --pt:1rem; --pb:0.5rem">
			<div style="--size:1.125rem; --weight:500; --as:center">{$i18n.t('Add User')}</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1rem; --pb:0.6rem; --p: 1rem 0;--bgc: var(--white); --br: 1rem">
			<div style="--d:flex; --fd:column; --w:100%; --fd-sm:row; --jc-sm:center; --g-sm:1.5rem">
				<form
					style="--d:flex; --fd:column; --w:100%"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div
						style="--d:flex; --mt:-0.5rem; --mb:0.375rem; --g:0.25rem; --ofx:auto; --w:fit-content; --ta:center; --size:0.875rem; --weight:500; --radius:9999px; --bgc:transparent; --dark-c:var(--color-gray-200)"
	class="scrollbar-none"
					>
						<button
							style="--minw:fit-content; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{tab === ''
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
							type="button"
							on:click={() => {
								tab = '';
							}}>{$i18n.t('Form')}</button
						>

						<button
							style="--minw:fit-content; --p:0.375rem; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)"
	class="{tab === 'import'
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
							type="button"
							on:click={() => {
								tab = 'import';
							}}>{$i18n.t('CSV Import')}</button
						>
					</div>

					<div style="--px:0.25rem">
						{#if tab === ''}
							<div style="--d:flex; --fd:column; --w:100%; --mb:0.6rem">
								<div style="--mb:0.25rem; --size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Role')}</div>

								<div style="--fx:1 1 0%">
									<select
										style="--w:100%; --tt:capitalize; --radius:0.5rem; --size:0.875rem; --bgc:transparent; --oe:none"
	class="dark:disabled:text-gray-500"
										bind:value={_user.role}
										placeholder={$i18n.t('Enter Role')}
										required
									>
										<option value="pending"> {$i18n.t('pending')} </option>
										<option value="user"> {$i18n.t('user')} </option>
										<option value="facilitator"> {$i18n.t('facilitator')} </option>
										<option value="temporary"> {$i18n.t('temporary')} </option>
										<option value="admin"> {$i18n.t('admin')} </option>
									</select>
								</div>
							</div>

							<div style="--d:flex; --fd:column; --w:100%; --mt:0.25rem">
								<div style="--mb:0.25rem; --size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Name')}</div>

								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
	class="disabled:text-gray-500 dark:disabled:text-gray-500"
										type="text"
										bind:value={_user.name}
										placeholder={$i18n.t('Enter Full Name')}
										autocomplete="off"
										required
									/>
								</div>
							</div>

							<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.625rem; --w:100%" />

							<div style="--d:flex; --fd:column; --w:100%">
								<div style="--mb:0.25rem; --size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Email')}</div>

								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
	class="disabled:text-gray-500 dark:disabled:text-gray-500"
										type="email"
										bind:value={_user.email}
										placeholder={$i18n.t('Enter Email')}
										required
									/>
								</div>
							</div>

							<div style="--d:flex; --fd:column; --w:100%; --mt:0.25rem">
								<div style="--mb:0.25rem; --size:0.6rem; --c:var(--color-gray-500)">{$i18n.t('Password')}</div>

								<div style="--fx:1 1 0%">
									<input
										style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
	class="disabled:text-gray-500 dark:disabled:text-gray-500"
										type="password"
										bind:value={_user.password}
										placeholder={$i18n.t('Enter Password')}
										autocomplete="off"
									/>
								</div>
							</div>
						{:else if tab === 'import'}
							<div>
								<div style="--mb:0.6rem; --w:100%">
									<input
										id="upload-user-csv-input"
										hidden
										bind:files={inputFiles}
										type="file"
										accept=".csv"
									/>

									<button
										style="--w:100%; --size:0.875rem; --weight:500; --py:0.6rem; --bgc:transparent; --hvr-bgc:var(--color-gray-100);  --bs:dashed; --dark-bc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-850); --ta:center; --radius:0.6rem"
										type="button"
										on:click={() => {
											document.getElementById('upload-user-csv-input')?.click();
										}}
									>
										{#if inputFiles}
											{inputFiles.length > 0 ? `${inputFiles.length}` : ''} document(s) selected.
										{:else}
											{$i18n.t('Click here to select a csv file.')}
										{/if}
									</button>
								</div>

								<div style="--size:0.6rem; --c:var(--color-gray-500)">
									ⓘ {$i18n.t(
										'Ensure your CSV file includes 4 columns in this order: Name, Email, Password, Role.'
									)}
									<a
										style="--td:underline; --dark-c:var(--color-gray-200)"
										href="{WEBUI_BASE_URL}/static/user-import.csv"
									>
										{$i18n.t('Click here to download user import template file.')}
									</a>
								</div>
							</div>
						{/if}
					</div>

					<div style="--d:flex; --jc:flex-end; --pt:0.6rem; --size:0.875rem; --weight:500">
						<button
							style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px; --d:flex; --fd:row; --g:0.25rem; --ai:center"
	class="{loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Save')}

							{#if loading}
								<div style="--ml:0.5rem; --as:center">
									<Spinner />
								</div>
							{/if}
						</button>
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
