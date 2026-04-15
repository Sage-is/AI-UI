import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

import { viteStaticCopy } from 'vite-plugin-static-copy';

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
		sourcemap: true
	},
	worker: {
		format: 'es'
	},
	// Add development specific settings
	server: {
		hmr: {
			overlay: true
		},
		// Add proxy if needed for your backend
		proxy: {
			'/api': {
				target: 'http://localhost:8080',
				changeOrigin: true
			},
			'/static': {  // Proxy the static folder
				target: 'http://localhost:8080',
				changeOrigin: true
			},
			'/sprites': {  // Proxy the sprites folder
				target: 'http://localhost:8080',
				changeOrigin: true,
				rewrite: (path) => '/static' + path
			},
			'/uploads': {  // Proxy the uploads folder
				target: 'http://localhost:8080',
				changeOrigin: true
			},
			'/manifest.json': {  // Proxy the manifest.json file
				target: 'http://localhost:8080',
				changeOrigin: true,
				rewrite: (path) => '/static' + path
			},
			'/opensearch.xml': {  // Proxy the opensearch.xml file
				target: 'http://localhost:8080',
				changeOrigin: true,
				rewrite: (path) => '/static' + path
			},
			'/robots.txt': {  // Proxy the robots.txt file
				target: 'http://localhost:8080',
				changeOrigin: true,
				rewrite: (path) => '/static' + path
			},
			'/favicon.ico': {  // Proxy the favicon.ico file
				target: 'http://localhost:8080',
				changeOrigin: true,
				rewrite: (path) => '/static' + path
			},
			'/user.png': {  // Proxy the user.png file
				target: 'http://localhost:8080',
				changeOrigin: true
			},
		},
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