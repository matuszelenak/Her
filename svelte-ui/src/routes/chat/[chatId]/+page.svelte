<script lang="ts">
    import {createQuery} from '@tanstack/svelte-query'
    import {page} from '$app/state';
    import SvelteMarkdown from '@humanspeak/svelte-markdown'

    import type {PageData} from './$types'
    import {getChat} from "$lib/api";
    import {log} from "$lib/log";
    import {type Message, type WebSocketEvent, WebsocketEventType} from "$lib/types";
    import workletUrl from "$lib/audio-processor.ts?url";
    import {base64ToArrayBuffer} from "$lib/encoding";

    const MAX_AUDIO_BUFFER_SAMPLES = 65536 * 4

    const CTL_WRITE_IDX = 0
    const CTL_READ_IDX = 1
    const CTL_SAMPLES_AVAIL_IDX = 2
    const CTL_WORKLET_WAITING_IDX = 3
    const CONTROL_SAB_SIZE_BYTES = 4 * Int32Array.BYTES_PER_ELEMENT

    const sabSupported = typeof SharedArrayBuffer !== "undefined"


    let data: PageData

    let audioContext: AudioContext | null = null
    let workletNode: AudioWorkletNode | null = null
    let webSocket: WebSocket | null = null
    let audioSAB: SharedArrayBuffer | null = null
    let controlSAB: SharedArrayBuffer | null = null
    let audioBufferView: Float32Array | null = null
    let controlBufferView: Int32Array | null = null
    let isConnected = $state(false)
    let messages: Message[] = $state([])
    let manualUserMessage = $state("")
    let agentMessage = $state("")

    function connectWebSocket() {
        const WEBSOCKET_URL = `${window.location.protocol == "https:" ? "wss:" : "ws:"}//localhost:8000/ws/chat/${page.params.chatId}`
        webSocket = new WebSocket(WEBSOCKET_URL)
        webSocket.onopen = () => {
            isConnected = true
        }

        webSocket.onmessage = (event: MessageEvent) => {
            const message = JSON.parse(event.data) as WebSocketEvent

            if (message.type == WebsocketEventType.TOKEN) {
                if (message.token != null) {
                    agentMessage = `${agentMessage}${message.token.message.content}`
                } else {
                    messages = [...messages, {role: 'assistant', content: agentMessage}]
                    agentMessage = ""
                }
            }
            if (message.type == WebsocketEventType.MANUAL_PROMPT) {
                messages = [...messages, {role: 'user', content: message.text}]
            }
            if (message.type == WebsocketEventType.SPEECH_SAMPLES) {
                const incomingSamples = new Float32Array(base64ToArrayBuffer(message.samples))
                addAudioDataToSAB(incomingSamples)
            }
        }

        webSocket.onerror = (errEvent) => {
            isConnected = false;
        }

        webSocket.onclose = (event) => {
            isConnected = false
            log('info', `WebSocket disconnected. Code: ${event.code}, Reason: "${event.reason}"`)
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
                log('info', "AudioContext is suspended. User interaction required.")
            }

            await audioContext.audioWorklet.addModule(workletUrl)

            workletNode = new AudioWorkletNode(audioContext, 'audio-processor', {
                numberOfOutputs: 2,
                outputChannelCount: [2, 2],
                processorOptions: {
                    audioSAB: audioSAB,
                    controlSAB: controlSAB,
                }
            })

            workletNode.port.onmessage = (event) => {
                if (event.data?.type === 'error') {
                    log('error', `Worklet Error: ${event.data.message}`)
                } else if (event.data?.type === 'worklet_ready') {
                    log('info', "AudioWorklet reported ready.")
                    if (audioContext!.state === 'running') {
                        if (webSocket && webSocket.readyState === WebSocket.OPEN) {
                            webSocket.send(JSON.stringify({type: 'set_sample_rate', rate: audioContext!.sampleRate}))
                        }
                    } else {
                        log('info', "Worklet ready, but AudioContext still suspended.")
                    }
                } else if (event.data?.type === 'control') {
                    if (webSocket && webSocket.readyState === WebSocket.OPEN) {
                        webSocket.send(JSON.stringify({type: 'flow_control', command: event.data.command}))
                    }
                }
            }

            workletNode.connect(audioContext.destination)
            log('info', "AudioWorkletNode connected to destination.")

            return true

        } catch (errMessage) {
            log('error', `Audio system initialization failed: ${(errMessage as Error).message || errMessage}`)
            return false
        }
    }

    $effect(() => {
        if (!sabSupported) {
            log('error', "Critical: SharedArrayBuffer is not supported in this browser or context. Ensure COOP/COEP headers are correctly set on your server.")
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
        return () => {
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
            audioSAB = null;
            controlSAB = null;
            audioBufferView = null;
            controlBufferView = null

        }
    })

    const query = createQuery({
        queryKey: ['chat', page.params.chatId],
        queryFn: async () => await getChat(page.params.chatId),
    })

    $effect(() => {
        if ($query.isSuccess) {
            messages = $query.data.messages
        }
    })

</script>


<div class="flex justify-center">
    <div class="w-6/12 p-4 space-y-4 flex flex-col shadow-md rounded-lg">
        {#each messages as message}
            {#if message.role === 'assistant' }
                <div class="flex justify-start">
                    <div class="max-w-[70%] bg-gray-200 text-gray-800 p-3 rounded-lg shadow">
                        <p class="text-sm">
                            <SvelteMarkdown source={message.content}/>
                        </p>
<!--                        <span class="text-xs text-gray-500 block text-right mt-1">10:00 AM</span>-->
                    </div>
                </div>

            {:else }
                <div class="flex justify-end">
                    <div class="max-w-[70%] bg-blue-500 text-white p-3 rounded-lg shadow">
                        <p class="text-sm">
                            <SvelteMarkdown source={message.content}/>
                        </p>
<!--                        <span class="text-xs text-blue-200 block text-right mt-1">10:02 AM</span>-->
                    </div>
                </div>
            {/if}
        {/each}
        <p>
            <SvelteMarkdown source={agentMessage}/>
        </p>
        <input class="input" bind:value={manualUserMessage} onkeydown={(e) => {
        if (e.keyCode === 13 && !e.shiftKey && webSocket) {
            webSocket.send(JSON.stringify({type: 'text_prompt', prompt: manualUserMessage}))
            manualUserMessage = ""
            e.preventDefault()
        }
    }}>
    </div>

</div>

<style>
</style>
