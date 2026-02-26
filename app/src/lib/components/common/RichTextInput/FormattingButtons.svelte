<script>
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	/** @type {any} */
	export let editor = null;

	import Bold from '$lib/components/icons/Bold.svelte';
	import CodeBracket from '$lib/components/icons/CodeBracket.svelte';
	import H1 from '$lib/components/icons/H1.svelte';
	import H2 from '$lib/components/icons/H2.svelte';
	import H3 from '$lib/components/icons/H3.svelte';
	import Italic from '$lib/components/icons/Italic.svelte';
	import ListBullet from '$lib/components/icons/ListBullet.svelte';
	import NumberedList from '$lib/components/icons/NumberedList.svelte';
	import Strikethrough from '$lib/components/icons/Strikethrough.svelte';
	import Underline from '$lib/components/icons/Underline.svelte';
	import CheckBox from '$lib/components/icons/CheckBox.svelte';
	import ArrowLeftTag from '$lib/components/icons/ArrowLeftTag.svelte';
	import ArrowRightTag from '$lib/components/icons/ArrowRightTag.svelte';

	import Tooltip from '../Tooltip.svelte';

	// Shared styling constants
	const BASE_BUTTON_CLASSES =
		'hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all';
	const ACTIVE_BUTTON_CLASSES = 'bg-gray-50 dark:bg-gray-700';

	// Button configuration
	const buttons = [
		{
			id: 'h1',
			icon: H1,
			tooltip: 'H1',
			action: () => editor?.chain().focus().toggleHeading({ level: 1 }).run(),
			isActive: () => editor?.isActive('heading', { level: 1 })
		},
		{
			id: 'h2',
			icon: H2,
			tooltip: 'H2',
			action: () => editor?.chain().focus().toggleHeading({ level: 2 }).run(),
			isActive: () => editor?.isActive('heading', { level: 2 })
		},
		{
			id: 'h3',
			icon: H3,
			tooltip: 'H3',
			action: () => editor?.chain().focus().toggleHeading({ level: 3 }).run(),
			isActive: () => editor?.isActive('heading', { level: 3 })
		},
		{
			id: 'bulletList',
			icon: ListBullet,
			tooltip: 'Bullet List',
			action: () => editor?.chain().focus().toggleBulletList().run(),
			isActive: () => editor?.isActive('bulletList')
		},
		{
			id: 'orderedList',
			icon: NumberedList,
			tooltip: 'Ordered List',
			action: () => editor?.chain().focus().toggleOrderedList().run(),
			isActive: () => editor?.isActive('orderedList')
		},
		{
			id: 'taskList',
			icon: CheckBox,
			tooltip: 'Task List',
			action: () => editor?.chain().focus().toggleTaskList().run(),
			isActive: () => editor?.isActive('taskList')
		},
		{
			id: 'bold',
			icon: Bold,
			tooltip: 'Bold',
			action: () => editor?.chain().focus().toggleBold().run(),
			isActive: () => editor?.isActive('bold')
		},
		{
			id: 'italic',
			icon: Italic,
			tooltip: 'Italic',
			action: () => editor?.chain().focus().toggleItalic().run(),
			isActive: () => editor?.isActive('italic')
		},
		{
			id: 'underline',
			icon: Underline,
			tooltip: 'Underline',
			action: () => editor?.chain().focus().toggleUnderline().run(),
			isActive: () => editor?.isActive('underline')
		},
		{
			id: 'strike',
			icon: Strikethrough,
			tooltip: 'Strikethrough',
			action: () => editor?.chain().focus().toggleStrike().run(),
			isActive: () => editor?.isActive('strike')
		},
		{
			id: 'codeBlock',
			icon: CodeBracket,
			tooltip: 'Code Block',
			action: () => editor?.chain().focus().toggleCodeBlock().run(),
			isActive: () => editor?.isActive('codeBlock')
		}
	];

	// List indentation buttons (conditional)
	const listIndentButtons = [
		{
			id: 'liftList',
			icon: ArrowLeftTag,
			tooltip: 'Lift List',
			action: () => {
				editor?.commands.liftListItem(editor?.isActive('taskList') ? 'taskItem' : 'listItem');
			}
		},
		{
			id: 'sinkList',
			icon: ArrowRightTag,
			tooltip: 'Sink List',
			action: () => {
				editor?.commands.sinkListItem(editor?.isActive('taskList') ? 'taskItem' : 'listItem');
			}
		}
	];

	$: showListIndent =
		editor?.isActive('bulletList') ||
		editor?.isActive('orderedList') ||
		editor?.isActive('taskList');
</script>

<div
	style="--d:flex; --g:0.125rem; --p:0.125rem; --radius:0.5rem; --shadow:4; --bgc:#fff; --c:var(--color-gray-800); --dark-c:#fff; --dark-bgc:var(--color-gray-800); --minw:fit-content"
>
	<!-- Heading buttons (first 3 buttons) -->
	{#each buttons.slice(0, 3) as button (button.id)}
		<Tooltip placement="top" content={$i18n.t(button.tooltip)}>
			<button
				on:click={button.action}
				class="{button.isActive() ? ACTIVE_BUTTON_CLASSES : ''} {BASE_BUTTON_CLASSES}"
				type="button"
			>
				<svelte:component this={button.icon} />
			</button>
		</Tooltip>
	{/each}

	<!-- List indent buttons (conditional) -->
	{#if showListIndent}
		{#each listIndentButtons as button (button.id)}
			<Tooltip placement="top" content={$i18n.t(button.tooltip)}>
				<button on:click={button.action} class={BASE_BUTTON_CLASSES} type="button">
					<svelte:component this={button.icon} />
				</button>
			</Tooltip>
		{/each}
	{/if}

	<!-- List and formatting buttons (remaining buttons) -->
	{#each buttons.slice(3) as button (button.id)}
		<Tooltip placement="top" content={$i18n.t(button.tooltip)}>
			<button
				on:click={button.action}
				class="{button.isActive() ? ACTIVE_BUTTON_CLASSES : ''} {BASE_BUTTON_CLASSES}"
				type="button"
			>
				<svelte:component this={button.icon} />
			</button>
		</Tooltip>
	{/each}
</div>
