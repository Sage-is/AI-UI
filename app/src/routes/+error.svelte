<script>
	import { page } from '$app/stores';
</script>

<div style="--bgc:#fff; --dark-bgc:var(--color-gray-800, #333); --minh:100vh">
	<div style="--d:flex; --h:100%">
		<div style="--m:auto; --my:2.5rem; --dark-c:var(--color-gray-300, #cdcdcd); --size:1.875rem; --weight:600">
			{$page.status}: {$page.error?.message}
		</div>
	</div>
</div>
