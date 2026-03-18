<script lang="ts">
	import { DropdownMenu } from 'bits-ui';

	import { flyAndScale } from '$lib/utils/transitions';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { getBranding } from '$lib/apis/configs';
	import { getUserActiveStatusById } from '$lib/apis/users';

	export let side = 'right';
	export let align = 'top';

	export let user = null;
	let show = false;

	let active = false;
	let branding: { logo_url?: string; favicon_url?: string } = {};

	import { onMount } from 'svelte';

	onMount(async () => {
		try {
			branding = await getBranding();
		} catch (err) {
			console.error('Failed to load branding:', err);
		}
	});

	const getActiveStatus = async () => {
		const res = await getUserActiveStatusById(localStorage.token, user.id).catch((error) => {
			console.error('Error fetching user active status:', error);
		});

		if (res) {
			active = res.active;
		} else {
			active = false;
		}
	};

	$: if (show) {
		getActiveStatus();
	}
</script>

<DropdownMenu.Root
	bind:open={show}
	closeFocus={false}
	onOpenChange={(state) => {}}
	typeahead={false}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			style="--maxw:100%; --w:240px; --radius:0.5rem; --z:9999; --bgc:#fff; --dark-bgc:#000; --dark-c:#fff; --shadow:4"
			sideOffset={8}
			{side}
			{align}
			transition={flyAndScale}
		>
			{#if user}
				<div style="--d:flex; --fd:column; --g:0.5rem; --w:100%; --radius:0.5rem">
					<div style="--py:2rem; --pos:relative; --bgc:var(--color-gray-900); --btlr:0.5rem; --btrr:0.5rem">
						<img
							crossorigin="anonymous"
							src={user?.profile_image_url ?? branding?.logo_url ?? `${WEBUI_BASE_URL}/static/icons/favicon.png`}
							style="--pos:absolute; --bottom:-1.2rem; --left:0.6rem; --w:3rem; --h:3rem; --ml:0.125rem; --objf:cover; --radius:9999px; --translatey:-1px"
							alt="profile"
						/>
					</div>

					<div style="--d:flex; --fd:column; --pt:1rem; --pb:0.625rem; --px:1rem">
						<div style="--mb:-0.2rem">
							<span style="--weight:500; --size:0.8rem; --line-clamp:1"> {user.name} </span>
						</div>

						<div style="--d:flex; --ai:center; --g:0.5rem">
							{#if active}
								<div>
									<span style="--pos:relative; --d:flex; --w:0.5rem; --h:0.5rem">
										<span
											style="animation:ping 1s cubic-bezier(0, 0, 0.2, 1) infinite; --pos:absolute; --d:inline-flex; --h:100%; --w:100%; --radius:9999px; --bgc:#4ade80; --op:0.75"
										/>
										<span style="--pos:relative; --d:inline-flex; --radius:9999px; --w:0.5rem; --h:0.5rem; --bgc:#22c55e" />
									</span>
								</div>

								<div style="--translatey:-1px">
									<span style="--size:0.6rem"> Active </span>
								</div>
							{:else}
								<div>
									<span style="--pos:relative; --d:flex; --w:0.5rem; --h:0.5rem">
										<span style="--pos:relative; --d:inline-flex; --radius:9999px; --w:0.5rem; --h:0.5rem; --bgc:var(--color-gray-500)" />
									</span>
								</div>

								<div style="--translatey:-1px">
									<span style="--size:0.6rem"> Away </span>
								</div>
							{/if}
						</div>
					</div>
				</div>
			{/if}
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
