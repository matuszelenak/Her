import {useEffect} from "react";


export const useAudioRecorder = (callback: (a: Float32Array) => any) => {
    useEffect(() => {
        const init = async () => {
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(async function (stream) {
                    const audioContext = new AudioContext()
                    await audioContext.audioWorklet.addModule('/audioRecorder.js');
                    let src = audioContext.createMediaStreamSource(stream);

                    const processor = new AudioWorkletNode(audioContext, 'record-processor');

                    processor.port.onmessage = (e) => {
                        if (e.data.eventType === 'data') {
                            callback(e.data.audioBuffer)
                        }
                    }
                    src.connect(processor);
                })
                .catch(function (err) {
                    console.log('The following error occurred: ' + err);
                });
        }

        init()
    }, []);
}
