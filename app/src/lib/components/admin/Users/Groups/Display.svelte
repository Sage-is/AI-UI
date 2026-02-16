<script lang="ts">
	import { getContext } from 'svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let name = '';
	export let color = '';
	export let description = '';
</script>

<div style="--d:flex; --g:0.5rem">
	<div style="--d:flex; --fd:column; --w:100%">
		<div style="--mb:0.125rem; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">{$i18n.t('Name')}</div>

		<div style="--fx:1 1 0%">
			<input
				style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
	class="placeholder:text-gray-300 dark:placeholder:text-gray-700"
				type="text"
				bind:value={name}
				placeholder={$i18n.t('Group Name')}
				autocomplete="off"
				required
			/>
		</div>
	</div>
</div>

<!-- <div style="--d:flex; --fd:column; --w:100%; --mt:0.5rem">
	<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">{$i18n.t('Color')}</div>

	<div style="--fx:1 1 0%">
		<Tooltip content={$i18n.t('Hex Color - Leave empty for default color')} placement="top-start">
			<div style="--d:flex; --g:0.125rem">
				<div style="--c:var(--color-gray-500, #9b9b9b)">#</div>

				<input
					style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
	class="placeholder:text-gray-300 dark:placeholder:text-gray-700"
					type="text"
					bind:value={color}
					placeholder={$i18n.t('Hex Color')}
					autocomplete="off"
				/>
			</div>
		</Tooltip>
	</div>
</div> -->

<div style="--d:flex; --fd:column; --w:100%; --mt:0.5rem">
	<div style="--mb:0.25rem; --size:0.75rem; --c:var(--color-gray-500, #9b9b9b)">{$i18n.t('Description')}</div>

	<div style="--fx:1 1 0%">
		<Textarea
			className="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden resize-none"
			rows={4}
			bind:value={description}
			placeholder={$i18n.t('Group Description')}
		/>
	</div>
</div>
