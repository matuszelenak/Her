import {useEffect, useState} from "react";

export const useAudioPlayer = () => {
    const audioContext = new AudioContext();
    const [audioNode, setAudioNode] = useState<AudioWorkletNode | null>(null)

    useEffect(() => {
        const init = async () => {
            await audioContext.audioWorklet.addModule('audioProcessor.js');
            const audioNode = new AudioWorkletNode(audioContext, 'audio-processor');
            audioNode.connect(audioContext.destination);

            setAudioNode(audioNode)
        }

        init()
    }, []);

    return { audioNode, audioContext }
}