import {useEffect} from 'react'
import reactLogo from './assets/react.svg'
import './App.css'
import useWebSocket from "react-use-websocket";
import {useAudioPlayer} from "./utils/audioPlayer.ts";

function generateUUID() {
    let dt = new Date().getTime();
    const uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        const r = (dt + Math.random() * 16) % 16 | 0;
        dt = Math.floor(dt / 16);
        return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
    return uuid;
}

// @ts-ignore
function resampleTo16kHZ(audioData, origSampleRate = 44100) {
    // Convert the audio data to a Float32Array
    const data = new Float32Array(audioData);

    // Calculate the desired length of the resampled data
    const targetLength = Math.round(data.length * (16000 / origSampleRate));

    // Create a new Float32Array for the resampled data
    const resampledData = new Float32Array(targetLength);

    // Calculate the spring factor and initialize the first and last values
    const springFactor = (data.length - 1) / (targetLength - 1);
    resampledData[0] = data[0];
    resampledData[targetLength - 1] = data[data.length - 1];

    // Resample the audio data
    for (let i = 1; i < targetLength - 1; i++) {
        const index = i * springFactor;
        const leftIndex = Math.floor(index).toFixed();
        const rightIndex = Math.ceil(index).toFixed();
        // @ts-ignore
        const fraction = index - leftIndex;
        // @ts-ignore
        resampledData[i] = data[leftIndex] + (data[rightIndex] - data[leftIndex]) * fraction;
    }

    return resampledData;
}


function App() {
    const { audioNode, audioContext } = useAudioPlayer()

    const {
        readyState,
        sendMessage
    } = useWebSocket(
        `ws://localhost:8000/ws/41ae3e52-dd7d-4fd6-92a1-88638e8ceaa1`,
        {
            onMessage: (event: WebSocketEventMap['message']) => {
                const message = JSON.parse(event.data)

                if (message.type == 'speech') {
                    const int16Array = message.samples
                    let float32Array = new Float32Array(int16Array.length * 2);
                    for (let i = 0; i < int16Array.length; i++) {
                        float32Array[i * 2] = int16Array[i] / 32768.;
                        float32Array[i * 2 + 1] = int16Array[i] / 32768.;
                    }
                    audioNode?.port?.postMessage({message: 'audioData', audioData: float32Array});
                }
            },
            reconnectAttempts: 1000,
            reconnectInterval: 2000
        }
    );

    useEffect(() => {
        console.log('Initializing')

        async function initContext() {
            navigator.mediaDevices.getUserMedia({audio: true})
                .then(function (stream) {
                    // Create a new MediaRecorder instance
                    const audioDataCache = [];
                    const mediaStream = audioContext.createMediaStreamSource(stream);
                    const recorder = audioContext.createScriptProcessor(4096, 1, 1);

                    recorder.onaudioprocess = async (event) => {
                        const inputData = event.inputBuffer.getChannelData(0);
                        const audioData16kHz = resampleTo16kHZ(inputData, audioContext.sampleRate);

                        audioDataCache.push(inputData);

                        sendMessage(audioData16kHz);
                    };

                    // Prevent page mute
                    mediaStream.connect(recorder);
                    recorder.connect(audioContext.destination);
                })
        }

        initContext()
    }, [readyState])

    return (
        <>
            <div>
                <a href="https://react.dev" target="_blank">
                    <img src={reactLogo} className="logo react" alt="React logo"/>
                </a>
            </div>
        </>
    )
}

export default App
