import {useChatWebSocket} from "./WebSocketProvider.tsx";
import {SpeechSamplesEvent, WebsocketEventType} from "../types.ts";
import {useEffect, useState} from "react";
import {base64ToArrayBuffer} from "../utils/encoding.ts";

const CTL_WRITE_IDX = 0;
const CTL_READ_IDX = 1;
const CTL_SAMPLES_AVAIL_IDX = 2;
const CTL_WORKLET_WAITING_IDX = 3;
const CONTROL_SAB_SIZE_BYTES = 4 * Int32Array.BYTES_PER_ELEMENT;

const MAX_AUDIO_BUFFER_SAMPLES = 65536 * 4;

export function useWebsocketAudioPlayer() {
    const [workletNode, setWorkletNode] = useState<AudioWorkletNode | null>(null);
    const [samplesArray, setSamplesArray] = useState<Float32Array | null>(null);
    const [controlArray, setControlArray] = useState<Int32Array | null>(null);
    const [workletReady, setWorkletReady] = useState<boolean>(false);

    const {sendMessage: sendJsonMessage, subscribe} = useChatWebSocket()

    useEffect(() => {
        // @ts-expect-error wtf
        const unsubscribe = subscribe(WebsocketEventType.SPEECH_SAMPLES, (message: SpeechSamplesEvent) => {
            if (workletNode === null || controlArray === null || samplesArray === null || !workletReady) return

            const incomingSamples = new Float32Array(base64ToArrayBuffer(message.samples))

            const numIncomingSamples = incomingSamples.length;

            if (numIncomingSamples === 0) return;

            const samplesAvailable = Atomics.load(controlArray, CTL_SAMPLES_AVAIL_IDX);
            if (samplesAvailable + numIncomingSamples > MAX_AUDIO_BUFFER_SAMPLES) {
                console.warn(`[React] SAB buffer full! Dropping ${numIncomingSamples} samples. Available: ${samplesAvailable}`);
                return;
            }

            let writePointer = Atomics.load(controlArray, CTL_WRITE_IDX);
            const spaceToEnd = MAX_AUDIO_BUFFER_SAMPLES - writePointer;

            if (numIncomingSamples <= spaceToEnd) {
                samplesArray.set(incomingSamples, writePointer);
                writePointer += numIncomingSamples;
            } else {
                samplesArray.set(incomingSamples.subarray(0, spaceToEnd), writePointer);
                samplesArray.set(incomingSamples.subarray(spaceToEnd), 0);
                writePointer = numIncomingSamples - spaceToEnd;
            }
            if (writePointer === MAX_AUDIO_BUFFER_SAMPLES) writePointer = 0;

            Atomics.store(controlArray, CTL_WRITE_IDX, writePointer);
            Atomics.add(controlArray, CTL_SAMPLES_AVAIL_IDX, numIncomingSamples); // Atomically add
            }
        )
        return () => unsubscribe()
    }, [subscribe, workletNode, controlArray, samplesArray, workletReady]);

    useEffect(() => {
        const initAudioWorklet = async () => {
            const samplesSAB = new SharedArrayBuffer(MAX_AUDIO_BUFFER_SAMPLES * Float32Array.BYTES_PER_ELEMENT)
            const controlSAB = new SharedArrayBuffer(CONTROL_SAB_SIZE_BYTES)

            const samplesArray = new Float32Array(samplesSAB)
            const controlArray = new Int32Array(controlSAB)

            Atomics.store(controlArray, CTL_WRITE_IDX, 0);
            Atomics.store(controlArray, CTL_READ_IDX, 0);
            Atomics.store(controlArray, CTL_SAMPLES_AVAIL_IDX, 0);
            Atomics.store(controlArray, CTL_WORKLET_WAITING_IDX, 0);

            setSamplesArray(samplesArray)
            setControlArray(controlArray)

            const audioContext = new AudioContext()
            await audioContext.audioWorklet.addModule('/audio-processor.js');

            const node = new AudioWorkletNode(
                audioContext,
                'audio-processor',
                {
                    processorOptions: {
                        audioSAB: samplesSAB,
                        controlSAB: controlSAB
                    }
                }
            )


            node.port.onmessage = (event) => {
                if (event.data?.type === 'control') {
                    // Forward control command to backend
                    sendJsonMessage({
                        type: 'flow_control',
                        command: event.data.command
                    })
                }
                else if (event.data?.type == 'worklet_ready') {
                    setWorkletReady(true)
                }
                else {
                    // Handle other potential messages from worklet if needed
                    console.log('[React] Received message from worklet:', event.data);
                }
            };

            node.connect(audioContext.destination)
            setWorkletNode(node)
        }

        initAudioWorklet()
    }, [sendJsonMessage]);

    return {}
}