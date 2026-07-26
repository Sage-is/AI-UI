// Memoized lazy loaders for the heavy markdown-render components.
//
// A plain-text conversation must pull none of katex, mermaid, highlight.js, or
// codemirror. These load only when a message actually renders math or a code
// fence. The memo (`??=`) is what makes it streaming-safe: each returns the SAME
// promise identity on every call, so `{#await loadX() then ...}` never flips
// back to its pending branch as tokens stream in — the module fetches once, then
// every re-render resolves from cache.

let katexRenderer: Promise<typeof import('./KatexRenderer.svelte')>;
export const loadKatexRenderer = () => (katexRenderer ??= import('./KatexRenderer.svelte'));

let codeBlock: Promise<typeof import('$lib/components/chat/Messages/CodeBlock.svelte')>;
export const loadCodeBlock = () =>
	(codeBlock ??= import('$lib/components/chat/Messages/CodeBlock.svelte'));
