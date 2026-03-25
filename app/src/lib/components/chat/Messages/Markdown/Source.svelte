<script lang="ts">
	export let id;
	export let token;
	export let onClick: Function = () => {};

	let attributes: Record<string, string | undefined> = {};

	function extractAttributes(input: string): Record<string, string> {
		const regex = /(\w+)="([^"]*)"/g;
		let match;
		let attrs: Record<string, string> = {};

		// Loop through all matches and populate the attributes object
		while ((match = regex.exec(input)) !== null) {
			attrs[match[1]] = match[2];
		}

		return attrs;
	}

	// Helper function to return only the domain from a URL
	function getDomain(url: string): string {
		const domain = url.replace('http://', '').replace('https://', '').split(/[/?#]/)[0];
		return domain;
	}

	// Helper function to check if text is a URL and return the domain
	function formattedTitle(title: string): string {
		if (title.startsWith('http')) {
			return getDomain(title);
		}

		return title;
	}

	$: attributes = extractAttributes(token.text);
</script>

{#if attributes.title !== 'N/A'}
	<button
		style="--size:0.6rem; --weight:500; --w:fit-content; --translatey:2px; --px:0.5rem; --py:0.125rem; --dark-bgc:rgb(255 255 255 / 0.05); --dark-c:rgb(255 255 255 / 0.6); --hvr-dark-c:#fff; --bgc:var(--color-gray-50); --c:rgb(0 0 0 / 0.6); --hvr-c:#000; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:0.5rem"
		on:click={() => {
			onClick(id, attributes.data);
		}}
	>
		<span style="--line-clamp:1">
			{attributes.title ? formattedTitle(attributes.title) : ''}
		</span>
	</button>
{/if}
