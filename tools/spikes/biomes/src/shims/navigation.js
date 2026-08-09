// `$app/navigation` shim. THROWAWAY (the idea is not).
//
// The plan calls the per-biome work "excising SvelteKit-only imports (a
// `$app/navigation` shim)" and assumes it is small. This file is the claim made
// concrete: an alias points `$app/navigation` here, and a component that
// imports `goto` compiles and runs outside SvelteKit unchanged.
//
// Scope note: `goto` here does a real history push and fires `popstate`, which
// is what a server-rendered shell would listen for. The options SvelteKit
// accepts (replaceState, keepFocus, invalidateAll) are accepted and ignored —
// enough for the surfaces that move first, and a real component would tell us
// loudly if it needed more, because it would stop working.
export function goto(url, opts = {}) {
  if (opts.replaceState) history.replaceState({}, '', url);
  else history.pushState({}, '', url);
  dispatchEvent(new PopStateEvent('popstate'));
  return Promise.resolve();
}

export const invalidate = () => Promise.resolve();
export const invalidateAll = () => Promise.resolve();
export const preloadData = () => Promise.resolve();
export const preloadCode = () => Promise.resolve();
export const beforeNavigate = () => {};
export const afterNavigate = () => {};
export const onNavigate = () => {};
export const pushState = (url, state) => history.pushState(state, '', url);
export const replaceState = (url, state) => history.replaceState(state, '', url);
export const disableScrollHandling = () => {};
