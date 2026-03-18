<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { Confetti } from 'svelte-confetti';

	import { WEBUI_NAME, config, settings } from '$lib/stores';

	import { WEBUI_VERSION } from '$lib/constants';
	import { getChangelog } from '$lib/apis';

	import Modal from './common/Modal.svelte';
	import { updateUserSettings } from '$lib/apis/users';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	let changelog = null;

	onMount(async () => {
		const res = await getChangelog();
		changelog = res;
	});
</script>

<Modal bind:show size="lg">
	<div style="--px:1.2rem; --pt:1rem; --dark-c:var(--color-gray-300); --c:var(--color-gray-700)">
		<div style="--d:flex; --jc:space-between; --ai:flex-start">
			<div style="--size:1.2rem; --weight:600">
				{$i18n.t("What's New in")}
				{$WEBUI_NAME}
				<Confetti x={[-1, -0.25]} y={[0, 0.5]} />
			</div>
			<button
				style="--as:center"
				on:click={() => {
					localStorage.version = $config.version;
					show = false;
				}}
				aria-label={$i18n.t('Close')}
			>
				<XMark className={'size-5'}>
					<p class="sr-only">{$i18n.t('Close')}</p>
				</XMark>
			</button>
		</div>
		<div style="--d:flex; --ai:center; --mt:0.2rem">
			<div style="--size:0.8rem; --dark-c:var(--color-gray-200)">{$i18n.t('Release Notes')}</div>
			<div
				style="--d:flex; --as:center; --w:1px; --h:1.5rem; --mx:0.625rem; --bgc:var(--color-gray-200); --dark-bgc:var(--color-gray-700)"
			/>
			<div style="--size:0.8rem; --dark-c:var(--color-gray-200)">
				v{WEBUI_VERSION}
			</div>
		</div>
	</div>

	<div
		style="--w:100%; --p:1rem; --px:1.2rem; --c:var(--color-gray-700); --dark-c:var(--color-gray-100)"
	>
		<div style="--ofy:scroll; --maxh:24rem" class="scrollbar-hidden">
			<div style="--mb:0.6rem">
				{#if changelog}
					{#each Object.keys(changelog) as version}
						<div style="--mb:0.6rem; --pr:0.5rem">
							<div style="--weight:600; --size:1.2rem; --mb:0.2rem; --dark-c:#fff">
								v{version} - {changelog[version].date}
							</div>

							<hr />

							{#each Object.keys(changelog[version]).filter((section) => section !== 'date') as section}
								<div
									style="--weight:600; --tt:uppercase; --size:0.6rem; --w:fit-content; --px:0.6rem; --radius:9999px; --my:0.6rem"
									class={section === 'added'
										? 'text-white bg-blue-600'
										: section === 'fixed'
											? 'text-white bg-green-600'
											: section === 'changed'
												? 'text-white bg-yellow-600'
												: section === 'removed'
													? 'text-white bg-red-600'
													: ''}
								>
									{section}
								</div>

								<div style="--my:0.6rem; --px:0.4rem">
									{#each Object.keys(changelog[version][section]) as item}
										<div style="--size:0.8rem; --mb:0.5rem">
											<div style="--weight:600; --tt:uppercase">
												{changelog[version][section][item].title}
											</div>
											<div style="--mb:0.5rem; --mt:0.2rem">
												{changelog[version][section][item].content}
											</div>
										</div>
									{/each}
								</div>
							{/each}
						</div>
					{/each}
				{/if}
			</div>
		</div>

		<button
			on:click={async () => {
				localStorage.version = $config.version;
				await settings.set({ ...$settings, ...{ version: $config.version } });
				await updateUserSettings(localStorage.token, { ui: $settings });
				show = false;
			}}
			style="--ml:auto; --px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
		>
			{$i18n.t("Okay, Let's Go!")}
		</button>
	</div>
</Modal>
