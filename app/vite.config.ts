import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

import { viteStaticCopy } from 'vite-plugin-static-copy';

// THE DEV PROXY. `vite dev` serves the SPA on 5173; everything below belongs to
// the FastAPI app on 8080 and is forwarded to it. In production none of this
// runs — FastAPI serves the built SPA itself and there is no proxy at all.
//
// A LIST, NOT EIGHT OBJECT LITERALS. It used to be one block per path, so
// adding a route meant copying a block, and that is exactly why it drifted:
// `/pages` was never added, so every no-build surface 404'd in dev while
// working perfectly in the image. Add a prefix to the array now and it is one
// line.
//
// Backend routes are registered in `backend/sage_is_ai/main.py`. Not derived
// from it on purpose — parsing Python from TypeScript to save editing a list
// twice a year is a parser to maintain plus a guard for the parser, and the
// failure it prevents is a dev 404 that costs thirty seconds once you know this
// file exists.
//
// NEVER ADD '/'. `main.py` mounts the whole SPA there with `html=True`, and a
// '/' key here matches every request — including Vite's own `/@vite/client`,
// `/src/*` and `/node_modules/*`. What sits at '/' is precisely what Vite
// REPLACES in dev.
const API = 'http://localhost:8080';

const BACKEND = [
	'/api',
	'/static',
	'/uploads',
	'/ws', // socket.io — needs the websocket flag below
	'/user.png',
	'/pages', // the server-rendered no-build surfaces
	'/themes', // active.css  — a grafted Theme Sprig™
	'/ui' // active.html — a grafted ui-Sprig™ fragment
];

// Published at the root, served out of /static, so these carry a rewrite.
// `/user.png` is deliberately NOT here — it was proxied without one.
const FROM_STATIC = ['/manifest.json', '/opensearch.xml', '/robots.txt', '/favicon.ico'];

const backendProxy = {
	...Object.fromEntries(
		BACKEND.map((path) => [path, { target: API, changeOrigin: true, ws: path === '/ws' }])
	),
	...Object.fromEntries(
		FROM_STATIC.map((path) => [
			path,
			{ target: API, changeOrigin: true, rewrite: () => '/static' + path }
		])
	)
};

// /** @type {import('vite').Plugin} */
const viteServerConfig = {
	name: 'log-request-middleware',
	configureServer(server: any) {
		server.middlewares.use((req: any, res: any, next: any) => {
			res.setHeader('Access-Control-Allow-Origin', '*');
			res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
			res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

			// Only set COEP headers for production builds, not in development
			// COEP can cause issues with development tools and localhost
			const isDevelopment = process.env.NODE_ENV !== 'production';
			if (!isDevelopment) {
				res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
				res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');
			}
			next();
		});
	}
};

export default defineConfig({
	plugins: [
		sveltekit(),
		viteServerConfig,
		viteStaticCopy({
			targets: [
				{
					src: 'node_modules/onnxruntime-web/dist/*.jsep.*',

					dest: 'wasm'
				}
			]
		})
	],
	define: {
		APP_VERSION: JSON.stringify(process.env.npm_package_version),
		APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build')
	},
	build: {
		// No sourcemaps in shipped builds — 54MB of .js.map in the image (8.I.1).
		// Flip to true locally when debugging a production bundle.
		sourcemap: false
	},
	worker: {
		format: 'es'
	},
	// Add development specific settings
	server: {
		hmr: {
			overlay: true
		},
		// Built from the lists at the top of this file. See the note there before
		// adding a path — especially the one about never adding '/'.
		proxy: backendProxy,
		// Optimize hot reload
		watch: {
			usePolling: false,
			ignored: ['**/node_modules/**', '**/dist/**']
		}
	},
	optimizeDeps: {
		exclude: ['pyodide'] // Prevent Vite from trying to optimize Pyodide
	}
});