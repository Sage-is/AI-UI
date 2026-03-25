<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { addUser } from '$lib/apis/auths';
	import { getAllUsers } from '$lib/apis/users';
	import { generateInitialsImage } from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	export let onNext: () => void = () => {};
	export let onBack: () => void = () => {};
	export let onWorkingAlone: () => void = () => {};

	let name = '';
	let email = '';
	let password = '';
	let role = 'user';

	let addedUsers: Array<{ name: string; email: string; role: string }> = [];
	let existingUsersCount = 0;
	let loading = true;
	let csvImporting = false;
	let inputFiles: FileList | null = null;

	/** Fetch non-admin users and update local state */
	const loadUsers = async () => {
		try {
			const res = await getAllUsers(localStorage.token);
			// API returns { users: [...], total: N }
			const users = Array.isArray(res) ? res : (res?.users ?? []);
			const nonAdmin = users.filter((u: any) => u.role !== 'admin');
			existingUsersCount = nonAdmin.length;
			addedUsers = nonAdmin.map((u: any) => ({ name: u.name, email: u.email, role: u.role }));
		} catch (e) {
			console.error('Failed to load users', e);
		}
	};

	onMount(async () => {
		await loadUsers();
		loading = false;
	});

	const handleAddUser = async () => {
		if (!name || !email || !password) {
			toast.error($i18n.t('Please fill in all fields'));
			return;
		}

		try {
			const res = await addUser(localStorage.token, name, email, password, role);
			if (res) {
				toast.success($i18n.t('User added successfully'));
				addedUsers = [...addedUsers, { name, email, role }];
				name = '';
				email = '';
				password = '';
				role = 'user';
			}
		} catch (e) {
			toast.error($i18n.t('Failed to add user: {{error}}', { error: e }));
		}
	};

	const handleCsvImport = async () => {
		if (!inputFiles || inputFiles.length === 0) {
			toast.error($i18n.t('Please select a CSV file'));
			return;
		}

		csvImporting = true;
		const file = inputFiles[0];
		const reader = new FileReader();

		reader.onload = async (e) => {
			const csv = e.target?.result as string;
			const rows = csv.split('\n');
			let importCount = 0;

			for (const [idx, row] of rows.entries()) {
				const columns = row.split(',').map((col) => col.trim());

				if (idx > 0 && columns.length === 4 && columns[0]) {
					if (['admin', 'user', 'pending'].includes(columns[3].toLowerCase())) {
						const res = await addUser(
							localStorage.token,
							columns[0],
							columns[1],
							columns[2],
							columns[3].toLowerCase(),
							generateInitialsImage(columns[0])
						).catch((error) => {
							toast.error($i18n.t('Row {{row}}: {{error}}', { row: idx + 1, error }));
							return null;
						});

						if (res) {
							importCount++;
						}
					} else if (columns[0]) {
						toast.error($i18n.t('Row {{row}}: invalid format.', { row: idx + 1 }));
					}
				}
			}

			if (importCount > 0) {
				toast.success($i18n.t('Successfully imported {{count}} users.', { count: importCount }));
				await loadUsers();
			}

			inputFiles = null;
			const uploadInput = document.getElementById('wizard-upload-user-csv');
			if (uploadInput) {
				(uploadInput as HTMLInputElement).value = '';
			}
			csvImporting = false;
		};

		reader.readAsText(file, 'utf-8');
	};
</script>

