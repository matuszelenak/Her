<script lang="ts">
    import workletUrl from "$lib/audio-processor.ts?url";
    import {type WebSocketEvent, WebsocketEventType} from "$lib/types";
    import {base64ToArrayBuffer} from "$lib/encoding";

    const MAX_AUDIO_BUFFER_SAMPLES = 65536 * 4

    const CTL_WRITE_IDX = 0
    const CTL_READ_IDX = 1
    const CTL_SAMPLES_AVAIL_IDX = 2
    const CTL_WORKLET_WAITING_IDX = 3
    const CONTROL_SAB_SIZE_BYTES = 4 * Int32Array.BYTES_PER_ELEMENT

    const sabSupported = typeof SharedArrayBuffer !== "undefined"

    let isConnected = $state(false)
    let isAudioSystemReady = $state(false)
    let error: string | null = $state(null)
    let displaySampleRate: number | null = $state(null)
    let needsUserInteraction = $state(false)

    let audioContext: AudioContext | null = null
    let workletNode: AudioWorkletNode | null = null
    let webSocket: WebSocket | null = null
    let audioSAB: SharedArrayBuffer | null = null
    let controlSAB: SharedArrayBuffer | null = null
    let audioBufferView: Float32Array | null = null
    let controlBufferView: Int32Array | null = null

    function log(level: string, message: string) {
        if (level === 'error') console.error(`[SveltePlayer] ${message}`)
        else console.log(`[SveltePlayer] ${message}`)
    }

    async function initAudioSystem() {
        try {
            log('info', "Initializing audio system...")
            audioSAB = new SharedArrayBuffer(MAX_AUDIO_BUFFER_SAMPLES * Float32Array.BYTES_PER_ELEMENT)
            controlSAB = new SharedArrayBuffer(CONTROL_SAB_SIZE_BYTES)

            audioBufferView = new Float32Array(audioSAB)
            controlBufferView = new Int32Array(controlSAB)

            Atomics.store(controlBufferView, CTL_WRITE_IDX, 0)
            Atomics.store(controlBufferView, CTL_READ_IDX, 0)
            Atomics.store(controlBufferView, CTL_SAMPLES_AVAIL_IDX, 0)
            Atomics.store(controlBufferView, CTL_WORKLET_WAITING_IDX, 0)

            audioContext = new AudioContext()
            log('info', `AudioContext created. Initial state: ${audioContext.state}, Sample rate: ${audioContext.sampleRate}`)

            if (audioContext.state === 'suspended') {
                needsUserInteraction = true;
                log('info', "AudioContext is suspended. User interaction required.")
            }

            await audioContext.audioWorklet.addModule(workletUrl)
            log('info', "AudioWorklet module loaded.")

            workletNode = new AudioWorkletNode(audioContext, 'audio-processor', {
                numberOfOutputs: 2,
                outputChannelCount: [2, 2],
                processorOptions: {
                    audioSAB: audioSAB,
                    controlSAB: controlSAB,
                }
            })
            log('info', "AudioWorkletNode created.")

            workletNode.port.onmessage = (event) => {
                if (event.data?.type === 'error') {
                    error = `Worklet Error: ${event.data.message}`
                    log('error', error)
                    isAudioSystemReady = false
                } else if (event.data?.type === 'worklet_ready') {
                    log('info', "AudioWorklet reported ready.")
                    if (audioContext!.state === 'running') {
                        isAudioSystemReady = true
                        displaySampleRate = audioContext!.sampleRate
                        error = null
                        if (webSocket && webSocket.readyState === WebSocket.OPEN) {
                            sendSampleRateToBackend(audioContext!.sampleRate)
                        }
                    } else {
                        log('info', "Worklet ready, but AudioContext still suspended.")
                        needsUserInteraction = true
                    }
                } else if (event.data?.type === 'control') {
                    sendControlCommandToBackend(event.data.command)
                }
            }

            workletNode.connect(audioContext.destination)
            log('info', "AudioWorkletNode connected to destination.")

            return true

        } catch (errMessage) {
            error = `Audio system initialization failed: ${(errMessage as Error).message || errMessage}`
            log('error', error)
            return false
        }
    }

    async function handleUserInteraction() {
        if (!audioContext || !needsUserInteraction) return

        log('info', "Attempting to resume AudioContext due to user interaction...")
        try {
            await audioContext.resume()
            log('info', `AudioContext resumed. Current state: ${audioContext.state}`)
            if (audioContext.state === 'running') {
                needsUserInteraction = false
                if (workletNode && !isAudioSystemReady) {
                    log('info', "Context running and worklet exists, setting audio system ready.")
                    isAudioSystemReady = true
                    displaySampleRate = audioContext.sampleRate
                    error = null
                    if (webSocket && webSocket.readyState === WebSocket.OPEN) {
                        sendSampleRateToBackend(audioContext.sampleRate)
                    }
                }
            } else {
                error = "Failed to resume AudioContext. State: " + audioContext.state
                log('error', error)
            }
        } catch (errMessage) {
            error = `Error resuming AudioContext: ${(errMessage as Error).message || errMessage}`
            log('error', error)
        }
    }

    function connectWebSocket() {
        if (!sabSupported) {
            log('warn', "WebSocket connection aborted: SAB not supported or audio init failed.")
            return
        }
        const WEBSOCKET_URL = `${window.location.protocol == "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws/audio`
        log('info', `Attempting to connect WebSocket to ${WEBSOCKET_URL}...`)
        webSocket = new WebSocket(WEBSOCKET_URL)
        webSocket.binaryType = 'arraybuffer';

        webSocket.onopen = () => {
            isConnected = true
            error = null
            log('info', "WebSocket connected.")
            if (isAudioSystemReady && audioContext) {
                sendSampleRateToBackend(audioContext.sampleRate)
            }
        }

        webSocket.onmessage = (event: MessageEvent) => {
            // const message = JSON.parse(event.data) as WebSocketEvent

            if (event.data instanceof ArrayBuffer) {
                // const incomingSamples = new Float32Array(base64ToArrayBuffer(message.samples))

                addAudioDataToSAB(new Float32Array(event.data))
            } else {
                log('warn', `Received unexpected message type from server: ${typeof event.data}`)
            }
        }

        webSocket.onerror = (errEvent) => {
            error = "WebSocket connection error."
            log('error', `${error} Event: ${JSON.stringify(errEvent)}`)
            isConnected = false;
        }

        webSocket.onclose = (event) => {
            isConnected = false
            log('info', `WebSocket disconnected. Code: ${event.code}, Reason: "${event.reason}"`)
        }
    }

    function sendSampleRateToBackend(rate: number) {
        if (webSocket && webSocket.readyState === WebSocket.OPEN) {
            log('info', `Sending sample rate to backend: ${rate}`)
            webSocket.send(JSON.stringify({ type: 'set_sample_rate', rate: rate }))
        }
    }

    function addAudioDataToSAB(samples: Float32Array) {
        if (!audioBufferView || !controlBufferView || samples.length === 0) return

        const numIncomingSamples = samples.length
        let currentSamplesAvailable = Atomics.load(controlBufferView, CTL_SAMPLES_AVAIL_IDX)

        if (currentSamplesAvailable + numIncomingSamples > MAX_AUDIO_BUFFER_SAMPLES) {
            log('warn', `SAB buffer full! Dropping ${numIncomingSamples} samples. Available: ${currentSamplesAvailable}`)
            return;
        }

        let writePointer = Atomics.load(controlBufferView, CTL_WRITE_IDX)
        const spaceToEnd = MAX_AUDIO_BUFFER_SAMPLES - writePointer

        if (numIncomingSamples <= spaceToEnd) {
            for (let i = 0; i < numIncomingSamples; i++) {
                audioBufferView[writePointer + i] = samples[i]
            }
            writePointer += numIncomingSamples
        } else {
            for (let i = 0; i < spaceToEnd; i++) {
                audioBufferView[writePointer + i] = samples[i]
            }
            for (let i = 0; i < numIncomingSamples - spaceToEnd; i++) {
                audioBufferView[i] = samples[spaceToEnd + i]
            }
            writePointer = numIncomingSamples - spaceToEnd
        }
        if (writePointer === MAX_AUDIO_BUFFER_SAMPLES) writePointer = 0

        Atomics.store(controlBufferView, CTL_WRITE_IDX, writePointer)
        Atomics.add(controlBufferView, CTL_SAMPLES_AVAIL_IDX, numIncomingSamples)
    }

    function sendControlCommandToBackend(command: string) {
        if (webSocket && webSocket.readyState === WebSocket.OPEN) {
            log('info', `Sending command to backend: ${command}`)
            webSocket.send(JSON.stringify({ type: 'flow_control', command: command }))
        }
    }

    // Main setup and teardown effect
    $effect(() => {
        log('info', "Main setup effect running.")
        if (!sabSupported) {
            error = "Critical: SharedArrayBuffer is not supported in this browser or context. Ensure COOP/COEP headers are correctly set on your server."
            log('error', error)
            return; // Stop further setup if SAB not supported
        }

        // Asynchronous setup logic
        async function mountLogic() {
            const audioInitSuccess = await initAudioSystem()
            if (audioInitSuccess) {
                connectWebSocket()
            } else {
                log('error', "Audio system initialization failed, WebSocket connection aborted.")
            }
        }

        mountLogic()

        // Cleanup function for this effect (equivalent to onDestroy)
        return () => {
            log('info', "Main setup effect cleanup (onDestroy equivalent)...")
            if (webSocket) {
                webSocket.close()
                webSocket = null
            }
            if (workletNode) {
                workletNode.disconnect()
                workletNode = null
            }
            if (audioContext) {
                audioContext.close().catch(e => log('error', `Error closing AudioContext: ${e}`))
                audioContext = null
            }

            // SABs and views will be garbage collected
            audioSAB = null; controlSAB = null; audioBufferView = null; controlBufferView = null
            log('info', "Resources cleaned up.")
        }
    })

