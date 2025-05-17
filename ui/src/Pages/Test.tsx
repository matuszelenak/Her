import {useEffect, useState} from 'react';
import useWebSocket from "react-use-websocket";
import {base64ToArrayBuffer} from "../utils/encoding.ts";

type SamplesEvent = {
    samples: string
}

const CTL_WRITE_IDX = 0;
const CTL_READ_IDX = 1;
const CTL_SAMPLES_AVAIL_IDX = 2;
const CTL_WORKLET_WAITING_IDX = 3;
const CONTROL_SAB_SIZE_BYTES = 4 * Int32Array.BYTES_PER_ELEMENT;

const MAX_AUDIO_BUFFER_SAMPLES = 65536 * 4;


export const WebSocketAudioPlayer = () => {
    const [workletNode, setWorkletNode] = useState<AudioWorkletNode | null>(null);
    const [samplesArray, setSamplesArray] = useState<Float32Array | null>(null);
    const [controlArray, setControlArray] = useState<Int32Array | null>(null);
    const [workletReady, setWorkletReady] = useState<boolean>(false);

    const {sendJsonMessage} = useWebSocket(
        `${window.location.protocol == "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws/audio`,
        {
            onMessage: async (event: WebSocketEventMap['message']) => {
                if (workletNode === null || controlArray === null || samplesArray === null) return

                const message = JSON.parse(event.data) as SamplesEvent
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
            },
            shouldReconnect: () => true,
            reconnectAttempts: 1000,
            reconnectInterval: 2000,
        },
        workletReady
    )

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

    return (
        <div>
            <h2>WebSocket Audio Player</h2>
        </div>
    );
};