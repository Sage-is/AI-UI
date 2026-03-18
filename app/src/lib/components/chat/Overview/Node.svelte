<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { Handle, Position, type NodeProps } from '@xyflow/svelte';

	import ProfileImage from '../Messages/ProfileImage.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Heart from '$lib/components/icons/Heart.svelte';

	type $$Props = NodeProps;
	export let data: $$Props['data'];
</script>

<div
	style="--px:1rem; --py:0.6rem; --shadow:3; --radius:0.6rem; --dark-bgc:#000; --bgc:#fff;  --dark-bc:var(--color-gray-900); --w:15rem; --h:5rem"
	class="group"
>
	<Tooltip
		content={data?.message?.error ? data.message.error.content : data.message.content}
		style="--w:100%"
		allowHTML={false}
	>
		{#if data.message.role === 'user'}
			<div style="--d:flex; --w:100%">
				<ProfileImage
					src={data.user?.profile_image_url ?? `${WEBUI_BASE_URL}/static/user.png`}
					className={'size-5 -translate-y-[1px]'}
				/>
				<div style="--ml:0.5rem">
					<div style="--d:flex; --jc:space-between; --ai:center">
						<div style="--size:0.6rem; --c:#000; --dark-c:#fff; --weight:500; --line-clamp:1">
							{data?.user?.name ?? 'User'}
						</div>
					</div>

					{#if data?.message?.error}
						<div style="--c:#ef4444; --line-clamp:2; --size:0.6rem; --mt:0.125rem">{data.message.error.content}</div>
					{:else}
						<div style="--c:var(--color-gray-500); --line-clamp:2; --size:0.6rem; --mt:0.125rem">{data.message.content}</div>
					{/if}
				</div>
			</div>
		{:else}
			<div style="--d:flex; --w:100%">
				<ProfileImage
					src={data?.model?.info?.meta?.profile_image_url ?? ''}
					className={'size-5 -translate-y-[1px]'}
				/>

				<div style="--ml:0.5rem">
					<div style="--d:flex; --jc:space-between; --ai:center">
						<div style="--size:0.6rem; --c:#000; --dark-c:#fff; --weight:500; --line-clamp:1">
							{data?.model?.name ?? data?.message?.model ?? 'Assistant'}
						</div>

						<button
							class={data?.message?.favorite ? '' : 'invisible group-hover:visible'}
							on:click={() => {
								data.message.favorite = !(data?.message?.favorite ?? false);
							}}
						>
							<Heart
								className="size-3 {data?.message?.favorite
									? 'fill-red-500 stroke-red-500'
									: 'hover:fill-red-500 hover:stroke-red-500'} "
								strokeWidth="2.5"
							/>
						</button>
					</div>

					{#if data?.message?.error}
						<div style="--c:#ef4444; --line-clamp:2; --size:0.6rem; --mt:0.125rem">
							{data.message.error.content}
						</div>
					{:else}
						<div style="--c:var(--color-gray-500); --line-clamp:2; --size:0.6rem; --mt:0.125rem">{data.message.content}</div>
					{/if}
				</div>
			</div>
		{/if}
	</Tooltip>
	<Handle type="target" position={Position.Top} style="--w:0.5rem; --radius:9999px; --dark-bgc:var(--color-gray-900)" />
	<Handle type="source" position={Position.Bottom} style="--w:0.5rem; --radius:9999px; --dark-bgc:var(--color-gray-900)" />
</div>
