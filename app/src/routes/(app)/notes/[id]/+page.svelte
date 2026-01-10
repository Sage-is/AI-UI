<script lang="ts">
	import { page } from '$app/stores';
	import NoteEditor from '$lib/components/notes/NoteEditor.svelte';
</script>

<div id="note-container" class="w-full flex-1 h-full">
	<NoteEditor id={$page.params.id} />
</div>
