<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';

	import { user, config, settings } from '$lib/stores';
	import { updateUserProfile, createAPIKey, getAPIKey, getSessionUser } from '$lib/apis/auths';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import UpdatePassword from './Account/UpdatePassword.svelte';
	import ClaimAccount from './Account/ClaimAccount.svelte';
	import { getGravatarUrl } from '$lib/apis/utils';
	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';
	import { copyToClipboard } from '$lib/utils';
		import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;
	export let saveSettings: Function;

	let profileImageUrl = '';
	let name = '';

	let webhookUrl = '';

	let JWTTokenCopied = false;

	let APIKey = '';
	let APIKeyCopied = false;
	let profileImageInputElement: HTMLInputElement;

	const submitHandler = async () => {
		if (name !== $user?.name) {
			if (profileImageUrl === generateInitialsImage($user?.name) || profileImageUrl === '') {
				profileImageUrl = generateInitialsImage(name);
			}
		}

		if (webhookUrl !== $settings?.notifications?.webhook_url) {
			saveSettings({
				notifications: {
					...$settings.notifications,
					webhook_url: webhookUrl
				}
			});
		}

		const updatedUser = await updateUserProfile(name, profileImageUrl).catch((error) => {
			toast.error(`${error}`);
		});

		if (updatedUser) {
			// Get Session User Info
			const sessionUser = await getSessionUser().catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			await user.set(sessionUser);
			return true;
		}
		return false;
	};

	const createAPIKeyHandler = async () => {
		APIKey = await createAPIKey();
		if (APIKey) {
			toast.success($i18n.t('API Key created.'));
		} else {
			toast.error($i18n.t('Failed to create API Key.'));
		}
	};

	onMount(async () => {
		name = $user?.name;
		profileImageUrl = $user?.profile_image_url;
		webhookUrl = $settings?.notifications?.webhook_url ?? '';

		APIKey = await getAPIKey().catch((error) => {
			console.log(error);
			return '';
		});
	});
</script>

