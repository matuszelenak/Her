import {defineConfig} from 'vite'
import {sveltekit} from '@sveltejs/kit/vite';
import tailwindcss from "@tailwindcss/vite";
import {viteStaticCopy} from "vite-plugin-static-copy";

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit(),
		{
			name: "isolation",
			configureServer(server) {
				server.middlewares.use((_req, res, next) => {
					res.setHeader("Cross-Origin-Opener-Policy", "same-origin");
					res.setHeader("Cross-Origin-Embedder-Policy", "require-corp");
					next();
				});
			},
		},
		viteStaticCopy({
			targets: [
				{
					src: 'node_modules/onnxruntime-web/dist/*.wasm',
					dest: './'
				},
				{
					src: 'node_modules/onnxruntime-web/dist/*.mjs',
					dest: './'
				}
			]
		})
	],
	server: {
		host: '0.0.0.0',
		hmr: {
			clientPort: 5000,
		},
		port: 5000,
		open: false,
		allowedHosts: ['ui']
	},
	worker: {
		format: 'es'
	}
})
