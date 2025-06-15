import {defineConfig} from 'vite'
import crossOriginIsolation from 'vite-plugin-cross-origin-isolation'
import {sveltekit} from '@sveltejs/kit/vite';
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit(),
		crossOriginIsolation()
	],
	server: {
		host: '0.0.0.0',
		hmr: {
			clientPort: 5000,
		},
		port: 5000,
		open: false,
		allowedHosts: ['ui'],
	},
	worker: {
		format: 'es'
	}
})
