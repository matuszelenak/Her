import {useEffect, useState} from 'react';
import useWebSocket from "react-use-websocket";
import {base64ToArrayBuffer} from "../utils/encoding.ts";

type SamplesEvent = {
    samples: string
}

export const WebSocketAudioPlayer = () => {
    const [workletNode, setWorkletNode] = useState<AudioWorkletNode | null>(null);

    const {sendJsonMessage} = useWebSocket(
        `${window.location.protocol == "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws/audio`,
        {
            onMessage: async (event: WebSocketEventMap['message']) => {
                const message = JSON.parse(event.data) as SamplesEvent

                if (workletNode) {
                    const samples = new Float32Array(base64ToArrayBuffer(message.samples));
                    workletNode.port.postMessage(samples);
                }
            },
            shouldReconnect: () => true,
            reconnectAttempts: 1000,
            reconnectInterval: 2000
        }
    )

    useEffect(() => {
        const initAudioWorklet = async () => {
            const audioContext = new AudioContext()
            await audioContext.audioWorklet.addModule('/audioPlayer.js');

            const node = new AudioWorkletNode(audioContext, 'audio-player')
            node.connect(audioContext.destination)

            node.port.onmessage = (event) => {
                if (event.data?.type === 'control') {
                    // Forward control command to backend
                    sendJsonMessage({
                        command: event.data.command
                    })
                } else {
                    // Handle other potential messages from worklet if needed
                    console.log('[React] Received message from worklet:', event.data);
                }
            };

            setWorkletNode(node)
        }

        initAudioWorklet()
    }, []);

    return (
        <div>
            <h2>WebSocket Audio Player</h2>
            {/* Add any buttons or controls if needed (e.g., manual connect/disconnect) */}
        </div>
    );
};