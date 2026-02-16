<script lang="ts">
	import { page } from '$app/stores';
	import NoteEditor from '$lib/components/notes/NoteEditor.svelte';
</script>

<div id="note-container" style="--w:100%; --fx:1 1 0%; --h:100%">
	<NoteEditor id={$page.params.id} />
</div>
