<script lang="ts">
	import DOMPurify from 'dompurify';

	import { getVersionUpdates, getWebhookUrl, updateWebhookUrl } from '$lib/apis';
	import {
		getAdminConfig,
		updateAdminConfig,
	} from '$lib/apis/auths';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import { config, settings, showChangesAndSetup, setupTriggerReason } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';
	import { compareVersion } from '$lib/utils';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Textarea from '$lib/components/common/Textarea.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let updateAvailable = null;
	let version = {
		current: '',
		latest: ''
	};

	let adminConfig = null;
	let webhookUrl = '';

	// Setup wizard
	let workingAlone = false;

	const checkForVersionUpdates = async () => {
		updateAvailable = null;
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: WEBUI_VERSION,
				latest: WEBUI_VERSION
			};
		});

		console.info(version);

		updateAvailable = compareVersion(version.latest, version.current);
		console.info(updateAvailable);
	};

	const updateHandler = async () => {
		webhookUrl = await updateWebhookUrl(localStorage.token, webhookUrl);
		const res = await updateAdminConfig(adminConfig);

		// Save working alone to user settings
		await settings.set({ ...$settings, workingAlone });
		await updateUserSettings(localStorage.token, { ui: $settings });

		if (res) {
			saveHandler();
		} else {
			toast.error($i18n.t('Failed to update settings'));
		}
	};

	onMount(async () => {
		if ($config?.features?.enable_version_update_check) {
			checkForVersionUpdates();
		}

		await Promise.all([
			(async () => {
				adminConfig = await getAdminConfig();
			})(),

			(async () => {
				webhookUrl = await getWebhookUrl(localStorage.token);
			})(),
		]);

		workingAlone = $settings?.workingAlone ?? false;
	});
</script>

<form
	style="--d:flex; --fd:column; --h:100%; --jc:space-between; --g:0.6rem; --size:0.8rem"
	on:submit|preventDefault={async () => {
		updateHandler();
	}}
