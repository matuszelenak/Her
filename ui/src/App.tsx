import reactLogo from './assets/react.svg'
import './App.css'
import useWebSocket from "react-use-websocket";
import {useAudioPlayer} from "./utils/audioPlayer.ts";
import {useAudioRecorder} from "./utils/audioRecorder.ts";


function App() {
    const audioContext = new AudioContext();
    const { audioNode } = useAudioPlayer(audioContext)

    const {
        sendMessage,
    } = useWebSocket(
        `ws://localhost:8000/ws/41ae3e52-dd7d-4fd6-92a1-88638e8ceaa1`,
        {
            onMessage: (event: WebSocketEventMap['message']) => {
                const message = JSON.parse(event.data)

                if (message.type == 'speech') {
                    audioNode?.port?.postMessage({message: 'audioData', audioData: new Float32Array(message.samples)});
                }
            },
            reconnectAttempts: 1000,
            reconnectInterval: 2000
        }
    );

    useAudioRecorder((buffer: ArrayBuffer) => {
        sendMessage(buffer)
    })

    return (
        <>
            <div>
                <button>Please</button>
                <a href="https://react.dev" target="_blank">
                    <img src={reactLogo} className="logo react" alt="React logo"/>

                </a>
            </div>
        </>
    )
}

export default App
