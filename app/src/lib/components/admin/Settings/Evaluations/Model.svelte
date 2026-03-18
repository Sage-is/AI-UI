<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import ArenaModelModal from './ArenaModelModal.svelte';
	export let model;

	let showModel = false;
</script>

<ArenaModelModal
	bind:show={showModel}
	edit={true}
	{model}
	on:submit={async (e) => {
		dispatch('edit', e.detail);
	}}
	on:delete={async () => {
		dispatch('delete');
	}}
/>

<div style="--py:0.125rem">
	<div style="--d:flex; --jc:space-between; --ai:center; --mb:0.2rem">
		<div style="--d:flex; --fd:column; --fx:1 1 0%">
			<div style="--d:flex; --g:0.625rem; --ai:center">
				<img
					src={model.meta.profile_image_url}
					alt={model.name}
					style="--w:2rem; --h:2rem; --radius:9999px; --objf:cover; --fs:0"
				/>

				<div style="--w:100%; --d:flex; --fd:column">
					<div style="--d:flex; --ai:center; --g:0.2rem">
						<div style="--fs:0; --line-clamp:1">
							{model.name}
						</div>
					</div>

					<div style="--d:flex; --ai:center; --g:0.2rem">
						<div style="--size:0.6rem; --w:100%; --c:var(--color-gray-500); --bgc:transparent; --line-clamp:1">
							{model?.meta?.description ?? model.id}
						</div>
					</div>
				</div>
			</div>
		</div>

		<div style="--d:flex; --ai:center">
			<button
				style="--as:center; --w:fit-content; --size:0.8rem; --p:0.4rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:rgb(255 255 255 / 0.05); --radius:0.6rem"
				type="button"
				on:click={() => {
					showModel = true;
				}}
			>
				<Cog6 />
			</button>
		</div>
	</div>
</div>