>
	<div style="--mt:0.125rem; --g:0.6rem; --ofy:scroll; --h:100%"
	class="scrollbar-hidden">
		{#if adminConfig !== null}
			<div class="">
				<div style="--mb:0.8rem">
					<div style="--mb:0.625rem; --size:1rem; --weight:500">{$i18n.t('General')}</div>

					<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

					<div style="--mb:0.625rem">
						<div style="--mb:0.2rem; --size:0.6rem; --weight:500; --d:flex; --g:0.5rem; --ai:center">
							<div>
								{$i18n.t('Version')}
							</div>
						</div>
						<div style="--d:flex; --w:100%; --jc:space-between; --ai:center">
							<div style="--d:flex; --fd:column; --size:0.6rem; --c:var(--color-gray-700); --dark-c:var(--color-gray-200)">
								<div style="--d:flex; --g:0.2rem">
									<Tooltip content={WEBUI_BUILD_HASH}>
										v{WEBUI_VERSION}
									</Tooltip>

									{#if $config?.features?.enable_version_update_check}
										<a
											href="https://github.com/Sage-is/AI-UI/releases/tag/v{version.latest}"
											target="_blank"
										>
											{updateAvailable === null
												? $i18n.t('Checking for updates...')
												: updateAvailable
													? `(v${version.latest} ${$i18n.t('available!')})`
													: $i18n.t('(latest)')}
										</a>
									{/if}
								</div>

								<button
									style="--td:underline; --d:flex; --ai:center; --g:0.2rem; --size:0.6rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-500)"
									type="button"
									on:click={() => {
										setupTriggerReason.set({ hasChangelog: true, needsModels: false, needsUsers: false, manualTrigger: false });
										showChangesAndSetup.set(true);
									}}
								>
									<div>{$i18n.t("See what's new")}</div>
								</button>

								<button
									style="--td:underline; --d:flex; --ai:center; --g:0.2rem; --size:0.6rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-500)"
									type="button"
									on:click={() => {
										setupTriggerReason.set({ hasChangelog: false, needsModels: false, needsUsers: false, manualTrigger: true });
										showChangesAndSetup.set(true);
									}}
								>
									<div>{$i18n.t('Run Setup Wizard')}</div>
								</button>
							</div>

							{#if $config?.features?.enable_version_update_check}
								<button
									style="--size:0.6rem; --px:0.6rem; --py:0.4rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem; --weight:500"
									type="button"
									on:click={() => {
										checkForVersionUpdates();
									}}
								>
									{$i18n.t('Check for updates')}
								</button>
							{/if}
						</div>
					</div>

					<div style="--mb:0.625rem">
						<div style="--d:flex; --w:100%; --jc:space-between; --ai:center; --pr:0.5rem">
							<div style="--size:0.6rem; --pr:0.5rem">
								<div style="--weight:500">
									{$i18n.t('Working Alone')}
								</div>
								<div style="--size:0.6rem; --c:var(--color-gray-500)">
									{$i18n.t('Skip user setup in the wizard. Toggle off to re-enable the users step.')}
								</div>
							</div>

							<Switch bind:state={workingAlone} />
						</div>
					</div>

					<div style="--mb:0.625rem">
						<div style="--d:flex; --w:100%; --jc:space-between; --ai:center; --pr:0.5rem">
							<div style="--size:0.6rem; --pr:0.5rem">
								<div style="--weight:500">
									{$i18n.t('Setup Wizard')}
								</div>
								<div style="--size:0.6rem; --c:var(--color-gray-500)">
									{#if $settings?.setupCompleted}
										{$i18n.t('Setup completed. Reset to trigger the wizard again on next login.')}
									{:else}
										{$i18n.t('Setup has not been completed yet.')}
									{/if}
								</div>
							</div>

							<button
								style="--size:0.6rem; --px:0.6rem; --py:0.4rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem; --weight:500"
								class="flex-shrink-0"
								type="button"
								on:click={async () => {
									workingAlone = false;
									await settings.set({ ...$settings, setupCompleted: false, workingAlone: false });
									await updateUserSettings(localStorage.token, { ui: $settings });
									toast.success($i18n.t('Setup wizard will trigger on next login'));
								}}
							>
								{$i18n.t('Reset')}
							</button>
						</div>
					</div>

					<div style="--mb:0.625rem">
						<div style="--d:flex; --w:100%; --jc:space-between; --ai:center">
							<div style="--size:0.6rem; --pr:0.5rem">
								<div class="">
									{$i18n.t('Help')}
								</div>
								<div style="--size:0.6rem; --c:var(--color-gray-500)">
									{$i18n.t('Discover how to use Sage.is AI and seek support from the community.')}
								</div>
							</div>

							<a
								style="--size:0.6rem; --weight:500; --td:underline"
	class="flex-shrink-0"
								href="https://docs.sage.is/"
								target="_blank"
							>
								{$i18n.t('Documentation')}
							</a>
						</div>

						<div style="--mt:0.2rem">
							<div style="--d:flex; --g:0.2rem">
								<a href="https://x.com/Sage_Is_AI" target="_blank">
									<img
										alt="X (formerly Twitter) Follow"
										src="https://img.shields.io/badge/X-Follow-black.svg?style=for-the-badge&logoColor=white"
									/>
								</a>

								<a href="http://linkedin.com/company/sage-is-ai" target="_blank">
									<a href="http://linkedin.com/company/sage-is-ai" target="_blank">
										<img
											alt="LinkedIn Follow"
											src="https://img.shields.io/badge/LinkedIn-Follow-blue.svg?style=for-the-badge&logo=linkedin&logoColor=white"
										/>
									</a>
								</a>

								<a href="https://bsky.app/profile/sage-is-ai.bsky.social" target="_blank">
									<img
										alt="Bluesky Follow"
										src="https://img.shields.io/badge/bluesky-%230A7AFF.svg?style=for-the-badge&logo=bluesky&logoColor=white&label=Follow"
									/>
								</a>

								<a href="https://github.com/Sage-is/AI-UI" target="_blank">
									<img
										alt="Github Repo"
										src="https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white&label=Star us on"
									/>
								</a>
							</div>
						</div>
					</div>

					<div style="--mb:0.625rem">
						<div style="--d:flex; --w:100%; --jc:space-between; --ai:center">
							<div style="--size:0.6rem; --pr:0.5rem">
								<div class="">
									{$i18n.t('License')}
								</div>

								{#if $config?.license_metadata}
									<a href="https://docs.sage.is/license" target="_blank" style="--c:var(--color-gray-500); --mt:0.125rem">
										<span style="--tt:capitalize; --c:#000; --dark-c:#fff"
											>{$config?.license_metadata?.type}
											license</span
										>
										registered to
										<span style="--tt:capitalize; --c:#000; --dark-c:#fff"
											>{$config?.license_metadata?.organization_name}</span
										>
										for
										<span style="--weight:500; --c:#000; --dark-c:#fff"
											>{$config?.license_metadata?.seats ?? 'Unlimited'} users.</span
										>
									</a>
									{#if $config?.license_metadata?.html}
										<div style="--mt:0.125rem">
											{@html DOMPurify.sanitize($config?.license_metadata?.html)}
										</div>
									{/if}
								{:else}
									<a
										style="--size:0.6rem; --hvr-td:underline"
										href="https://docs.sage.is/license"
										target="_blank"
									>
										<span style="--c:var(--color-gray-500)">
											{$i18n.t(
												'Sage.is AI runs on open source. Always will. No lock-in. No tricks. Full AGPL freedom. Enterprise teams please stand with us. Sponsor the future of Honest and Real Open AI.'
											)}
										</span>
									</a>
								{/if}
							</div>

							<!-- <button
								style="--size:0.6rem; --px:0.6rem; --py:0.4rem; --bgc:var(--color-gray-50); --hvr-bgc:var(--color-gray-100); --dark-bgc:var(--color-gray-850); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem; --weight:500"
	class="flex-shrink-0"
							>
								{$i18n.t('Activate')}
							</button> -->
						</div>
					</div>
				</div>


				<!-- Authentication settings moved to Admin > Settings > Auth tab -->

				<div style="--mb:0.6rem">
					<div style="--mb:0.625rem; --size:1rem; --weight:500">{$i18n.t('Features')}</div>

					<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-850); --my:0.5rem" />

					<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between; --pr:0.5rem">
						<div style="--as:center; --size:0.6rem; --weight:500">
							{$i18n.t('Enable Community Sharing')}
						</div>

						<Switch bind:state={adminConfig.ENABLE_COMMUNITY_SHARING} />
					</div>

					<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between; --pr:0.5rem">
						<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Enable Message Rating')}</div>

						<Switch bind:state={adminConfig.ENABLE_MESSAGE_RATING} />
					</div>

					<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between; --pr:0.5rem">
						<div style="--as:center; --size:0.6rem; --weight:500">
							{$i18n.t('Notes')} ({$i18n.t('Beta')})
						</div>

						<Switch bind:state={adminConfig.ENABLE_NOTES} />
					</div>

					<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between; --pr:0.5rem">
						<div style="--as:center; --size:0.6rem; --weight:500">
							{$i18n.t('Spaces')} ({$i18n.t('Beta')})
						</div>

						<Switch bind:state={adminConfig.ENABLE_SPACES} />
					</div>

					<div style="--mb:0.625rem; --d:flex; --w:100%; --ai:center; --jc:space-between; --pr:0.5rem">
						<div style="--as:center; --size:0.6rem; --weight:500">
							{$i18n.t('User Webhooks')}
						</div>

						<Switch bind:state={adminConfig.ENABLE_USER_WEBHOOKS} />
					</div>

					<div style="--mb:0.625rem">
						<div style="--as:center; --size:0.6rem; --weight:500; --mb:0.5rem">
							{$i18n.t('Response Watermark')}
						</div>
						<Textarea
							placeholder={$i18n.t('Enter a watermark for the response. Leave empty for none.')}
							bind:value={adminConfig.RESPONSE_WATERMARK}
						/>
					</div>

					<div style="--mb:0.625rem; --w:100%; --jc:space-between">
						<div style="--d:flex; --w:100%; --jc:space-between">
							<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('WebUI URL')}</div>
						</div>

						<div style="--d:flex; --mt:0.5rem; --g:0.5rem">
							<input
								style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
								type="text"
								placeholder={`e.g.) "http://localhost:3000"`}
								bind:value={adminConfig.WEBUI_URL}
							/>
						</div>

						<div style="--mt:0.5rem; --size:0.6rem; --c:var(--color-gray-400); --dark-c:var(--color-gray-500)">
							{$i18n.t(
								'Enter the public URL of your WebUI. This URL will be used to generate links in the notifications.'
							)}
						</div>
					</div>

					<div style="--w:100%; --jc:space-between">
						<div style="--d:flex; --w:100%; --jc:space-between">
							<div style="--as:center; --size:0.6rem; --weight:500">{$i18n.t('Webhook URL')}</div>
						</div>

						<div style="--d:flex; --mt:0.5rem; --g:0.5rem">
							<input
								style="--w:100%; --radius:0.5rem; --py:0.5rem; --px:1rem; --size:0.8rem; --bgc:var(--color-gray-50); --dark-c:var(--color-gray-300); --dark-bgc:var(--color-gray-850); --oe:none"
								type="text"
								placeholder={`https://example.com/webhook`}
								bind:value={webhookUrl}
							/>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div style="--d:flex; --jc:flex-end; --pt:0.6rem; --size:0.8rem; --weight:500">
		<button
			style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
