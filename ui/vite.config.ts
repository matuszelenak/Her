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
                    src: 'node_modules/@ricky0123/vad-web/dist/vad.worklet.bundle.min.js',
                    dest: './'
                },
                {
                    src: 'node_modules/@ricky0123/vad-web/dist/silero_vad.onnx',
                    dest: './'
                },
                {
                    src: 'node_modules/onnxruntime-web/dist/*.wasm',
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
    },
    worker: {
        format: 'es'
    }
})
