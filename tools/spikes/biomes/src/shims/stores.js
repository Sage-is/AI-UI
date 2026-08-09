// `$app/stores` shim. THROWAWAY (the idea is not).
//
// `page` is the second half of the real surface: 26 of the 81 SvelteKit imports
// in app/src, against 54 for `goto`. Between them they are 80 of 81, so a shim
// covering these two covers essentially all of it.
//
// Components read `$page.url`, `$page.params` and `$page.route.id`. None of
// that needs a router — it is a store fed from `location`, updated whenever the
// history changes. The shim keeps the shape SvelteKit publishes so component
// source does not change.
import { readable } from 'svelte/store';

const snapshot = () => ({
  url: new URL(location.href),
  params: {},
  route: { id: location.pathname },
  status: 200,
  error: null,
  data: {},
  form: null,
  state: {}
});

export const page = readable(snapshot(), (set) => {
  const update = () => set(snapshot());
  addEventListener('popstate', update);
  return () => removeEventListener('popstate', update);
});

export const navigating = readable(null);
export const updated = Object.assign(readable(false), { check: () => Promise.resolve(false) });
