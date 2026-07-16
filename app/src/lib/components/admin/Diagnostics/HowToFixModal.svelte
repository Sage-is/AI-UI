<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { copyToClipboard } from '$lib/utils';
	import { graftSprig } from '$lib/apis/retrieval';

	import {
		fixRegistry,
		hasFix,
		getStepsFor,
		getAllShapesFor,
		type DeploymentShape
	} from './fixRegistry';

	const i18n: any = getContext('i18n');

	export let show: boolean = false;
	export let issueType: string | null = null;
	export let sprig: string | null = null;
	export let sprigCapability: string | null = null;
	export let onGrafted: (() => void) | null = null;
	export let defaultShape: DeploymentShape = 'unknown';
	export let shapeConfidence: 'high' | 'low' | 'unknown' = 'unknown';

	let selectedShape: DeploymentShape = 'unknown';
	let showOtherShapes: boolean = false;
	let showManualFix: boolean = false;
	let grafting: boolean = false;

	$: entry = issueType ? fixRegistry[issueType] : undefined;
	$: documented = hasFix(issueType);
	$: needsShapePicker = shapeConfidence !== 'high' && selectedShape === 'unknown';
	$: activeShape =
		shapeConfidence === 'high' ? defaultShape : selectedShape !== 'unknown' ? selectedShape : 'unknown';
	$: primarySteps =
		entry && activeShape !== 'unknown' ? getStepsFor(entry, activeShape) : [];
	$: allShapes = entry ? getAllShapesFor(entry) : null;

	$: if (!show) {
		selectedShape = 'unknown';
		showOtherShapes = false;
		showManualFix = false;
		grafting = false;
	}

	const shapeLabel = (shape: DeploymentShape): string => {
		switch (shape) {
			case 'caprover':
				return $i18n.t('CapRover');
			case 'docker_compose':
				return $i18n.t('Docker Compose');
			case 'brew':
				return $i18n.t('Homebrew');
			default:
				return $i18n.t('Unknown');
		}
	};

	const handleCopy = async (text: string) => {
		await copyToClipboard(text);
		toast.success($i18n.t('Copied to clipboard'));
	};

	const handleGraft = async () => {
		if (!sprig || grafting) return;
		const name = sprig;
		const capability = sprigCapability ?? '';
		grafting = true;
		try {
			await graftSprig(localStorage.token, { name, capability });
			toast.success($i18n.t('Grafted {{name}} — capability restored.', { name }));
			show = false;
			onGrafted?.();
		} catch (e: any) {
			toast.error(
				e?.detail
					? `${$i18n.t('Failed to graft {{name}}', { name })}: ${e.detail}`
					: $i18n.t('Failed to graft {{name}}', { name })
			);
		} finally {
			grafting = false;
		}
	};

	const close = () => {
		show = false;
	};
</script>

