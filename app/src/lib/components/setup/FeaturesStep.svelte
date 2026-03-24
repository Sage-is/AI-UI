<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getAdminConfig, updateAdminConfig } from '$lib/apis/auths';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import QuestionMarkCircle from '$lib/components/icons/QuestionMarkCircle.svelte';

	const i18n = getContext('i18n');

	export let onNext: () => void = () => {};
	export let onBack: () => void = () => {};

	let loading = true;
	let saving = false;

	let enableCommunitySharing = false;
	let enableMessageRating = true;
	let enableNotes = false;
	let enableSpaces = false;
	let enableUserWebhooks = false;

	let adminConfig: any = null;

	onMount(async () => {
		try {
			adminConfig = await getAdminConfig();
			if (adminConfig) {
				enableCommunitySharing = adminConfig.ENABLE_COMMUNITY_SHARING ?? false;
				enableMessageRating = adminConfig.ENABLE_MESSAGE_RATING ?? true;
				enableNotes = adminConfig.ENABLE_NOTES ?? false;
				enableSpaces = adminConfig.ENABLE_SPACES ?? false;
				enableUserWebhooks = adminConfig.ENABLE_USER_WEBHOOKS ?? false;
			}
		} catch {
			toast.error($i18n.t('Failed to load feature settings'));
		}
		loading = false;
	});

	const saveAndNext = async () => {
		if (!adminConfig) {
			onNext();
			return;
		}
		saving = true;
		try {
			await updateAdminConfig({
				...adminConfig,
				ENABLE_COMMUNITY_SHARING: enableCommunitySharing,
				ENABLE_MESSAGE_RATING: enableMessageRating,
				ENABLE_NOTES: enableNotes,
				ENABLE_SPACES: enableSpaces,
				ENABLE_USER_WEBHOOKS: enableUserWebhooks
			});
			toast.success($i18n.t('Features saved'));
			onNext();
		} catch {
			toast.error($i18n.t('Failed to save feature settings'));
		}
		saving = false;
	};
</script>

