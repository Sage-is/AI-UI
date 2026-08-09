// `$app/environment` shim. THROWAWAY (the idea is not).
//
// Three imports in app/src, all trivially true or build-time constants once
// there is no server-side rendering step to be false for.
export const browser = true;
export const dev = false;
export const building = false;
export const version = 'biome';
