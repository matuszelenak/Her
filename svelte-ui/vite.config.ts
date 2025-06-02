import {defineConfig} from 'vite'
import crossOriginIsolation from 'vite-plugin-cross-origin-isolation'
import {sveltekit} from '@sveltejs/kit/vite';

export default defineConfig({
	plugins: [
		sveltekit(),
		crossOriginIsolation()
	],
	server: {
		host: '0.0.0.0',
		hmr: {
			clientPort: 5001,
		},
		port: 5001,
		open: false,
		allowedHosts: ['ui'],
	},
	worker: {
		format: 'es'
	}
})
