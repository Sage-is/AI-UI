<script>
	import { getContext } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import AccessControl from './AccessControl.svelte';

	export let show = false;
	export let accessControl = {};
	export let accessRoles = ['read'];
	export let allowPublic = true;

	export let onChange = () => {};
</script>

<Modal size="sm" bind:show>
	<div>
		<div style="--d:flex; --jc:space-between; --dark-c:var(--color-gray-100); --px:1.2rem; --pt:0.6rem; --pb:0.2rem">
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
				<Icon name="x-mark" strokeWidth="2" className={'size-5'} />
			</button>
		</div>

		<div style="--w:100%; --px:1.2rem; --pb:1rem; --dark-c:#fff">
			<AccessControl bind:accessControl {onChange} {accessRoles} {allowPublic} />
		</div>
	</div>
</Modal>
