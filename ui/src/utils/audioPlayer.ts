import {useEffect, useState} from "react";

const getCursorDistance = (consumer: number, producer: number, totalLength: number) => {
    if (consumer <= producer) {
        return totalLength - (producer - consumer)
    } else {
        return consumer - producer
    }
}

export const useAudioPlayer = (audioContext: AudioContext) => {
    const [audioNode, setAudioNode] = useState<AudioWorkletNode | null>(null)

    const [buffer, setBuffer] = useState<Float32Array | null>(null)
    const [consumerCursor, setConsumerCursor] = useState(0)
    const [producerCursor, setProducerCursor] = useState(0)


    const feeder = (samples: Float32Array) => {
        if (buffer === null || audioNode === null) {
            return false
        }

        const freeSpace = getCursorDistance(consumerCursor, producerCursor, buffer.length)

        if (freeSpace < 32768) {
            return false
        }

        buffer.set(samples, producerCursor)

        const newCursor = (producerCursor + samples.length) % buffer.length

        audioNode.port.postMessage(newCursor)

        setProducerCursor(newCursor)

        return true
    }

    useEffect(() => {
        const init = async () => {
            await audioContext.audioWorklet.addModule('/ringBufferPlayer.js');
            const audioNode = new AudioWorkletNode(audioContext, 'playback-processor');

            setAudioNode(audioNode)
            audioNode.port.onmessage = (e: MessageEvent) => {
                if (e.data.eventType === 'buffer') {
                    console.log('Buffer set')
                    const b = new Float32Array(e.data.buffer)
                    setBuffer(b)
                    console.log('Free space', b.length)
                } else {
                    setConsumerCursor(e.data)
                }
            }

            audioNode.connect(audioContext.destination);
        }

        init()
    }, []);

    const freeSpace = getCursorDistance(consumerCursor, producerCursor, buffer?.length || 262144)
    return { feeder, consumerCursor, producerCursor, freeSpace }
}
