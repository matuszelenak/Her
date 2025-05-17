import {defineConfig} from 'vite'
import react from '@vitejs/plugin-react'
import crossOriginIsolation from 'vite-plugin-cross-origin-isolation'
import { viteStaticCopy } from 'vite-plugin-static-copy';


// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        react(),
        crossOriginIsolation(),
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
    optimizeDeps: {
        exclude: ['onnxruntime-web']
    },
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