<div style="--px:1.2rem; --pt:1rem; --pb:1.5rem">
	<div style="--size:1.2rem; --weight:600; --dark-c:#fff; --mb:0.2rem">
		{$i18n.t('Add Users')}
	</div>
	<div
		style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:1.2rem"
	>
		{$i18n.t('Add team members or choose to work alone.')}
	</div>

	{#if loading}
		<div style="--d:flex; --jc:center; --py:2rem; --size:0.8rem; --c:var(--color-gray-400)">
			{$i18n.t('Loading...')}
		</div>
	{:else}
		<!-- Working Alone Option -->
		<button
			on:click={onWorkingAlone}
			style="--w:100%; --p:0.8rem; --mb:1rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; --bgc:transparent; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --ta:left; --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
		>
			<div style="--size:0.8rem; --weight:600; --m:0.2rem">{$i18n.t("I'm working alone")}</div>
			<div style="--size:0.6rem; --m:0.2rem; --lh:1.2rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
				{$i18n.t('Skip user setup — you can always add users later from Settings')}
			</div>
		</button>

		<!-- Divider -->
		<div style="--d:flex; --ai:center; --g:0.5rem; --mb:1rem">
			<div
				style="--fx:1 1 0%; --h:1px; --bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-700)"
			/>
			<div style="--size:0.65rem; --c:var(--color-gray-400)">{$i18n.t('or')}</div>
			<div
				style="--fx:1 1 0%; --h:1px; --bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-700)"
			/>
		</div>

		<!-- Add User Form -->
		<div style="--d:flex; --fd:column; --g:0.5rem; --mb:1rem">
			<div style="--d:flex; --g:0.5rem">
				<div style="--fx:1 1 0%">
					<div
						style="--size:0.65rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300)"
					>
						{$i18n.t('Name')}
					</div>
					<input
						style="--w:100%; --radius:0.5rem; --py:0.4rem; --px:0.6rem; --size:0.75rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --dark-c:var(--color-gray-300); --oe:none"
						type="text"
						placeholder={$i18n.t('John Doe')}
						bind:value={name}
					/>
				</div>
				<div style="--fx:1 1 0%">
					<div
						style="--size:0.65rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300)"
					>
						{$i18n.t('Email')}
					</div>
					<input
						style="--w:100%; --radius:0.5rem; --py:0.4rem; --px:0.6rem; --size:0.75rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --dark-c:var(--color-gray-300); --oe:none"
						type="email"
						placeholder="john@example.com"
						bind:value={email}
					/>
				</div>
			</div>
			<div style="--d:flex; --g:0.5rem">
				<div style="--fx:1 1 0%">
					<div
						style="--size:0.65rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300)"
					>
						{$i18n.t('Password')}
					</div>
					<input
						style="--w:100%; --radius:0.5rem; --py:0.4rem; --px:0.6rem; --size:0.75rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --dark-c:var(--color-gray-300); --oe:none"
						type="password"
						placeholder={$i18n.t('Password')}
						bind:value={password}
					/>
				</div>
				<div style="--w:6rem">
					<div
						style="--size:0.65rem; --weight:500; --mb:0.2rem; --c:var(--color-gray-600); --dark-c:var(--color-gray-300)"
					>
						{$i18n.t('Role')}
					</div>
					<select
						style="--w:100%; --radius:0.5rem; --py:0.4rem; --px:0.4rem; --size:0.75rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --dark-c:var(--color-gray-300); --oe:none"
						bind:value={role}
					>
						<option value="user">{$i18n.t('user')}</option>
						<option value="facilitator">{$i18n.t('facilitator')}</option>
						<option value="admin">{$i18n.t('admin')}</option>
					</select>
				</div>
				<button
					on:click={handleAddUser}
					style="--as:flex-end; --px:0.6rem; --py:0.4rem; --size:0.7rem; --weight:500; --bgc:var(--color-gray-100); --hvr-bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --radius:0.5rem; --shrink:0; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
				>
					{$i18n.t('Add')}
				</button>
			</div>
		</div>

		<!-- CSV Import -->
		<div style="--d:flex; --ai:center; --g:0.5rem; --mb:1rem">
			<div
				style="--fx:1 1 0%; --h:1px; --bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-700)"
			/>
			<div style="--size:0.65rem; --c:var(--color-gray-400)">{$i18n.t('or import CSV')}</div>
			<div
				style="--fx:1 1 0%; --h:1px; --bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-700)"
			/>
		</div>

		<div style="--mb:1rem">
			<input id="wizard-upload-user-csv" hidden bind:files={inputFiles} type="file" accept=".csv" />

			<div style="--d:flex; --g:0.5rem; --ai:center">
				<button
					style="--fx:1 1 0%; --size:0.75rem; --weight:500; --p:0.5rem; --bgc:transparent; --hvr-bgc:var(--color-gray-100); --dark-hvr-bgc:var(--color-gray-850); --ta:center; --radius:0.5rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:dashed; --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					type="button"
					on:click={() => {
						document.getElementById('wizard-upload-user-csv')?.click();
					}}
				>
					{#if inputFiles && inputFiles.length > 0}
						{inputFiles[0].name}
					{:else}
						{$i18n.t('Click to select a CSV file')}
					{/if}
				</button>

				{#if inputFiles && inputFiles.length > 0}
					<button
						on:click={handleCsvImport}
						disabled={csvImporting}
						style="--px:0.6rem; --py:0.4rem; --size:0.7rem; --weight:500; --bgc:var(--color-gray-100); --hvr-bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-800); --hvr-dark-bgc:var(--color-gray-700); --radius:0.5rem; --shrink:0; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
					>
						{csvImporting ? $i18n.t('Importing...') : $i18n.t('Import')}
					</button>
				{/if}
			</div>

			<div
				style="--mt:0.4rem; --size:0.6rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)"
			>
				{$i18n.t('CSV format: Name, Email, Password, Role.')}
				<a
					href="{WEBUI_BASE_URL}/static/user-import.csv"
					target="_blank"
					style="--td:underline; --dark-c:var(--color-gray-300)"
					on:click|stopPropagation
				>
					{$i18n.t('Download template')}
				</a>
			</div>
		</div>

		<!-- Added Users List -->
		{#if addedUsers.length > 0}
			<div style="--mb:1rem">
				<div style="--size:0.7rem; --weight:500; --mb:0.4rem; --c:var(--color-gray-500)">
					{$i18n.t('Users')} ({addedUsers.length})
					<a
						href="/admin/users"
						target="_blank"
						style="--size:0.65rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-500); --td:underline; --mt:0.2rem; --d:inline-block"
					>
						{$i18n.t('Manage users')}
					</a>
				</div>
				<div
					style="--d:flex; --fd:column; --g:0.3rem; --maxh:8rem; --ofy:auto"
					class="scrollbar-hidden"
				>
					{#each addedUsers as user}
						<div
							style="--d:flex; --jc:space-between; --ai:center; --py:0.3rem; --px:0.5rem; --radius:0.375rem; --bgc:var(--color-gray-50); --dark-bgc:var(--color-gray-850); --size:0.7rem"
						>
							<div style="--d:flex; --g:0.4rem; --ai:center">
								<span style="--weight:500">{user.name}</span>
								<span style="--c:var(--color-gray-400)">{user.email}</span>
							</div>
							<span style="--size:0.6rem; --c:var(--color-gray-400); --tt:capitalize"
								>{user.role}</span
							>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	{/if}

	<div style="--d:flex; --jc:space-between; --ai:center">
		<button
			on:click={onBack}
			style="--px:0.6rem; --py:0.3rem; --size:0.75rem; --c:var(--color-gray-500); --hvr-c:var(--color-gray-700); --dark-hvr-c:var(--color-gray-200)"
		>
			{$i18n.t('Back')}
		</button>

		<button
			on:click={onNext}
			style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
		>
			{$i18n.t('Next')}
		</button>
	</div>
</div>
