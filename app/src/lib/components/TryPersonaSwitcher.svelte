<script lang="ts">
	/**
	 * try.sage persona switcher.
	 *
	 * Renders one button per persona returned by
	 * `GET /api/v1/sage/runtime/personas` (Phase A2). Mounted inside
	 * `UserMenu.svelte` and only rendered when
	 * `$config?.features?.enable_try_sage` is true.
	 *
	 * Why this component reads from the shared `tryPersonas` store rather
	 * than re-fetching on its own: the workshop banner (B2) and this
	 * switcher both consume the same payload. Sharing one store keeps
	 * them in sync after admin extend/reset rotates the magic-link URLs
	 * (`invalidatePersonas()` clears the store; whichever component
	 * mounts first re-hydrates).
	 *
	 * Why hard navigation (`window.location.assign`) instead of
	 * SvelteKit `goto`: clicking a persona swaps tokens via the
	 * `/auth#magic_token=...` handler, and the new identity must boot
	 * with a clean store graph. A SPA navigation would carry the
	 * previous user's stores (chats, models, settings) into the next
	 * session — hard reload is the simplest way to avoid stale state.
	 *
	 * Why no admin reset/extend buttons here: those controls live in the
	 * try.sage banner (B-banner-admin owns them). The user menu only
	 * switches identities — it does not manage trial state.
	 */

	import { getContext, onMount } from 'svelte';
	import { config, tryPersonas, user } from '$lib/stores';
	import { loadPersonas } from '$lib/utils/sage-runtime';
	import type { Persona } from '$lib/apis/sage-runtime';
	import Icon from '$lib/components/Icon.svelte';

	const i18n = getContext('i18n');

	// Match the surrounding UserMenu button styling so the switcher
	// blends in with Settings / Archived Chats / Admin Panel.
	const itemStyle =
		'--d:flex; --radius:0.4rem; --py:0.4rem; --px:0.6rem; --w:100%; --hvr-bgc:var(--color-gray-50); --hvr-dark-bgc:var(--color-gray-800); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1)';

	onMount(() => {
		// Hydrate only if the banner hasn't already populated the store.
		// Keeping this lazy avoids a duplicate request when both the
		// banner and the switcher mount in the same render.
		if ($tryPersonas === null && $config?.features?.enable_try_sage) {
			const token =
				typeof localStorage !== 'undefined' ? localStorage.token ?? '' : '';
			loadPersonas(token).catch((err) => {
				console.error('TryPersonaSwitcher: failed to load personas', err);
			});
		}
	});

	function switchTo(persona: Persona) {
		// Hard navigation — see component-level comment.
		window.location.assign(persona.login_url);
	}
</script>

{#if $config?.features?.enable_try_sage && $tryPersonas && $tryPersonas.length > 0}
	<hr style="--bc:var(--color-gray-100); --dark-bc:var(--color-gray-800); --my:0.2rem; --p:0" />

	<div
		style="--d:flex; --g:0.5rem; --ai:center; --py:0.3rem; --px:0.6rem; --size:0.7rem; --weight:600; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); text-transform:uppercase; letter-spacing:0.04em"
	>
		<Icon name="user-group" className="size-4" strokeWidth="1.5" />
		<span>{$i18n ? $i18n.t('Switch persona') : 'Switch persona'}</span>
	</div>

	{#each $tryPersonas as persona (persona.key)}
		<button
			style={itemStyle}
			on:click={() => switchTo(persona)}
			title={persona.login_url}
		>
			<div style="--as:center; --mr:0.6rem">
				<Icon
					name={persona.role === 'admin' ? 'user-circle' : 'user'}
					className="w-5 h-5"
					strokeWidth="1.5"
				/>
			</div>
			<div
				style="--d:flex; --fd:column; --ai:flex-start; --as:center; overflow:hidden; --w:100%"
			>
				<div
					style="--w:100%; overflow:hidden; text-overflow:ellipsis; --ws:nowrap"
				>
					{persona.label}
				</div>
				<div
					style="--size:0.65rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); text-transform:lowercase"
				>
					{persona.role}
				</div>
			</div>
		</button>
	{/each}

	{#if $user?.role !== 'admin'}
		<div
			style="--py:0.4rem; --px:0.6rem; --size:0.7rem; --c:var(--color-gray-500); --dark-c:var(--color-gray-400); line-height:1.3"
		>
			{$i18n
				? $i18n.t(
						'Admins can reset this environment or delay the reset. Check the try.sage docs for details :D'
					)
				: 'Admins can reset this environment or delay the reset. Check the try.sage docs for details :D'}
		</div>
	{/if}
{/if}
