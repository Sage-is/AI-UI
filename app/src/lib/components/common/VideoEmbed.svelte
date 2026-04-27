<script lang="ts">
	/**
	 * VideoEmbed — narrow-scope embed component for the try.sage tutorial.
	 *
	 * WHY no playlist support: the tutorial is a step-by-step modal. Each step
	 * pairs one video with one explanation. A playlist URL would let YouTube's
	 * own queue overrule the per-step model, scrambling the workshop flow.
	 * Operators who want a playlist should split it into individual videos
	 * and configure them per step via TRY_SAGE_TUTORIAL_STEPS_JSON.
	 *
	 * WHY modestbranding + rel=0: the workshop is projected on a screen.
	 * The default YouTube end-screen suggestions and big logos are visual
	 * noise that distracts from the next-step CTA in the modal.
	 *
	 * Supported URL kinds (anything else falls through to a debug message):
	 *   - YouTube single video:  watch?v=ID  or  youtu.be/ID
	 *   - Vimeo single video:    vimeo.com/NUMERIC_ID
	 *   - Direct .mp4
	 */

	export let url: string;
	export let title: string = 'Tutorial video';

	type Kind =
		| { type: 'youtube'; id: string }
		| { type: 'vimeo'; id: string }
		| { type: 'mp4'; src: string }
		| { type: 'unsupported' };

	// Single-video matchers only. Playlist forms (`watch?list=`, plain
	// `playlist?list=`, shorts) intentionally fall through to `unsupported`.
	const YT_RE = /^https?:\/\/(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([A-Za-z0-9_-]{11})/;
	const VIMEO_RE = /^https?:\/\/(?:www\.)?vimeo\.com\/(\d+)/;
	const MP4_RE = /\.mp4($|\?)/i;

	function detect(u: string): Kind {
		if (!u) return { type: 'unsupported' };
		// Reject YouTube playlist-style URLs explicitly even when a video ID
		// is also present — the iframe would auto-queue the playlist.
		if (/[?&]list=/i.test(u) && /youtube\.com|youtu\.be/i.test(u)) {
			return { type: 'unsupported' };
		}
		const yt = u.match(YT_RE);
		if (yt) return { type: 'youtube', id: yt[1] };
		const vm = u.match(VIMEO_RE);
		if (vm) return { type: 'vimeo', id: vm[1] };
		if (MP4_RE.test(u)) return { type: 'mp4', src: u };
		return { type: 'unsupported' };
	}

	// Reactive: when `url` changes the kind re-derives and the markup
	// switches branches automatically.
	$: kind = detect(url);
</script>

<div class="aspect-video w-full overflow-hidden rounded-lg bg-black">
	{#if kind.type === 'youtube'}
		<iframe
			src={`https://www.youtube.com/embed/${kind.id}?modestbranding=1&rel=0`}
			{title}
			loading="lazy"
			allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
			allowfullscreen
			class="h-full w-full"
			frameborder="0"
		></iframe>
	{:else if kind.type === 'vimeo'}
		<iframe
			src={`https://player.vimeo.com/video/${kind.id}`}
			{title}
			loading="lazy"
			allow="autoplay; fullscreen; picture-in-picture"
			allowfullscreen
			class="h-full w-full"
			frameborder="0"
		></iframe>
	{:else if kind.type === 'mp4'}
		<!-- preload=metadata avoids blowing bandwidth on a workshop projector
		     before the attendee actually clicks play. -->
		<video controls preload="metadata" {title} class="h-full w-full">
			<source src={kind.src} type="video/mp4" />
			<track kind="captions" />
		</video>
	{:else}
		<div class="flex h-full w-full flex-col items-center justify-center gap-1 p-4 text-center text-sm text-gray-300">
			<div class="font-medium">Video format not supported</div>
			<div class="break-all text-xs text-gray-400">{url}</div>
			<div class="text-[0.65rem] text-gray-500">
				Supported: single YouTube/Vimeo videos and .mp4 URLs. Playlists are not supported.
			</div>
		</div>
	{/if}
</div>