<Modal bind:show size="lg">
	<div class="p-5">
		<div class="flex items-start justify-between mb-4 gap-3">
			<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
				{$i18n.t('How to fix')}
			</h2>
			<button
				type="button"
				class="text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
				on:click={close}
				aria-label={$i18n.t('Close')}
			>
				<Icon name="x-fill-20-ca63" className="size-5" />
			</button>
		</div>

		{#if sprig}
			<!-- Primary remedy: one-click graft the Sprig™ that delivers this capability. -->
			<div
				class="rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950 p-4 mb-4"
			>
				<div class="text-sm text-emerald-900 dark:text-emerald-100 mb-3">
					{$i18n.t(
						'This capability is delivered by the {{sprig}} Sprig™. Graft it to restore the service — no model download, no restart.',
						{ sprig }
					)}
				</div>
				<button
					type="button"
					class="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-sm disabled:opacity-60 disabled:cursor-not-allowed"
					on:click={handleGraft}
					disabled={grafting}
				>
					{#if grafting}
						<Spinner className="size-4" />
						<span>{$i18n.t('Grafting {{sprig}}…', { sprig })}</span>
					{:else}
						<span aria-hidden="true">🌱</span>
						<span>{$i18n.t('Graft {{sprig}}', { sprig })}</span>
					{/if}
				</button>
			</div>

			{#if documented}
				<button
					type="button"
					class="text-xs text-blue-700 dark:text-blue-300 hover:underline mb-3"
					on:click={() => (showManualFix = !showManualFix)}
				>
					{showManualFix
						? $i18n.t('Hide manual steps')
						: $i18n.t('Other ways to fix this')}
				</button>
			{/if}
		{/if}

		<!-- Manual / deployment-shape steps: primary when there is no Sprig™ fix;
		     tucked behind "Other ways to fix this" when a graft is offered. -->
		{#if !sprig || showManualFix}
		{#if !documented}
			<div
				class="rounded-lg border border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-950 p-3 text-sm text-yellow-900 dark:text-yellow-200"
			>
				{$i18n.t(
					'This issue type is not yet documented. See Technical detail and the command library below.'
				)}
			</div>
		{:else if entry}
			<div class="text-sm text-gray-800 dark:text-gray-200 mb-4">
				{$i18n.t(entry.plain_english_key)}
			</div>

			{#if needsShapePicker}
				<fieldset class="mb-4">
					<legend class="text-sm font-semibold mb-2 text-gray-900 dark:text-gray-100">
						{#if shapeConfidence === 'low'}
							{$i18n.t("We're not sure of your deployment type")}
						{:else}
							{$i18n.t('Pick your deployment')}
						{/if}
					</legend>
					<div class="flex flex-col gap-2">
						{#each ['caprover', 'docker_compose', 'brew'] as shape}
							<label
								class="flex items-center gap-2 text-sm text-gray-800 dark:text-gray-200 cursor-pointer"
							>
								<input
									type="radio"
									name="deployment-shape"
									value={shape}
									bind:group={selectedShape}
								/>
								<span>{shapeLabel(shape)}</span>
							</label>
						{/each}
					</div>
				</fieldset>
			{:else}
				<div class="mb-3">
					<h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
						{$i18n.t('Steps for {{SHAPE}}', { SHAPE: shapeLabel(activeShape) })}
					</h3>
					<ol class="list-decimal list-inside space-y-3 text-sm text-gray-800 dark:text-gray-200">
						{#each primarySteps as step}
							<li>
								<div>{$i18n.t(step.description_key)}</div>
								{#if step.ui_path}
									<div class="mt-1 text-xs text-gray-600 dark:text-gray-400">
										{$i18n.t('UI path')}: <code>{step.ui_path}</code>
									</div>
								{/if}
								{#if step.command}
									<div class="mt-2 flex items-start gap-2">
										<pre
											class="text-xs bg-gray-100 dark:bg-gray-800 rounded p-2 overflow-x-auto flex-1 text-gray-800 dark:text-gray-200">{step.command}</pre>
										<button
											type="button"
											class="text-xs px-2 py-1 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 flex-none"
											on:click={() => handleCopy(step.command ?? '')}
											aria-label={$i18n.t('Copy command')}
											title={$i18n.t('Copy')}
										>
											{$i18n.t('Copy')}
										</button>
									</div>
								{/if}
							</li>
						{/each}
					</ol>

					{#if shapeConfidence === 'high'}
						<button
							type="button"
							class="mt-4 text-xs text-blue-700 dark:text-blue-300 hover:underline"
							on:click={() => (showOtherShapes = !showOtherShapes)}
						>
							{#if showOtherShapes}
								{$i18n.t('Hide other deployment types')}
							{:else}
								{$i18n.t('Not on {{SHAPE}}? Show other deployment types', {
									SHAPE: shapeLabel(activeShape)
								})}
							{/if}
						</button>

						{#if showOtherShapes && allShapes}
							<div class="mt-3 space-y-4">
								{#each ['caprover', 'docker_compose', 'brew'].filter((s) => s !== activeShape) as otherShape}
									{@const otherSteps = allShapes[otherShape]}
									{#if otherSteps.length > 0}
										<div
											class="rounded border border-gray-200 dark:border-gray-700 p-3 bg-gray-50 dark:bg-gray-900"
										>
											<h4
												class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2"
											>
												{shapeLabel(otherShape)}
											</h4>
											<ol
												class="list-decimal list-inside space-y-2 text-sm text-gray-800 dark:text-gray-200"
											>
												{#each otherSteps as step}
													<li>
														<div>{$i18n.t(step.description_key)}</div>
														{#if step.command}
															<div class="mt-1 flex items-start gap-2">
																<pre
																	class="text-xs bg-gray-100 dark:bg-gray-800 rounded p-2 overflow-x-auto flex-1 text-gray-800 dark:text-gray-200">{step.command}</pre>
																<button
																	type="button"
																	class="text-xs px-2 py-1 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 flex-none"
																	on:click={() =>
																		handleCopy(step.command ?? '')}
																	aria-label={$i18n.t('Copy command')}
																>
																	{$i18n.t('Copy')}
																</button>
															</div>
														{/if}
													</li>
												{/each}
											</ol>
										</div>
									{/if}
								{/each}
							</div>
						{/if}
					{/if}
				</div>
			{/if}
		{/if}
		{/if}
	</div>
</Modal>