<div style="--px:1.2rem; --pt:1rem; --pb:1.5rem">
	<div style="--size:1.2rem; --weight:600; --dark-c:#fff; --mb:0.2rem">
		{$i18n.t('Features')}
	</div>
	<div style="--size:0.75rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); --mb:1.2rem">
		{$i18n.t('Enable or disable platform features for your users.')}
	</div>

	{#if loading}
		<div style="--d:flex; --jc:center; --py:2rem; --size:0.8rem; --c:var(--color-gray-400)">
			{$i18n.t('Loading...')}
		</div>
	{:else}
		<div style="--d:flex; --fd:column; --g:0.6rem; --mb:1.5rem">

			<!-- Community Sharing -->
			<label
				style="--d:flex; --ai:center; --jc:space-between; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; cursor:pointer; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<div>
					<div style="--d:flex; --ai:center; --g:0.4rem">
						<span style="--size:0.85rem; --weight:500">{$i18n.t('Community Sharing')}</span>
						<Tooltip content={$i18n.t('Let users publish conversations to a shared community feed visible to all platform members.')} placement="right" className="flex items-center">
							<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"><QuestionMarkCircle className="size-3.5" /></span>
						</Tooltip>
					</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{$i18n.t('Allow users to share conversations with the community')}
					</div>
				</div>
				<input type="checkbox" bind:checked={enableCommunitySharing} style="--w:1rem; --h:1rem; --shrink:0" />
			</label>

			<!-- Message Rating -->
			<label
				style="--d:flex; --ai:center; --jc:space-between; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; cursor:pointer; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<div>
					<div style="--d:flex; --ai:center; --g:0.4rem">
						<span style="--size:0.85rem; --weight:500">{$i18n.t('Message Rating')}</span>
						<Tooltip content={$i18n.t('Show thumbs up/down buttons on AI responses so users can provide feedback on response quality.')} placement="right" className="flex items-center">
							<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"><QuestionMarkCircle className="size-3.5" /></span>
						</Tooltip>
					</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{$i18n.t('Allow users to rate AI responses')}
					</div>
				</div>
				<input type="checkbox" bind:checked={enableMessageRating} style="--w:1rem; --h:1rem; --shrink:0" />
			</label>

			<!-- Notes (Beta) -->
			<label
				style="--d:flex; --ai:center; --jc:space-between; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-amber-100); --dark-bc:var(--color-amber-900); --bw:1px; --bs:solid; cursor:pointer; --hvr-bgc:var(--color-amber-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<div>
					<div style="--d:flex; --ai:center; --g:0.4rem">
						<span style="--size:0.85rem; --weight:500">{$i18n.t('Notes')}</span>
						<span style="--size:0.55rem; --c:var(--color-amber-600); --weight:600; --px:0.3rem; --py:0.1rem; --radius:0.25rem; --bgc:var(--color-amber-100); --dark-bgc:var(--color-amber-900); --dark-c:var(--color-amber-400)">{$i18n.t('Beta')}</span>
						<Tooltip content={$i18n.t('Adds a personal note-taking area where users can save and organize text notes. This feature is still in beta and may change.')} placement="right" className="flex items-center">
							<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"><QuestionMarkCircle className="size-3.5" /></span>
						</Tooltip>
					</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{$i18n.t('Enable note-taking features')}
					</div>
				</div>
				<input type="checkbox" bind:checked={enableNotes} style="--w:1rem; --h:1rem; --shrink:0" />
			</label>

			<!-- Spaces (Beta) -->
			<label
				style="--d:flex; --ai:center; --jc:space-between; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-amber-100); --dark-bc:var(--color-amber-900); --bw:1px; --bs:solid; cursor:pointer; --hvr-bgc:var(--color-amber-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<div>
					<div style="--d:flex; --ai:center; --g:0.4rem">
						<span style="--size:0.85rem; --weight:500">{$i18n.t('Spaces')}</span>
						<span style="--size:0.55rem; --c:var(--color-amber-600); --weight:600; --px:0.3rem; --py:0.1rem; --radius:0.25rem; --bgc:var(--color-amber-100); --dark-bgc:var(--color-amber-900); --dark-c:var(--color-amber-400)">{$i18n.t('Beta')}</span>
						<Tooltip content={$i18n.t('Create shared workspaces where teams can collaborate with dedicated models, knowledge bases, and conversation history. This feature is still in beta and may change.')} placement="right" className="flex items-center">
							<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"><QuestionMarkCircle className="size-3.5" /></span>
						</Tooltip>
					</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{$i18n.t('Enable workspace and collaboration spaces')}
					</div>
				</div>
				<input type="checkbox" bind:checked={enableSpaces} style="--w:1rem; --h:1rem; --shrink:0" />
			</label>

			<!-- User Webhooks -->
			<label
				style="--d:flex; --ai:center; --jc:space-between; --g:0.8rem; --p:0.8rem; --radius:0.75rem; --bc:var(--color-gray-200); --dark-bc:var(--color-gray-700); --bw:1px; --bs:solid; cursor:pointer; --hvr-bgc:var(--color-gray-50); --dark-hvr-bgc:var(--color-gray-850); --tn:background-color 150ms cubic-bezier(0.4, 0, 0.2, 1)"
			>
				<div>
					<div style="--d:flex; --ai:center; --g:0.4rem">
						<span style="--size:0.85rem; --weight:500">{$i18n.t('User Webhooks')}</span>
						<Tooltip content={$i18n.t('Allow users to set up webhook URLs that receive notifications when events occur, such as new messages or completed responses.')} placement="right" className="flex items-center">
							<span style="--c:var(--color-gray-400); --dark-c:var(--color-gray-500); cursor:help"><QuestionMarkCircle className="size-3.5" /></span>
						</Tooltip>
					</div>
					<div style="--size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400)">
						{$i18n.t('Allow users to configure webhook integrations')}
					</div>
				</div>
				<input type="checkbox" bind:checked={enableUserWebhooks} style="--w:1rem; --h:1rem; --shrink:0" />
			</label>

		</div>
	{/if}

	<div style="--d:flex; --jc:space-between; --ai:center">
		<button
			on:click={onBack}
			style="--px:0.6rem; --py:0.3rem; --size:0.75rem; --c:var(--color-gray-500); --hvr-c:var(--color-gray-700); --dark-hvr-c:var(--color-gray-200)"
		>
			{$i18n.t('Back')}
		</button>

		<div style="--d:flex; --ai:center; --g:0.6rem">
			<button
				on:click={onNext}
				style="--px:0.6rem; --py:0.3rem; --size:0.7rem; --c:var(--color-gray-400); --hvr-c:var(--color-gray-600); --td:underline"
			>
				{$i18n.t('Skip')}
			</button>

			<button
				on:click={saveAndNext}
				disabled={loading || saving}
				style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:{!loading && !saving ? '#000' : 'var(--color-gray-300)'}; --hvr-bgc:{!loading && !saving ? 'var(--color-gray-900)' : 'var(--color-gray-300)'}; --c:#fff; --dark-bgc:{!loading && !saving ? '#fff' : 'var(--color-gray-600)'}; --dark-c:{!loading && !saving ? '#000' : 'var(--color-gray-400)'}; --hvr-dark-bgc:{!loading && !saving ? 'var(--color-gray-100)' : 'var(--color-gray-600)'}; --tn:color, background-color 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
			>
				{saving ? $i18n.t('Saving...') : $i18n.t('Save & Next')}
			</button>
		</div>
	</div>
</div>
