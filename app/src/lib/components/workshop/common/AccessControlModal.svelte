<script>
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import AccessControl from './AccessControl.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	export let accessControl = {};
	export let accessRoles = ['read'];
	export let allowPublic = true;

	export let onChange = () => {};
</script>

<Modal size="sm" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-100, #ececec); --px:1.25rem; --pt:0.75rem; --pb:0.25rem">
			<div style="--size:1.125rem; --weight:500; --as:center"
	class="font-primary">
				{$i18n.t('Access Control')}
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

		<div style="--w:100%; --px:1.25rem; --pb:1rem; --dark-c:#fff">
			<AccessControl bind:accessControl {onChange} {accessRoles} {allowPublic} />
		</div>
	</div>
</Modal>