<div id="tab-account" style="--d:flex; --fd:column; --h:100%; --jc:space-between; --size:0.8rem">
	<div style="--ofy:scroll; --maxh:28rem; --maxh-lg:100%">
		<input
			id="profile-image-input"
			bind:this={profileImageInputElement}
			type="file"
			hidden
			accept="image/*"
			on:change={(e) => {
				const files = profileImageInputElement.files ?? [];
				let reader = new FileReader();
				reader.onload = (event) => {
					let originalImageUrl = `${event.target.result}`;

					const img = new Image();
					img.src = originalImageUrl;

					img.onload = function () {
						const canvas = document.createElement('canvas');
						const ctx = canvas.getContext('2d');

						// Calculate the aspect ratio of the image
						const aspectRatio = img.width / img.height;

						// Calculate the new width and height to fit within 250x250
						let newWidth, newHeight;
						if (aspectRatio > 1) {
							newWidth = 250 * aspectRatio;
							newHeight = 250;
						} else {
							newWidth = 250;
							newHeight = 250 / aspectRatio;
						}

						// Set the canvas size
						canvas.width = 250;
						canvas.height = 250;

						// Calculate the position to center the image
						const offsetX = (250 - newWidth) / 2;
						const offsetY = (250 - newHeight) / 2;

						// Draw the image on the canvas
						ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

						// Get the base64 representation of the compressed image
						const compressedSrc = canvas.toDataURL('image/jpeg');

						// Display the compressed image
						profileImageUrl = compressedSrc;

						profileImageInputElement.files = null;
					};
				};

				if (
					files.length > 0 &&
					['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(files[0]['type'])
				) {
					reader.readAsDataURL(files[0]);
				}
			}}
		/>

		<div style="--g:0.2rem">
			<!-- <div style="--size:0.8rem; --weight:500">{$i18n.t('Account')}</div> -->

			<div style="--d:flex; --g:1.2rem">
				<div style="--d:flex; --fd:column">
					<div style="--as:center; --mt:0.5rem">
						<button
							style="--pos:relative; --radius:9999px; --dark-bgc:var(--color-gray-700)"
							type="button"
							on:click={() => {
								profileImageInputElement.click();
							}}
						>
							<img
								src={profileImageUrl !== '' ? profileImageUrl : generateInitialsImage(name)}
								alt="profile"
								style="--radius:9999px; --w:4rem; --h:4rem; --objf:cover"
							/>

							<div
								style="--pos:absolute; --d:flex; --jc:center; --radius:9999px; --bottom:0; --left:0; --right:0; --top:0; --h:100%; --w:100%; --of:hidden; --bgc:var(--color-gray-700); --op:0; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --tdn:300ms; --ttf:cubic-bezier(0.4, 0, 0.2, 1); --hvr-op:0.5"
								class="bg-fixed"
							>
								<div style="--my:auto; --c:var(--color-gray-100)">
									<Icon name="pencil-fill-20" className="size-[1.2rem]" />
								</div>
							</div>
						</button>
					</div>
				</div>

				<div style="--fx:1 1 0%; --d:flex; --fd:column; --as:center; --g:0.125rem">
					<div style="--mb:0.125rem; --size:0.8rem; --weight:500">{$i18n.t('Profile Image')}</div>

					<div style="--d:flex; --g:0.4rem">
						<button
							style="--size:0.6rem; --ta:center; --c:var(--color-gray-800); --dark-c:var(--color-gray-400); --radius:9999px; --px:1rem; --py:0.125rem; --bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-850)"
							on:click={async () => {
								if (canvasPixelTest()) {
									profileImageUrl = generateInitialsImage(name);
								} else {
									toast.info(
										$i18n.t(
											'Fingerprint spoofing detected: Unable to use initials as avatar. Defaulting to default profile image.'
										),
										{
											duration: 1000 * 10
										}
									);
								}
							}}>{$i18n.t('Use Initials')}</button
						>

						<button
							style="--size:0.6rem; --ta:center; --c:var(--color-gray-800); --dark-c:var(--color-gray-400); --radius:9999px; --px:1rem; --py:0.125rem; --bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-850)"
							on:click={async () => {
								const url = await getGravatarUrl(localStorage.token, $user?.email);

								profileImageUrl = url;
							}}>{$i18n.t('Use Gravatar')}</button
						>

						<button
							style="--size:0.6rem; --ta:center; --c:var(--color-gray-800); --dark-c:var(--color-gray-400); --radius:0.5rem; --px:0.5rem; --py:0.2rem"
							on:click={async () => {
								profileImageUrl = `${WEBUI_BASE_URL}/static/user.png`;
							}}>{$i18n.t('Remove')}</button
						>
					</div>
				</div>
			</div>

			<div style="--pt:0.125rem">
				<div style="--d:flex; --fd:column; --w:100%">
					<div style="--mb:0.2rem; --size:0.6rem; --weight:500">{$i18n.t('Name')}</div>

					<div style="--fx:1 1 0%">
						<input
							style="--w:100%; --size:0.8rem; --dark-c:var(--color-gray-300); --bgc:transparent; --oe:none"
							type="text"
							bind:value={name}
							required
							placeholder={$i18n.t('Enter your name')}
						/>
					</div>
				</div>
			</div>

			{#if $config?.features?.enable_user_webhooks}
				<div style="--pt:0.5rem">
					<div style="--d:flex; --fd:column; --w:100%">
						<div style="--mb:0.2rem; --size:0.6rem; --weight:500">
							{$i18n.t('Notification Webhook')}
						</div>

						<div style="--fx:1 1 0%">
							<input
								style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
								type="url"
								placeholder={$i18n.t('Enter your webhook URL')}
								bind:value={webhookUrl}
								required
							/>
						</div>
					</div>
				</div>
			{/if}
		</div>

		<hr style="--bc:var(--color-gray-50); --dark-bc:var(--color-gray-850); --my:0.5rem" />

		{#if $user?.role === 'temporary'}
			<div
				style="--my:0.5rem; --p:0.6rem; --radius:0.6rem; --bgc:#fefce8; --dark-bgc:rgb(66 32 6 / 0.3);  --bc:#fde047; --dark-bc:rgb(161 98 7 / 0.5)"
			>
				<ClaimAccount />
			</div>
		{:else}
			<div style="--my:0.5rem">
				<UpdatePassword />
			</div>
		{/if}

		{#if ($config?.features?.enable_api_key ?? true) || $user?.role === 'admin'}
			<details style="--size:0.8rem">
				<summary
					style="--d:flex; --ai:center; --g:0.5rem; --cur:pointer; --us:none; --py:0.2rem; --list-style:none"
				>
					<span style="--weight:500">{$i18n.t('API keys')}</span>
					<details
						style="--d:inline; --size:0.6rem;
					--c:var(--color-gray-400);
					--dark-c:var(--color-gray-500);--w: 80%;
					--m: auto;--b:0"
						on:click|stopPropagation
					>
						<summary style="--cur:pointer; --us:none; --list-style:none">
							{$i18n.t('What is an API key?')} &#9662;
						</summary>
						<div style="--mt:0.4rem; --lh:1.5; --size:0.8rem">
							<p style="--mb:0.4rem">
								{$i18n.t(
									'An API (Application Programming Interface) lets other apps and scripts talk to your Sage AI account — for example, a chatbot on your website, a shortcut on your phone, or a custom workflow.'
								)}
							</p>
							<p style="--mb:0.4rem">
								{$i18n.t(
									'Your API key is like a password for those connections. Keep it secret — anyone who has it can act on your behalf.'
								)}
							</p>
							<p>
								{$i18n.t('To see every available endpoint and try them out, visit the')}
								<a
									href="/docs"
									target="_blank"
									rel="noopener"
									style="--c:var(--color-blue-500); --tdn:underline; --weight:500"
									>{$i18n.t('interactive API documentation')}</a
								>.
							</p>
						</div>
					</details>
					<span style="--ml:auto; --size:0.6rem; --weight:500; --c:var(--color-gray-400)"
						>&#9662;</span
					>
				</summary>

				<div style="--mt:0.5rem; --d:flex; --fd:column; --g:1rem">
					{#if $user?.role === 'admin'}
						<div style="--w:100%">
							<div style="--size:0.6rem; --weight:500; --mb:0.2rem">{$i18n.t('JWT Token')}</div>
							<div style="--d:flex">
								<SensitiveInput value={localStorage.token} readOnly={true} />

								<button
									style="--ml:0.4rem; --px:0.4rem; --py:0.2rem; --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem"
									on:click={() => {
										copyToClipboard(localStorage.token);
										JWTTokenCopied = true;
										setTimeout(() => {
											JWTTokenCopied = false;
										}, 2000);
									}}
								>
									{#if JWTTokenCopied}
										<Icon name="check-fill-20" className="size-4" />
									{:else}
										<Icon name="clipboard-copy-16" className="size-4" />
									{/if}
								</button>
							</div>
						</div>
					{/if}

					{#if $config?.features?.enable_api_key ?? true}
						<div style="--w:100%">
							<div style="--size:0.6rem; --weight:500; --mb:0.2rem">{$i18n.t('API Key')}</div>
							<div style="--d:flex">
								{#if APIKey}
									<SensitiveInput value={APIKey} readOnly={true} />

									<button
										style="--ml:0.4rem; --px:0.4rem; --py:0.2rem; --hvr-dark-bgc:var(--color-gray-850); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem"
										on:click={() => {
											copyToClipboard(APIKey);
											APIKeyCopied = true;
											setTimeout(() => {
												APIKeyCopied = false;
											}, 2000);
										}}
									>
										{#if APIKeyCopied}
											<Icon name="check-fill-20" className="size-4" />
										{:else}
											<Icon name="clipboard-copy-16" className="size-4" />
										{/if}
									</button>

									<Tooltip content={$i18n.t('Create new key')}>
										<button
											style="--px:0.4rem; --py:0.2rem; --radius:0.5rem; --hvr-dark-bgc:var(--color-gray-850); --tn:background-color 150ms"
											on:click={() => {
												createAPIKeyHandler();
											}}
										>
											<Icon name="reset" className="size-4" strokeWidth="2" />
										</button>
									</Tooltip>
								{:else}
									<button
										style="--d:flex; --g:0.4rem; --ai:center; --weight:500; --px:0.8rem; --py:0.4rem; --radius:0.5rem; --bgc:rgb(236 236 236 / 0.7); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-850); --tn:background-color 150ms"
										on:click={() => {
											createAPIKeyHandler();
										}}
									>
										<Icon name="plus" strokeWidth="2" className=" size-3.5" />

										{$i18n.t('Create new secret key')}</button
									>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			</details>
		{/if}
	</div>

	<div style="--d:flex; --jc:flex-end; --pt:0.6rem; --size:0.8rem; --weight:500">
		<button
			style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			on:click={async () => {
				const res = await submitHandler();

				if (res) {
					saveHandler();
				}
			}}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</div>
