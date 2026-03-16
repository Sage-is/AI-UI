<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import ManageOllama from '../Models/Manage/ManageOllama.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	export let urlIdx: number | null = null;
</script>

<Modal size="sm" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-100); --px:1.25rem; --pt:1rem; --pb:0.5rem">
			<div
				style="--d:flex; --w:100%; --jc:space-between; --ai:center; --size:1.125rem; --weight:500; --as:center"
	class="font-primary"
			>
				<div style="--fs:0">
					{$i18n.t('Manage Ollama')}
				</div>
			</div>
			<button
				style="--as:center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div style="--d:flex; --fd:column; --fd-md:row; --w:100%; --px:1.25rem; --pb:1rem; --p: 1rem 0;--bgc: var(--white); --br: 1rem">
			<ManageOllama {urlIdx} />
		</div>
	</div>
</Modal>