</script>

<main>
    <h1>Svelte SAB Audio Player (Runes)</h1>

    {#if !sabSupported} <div class="status error-box">
        <p><strong>Compatibility Error:</strong> SharedArrayBuffer is not supported.</p>
        <p>Please ensure your browser supports it and that the page is served with the necessary COOP (Cross-Origin-Opener-Policy: same-origin) and COEP (Cross-Origin-Embedder-Policy: require-corp) HTTP headers.</p>
    </div>
    {/if}

    {#if needsUserInteraction && sabSupported}
        <div class="status warning-box interactive-area" onclick={handleUserInteraction} onkeydown={handleUserInteraction} role="button" tabindex="0">
            <p>Audio is suspended. Click here to enable audio playback.</p>
        </div>
    {/if}

    <div class="status-grid">
        <div>WebSocket:</div>
        <div class:connected={isConnected} class:disconnected={!isConnected}>
            {isConnected ? 'Connected' : 'Disconnected'}
        </div>

        <div>Audio System:</div>
        <div class:ready={isAudioSystemReady} class:not-ready={!isAudioSystemReady}>
            {#if !sabSupported}
                Not Supported
            {:else if isAudioSystemReady}
                Ready (Sample Rate: {displaySampleRate || 'N/A'} Hz)
            {:else if needsUserInteraction}
                Needs User Interaction
            {:else}
                Initializing...
            {/if}
        </div>
    </div>

    {#if error && sabSupported} <div class="status error-box general-error">
        <p><strong>Error:</strong> {error}</p>
    </div>
    {/if}

</main>

<style>
    main {
        font-family: Arial, sans-serif;
        padding: 20px;
        max-width: 600px;
        margin: 0 auto;
        background-color: #f4f4f4;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    h1 {
        color: #333;
        text-align: center;
        margin-bottom: 20px;
    }
    .status-grid {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 10px 20px;
        background-color: #fff;
        padding: 15px;
        border-radius: 6px;
        margin-bottom: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .status-grid > div:nth-child(odd) {
        font-weight: bold;
        color: #555;
    }
    .connected, .ready { color: #28a745; font-weight: bold; }
    .disconnected, .not-ready { color: #dc3545; font-weight: bold; }

    .status {
        padding: 10px 15px;
        margin-bottom: 15px;
        border-radius: 5px;
        border: 1px solid transparent;
    }
    .error-box {
        background-color: #f8d7da;
        color: #721c24;
        border-color: #f5c6cb;
    }
    .warning-box {
        background-color: #fff3cd;
        color: #856404;
        border-color: #ffeeba;
    }
    .interactive-area {
        cursor: pointer;
        text-align: center;
        font-weight: bold;
    }
    .interactive-area:hover {
        background-color: #ffeeba; /* Slightly darker yellow on hover */
    }
    .general-error {
        margin-top: 15px;
    }
</style>
