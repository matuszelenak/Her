import { axiosDefault } from "../api.ts";
import { useEffect, useState } from "react";
import { SpeechFileEvent } from "../types.ts";


type QueuedAudio = {
    buffer: AudioBuffer,
    audioId: string
    order: number
}

export const usePlayer = () => {
    const [audioContext, setAudioContext] = useState<AudioContext | null>(null)

    const [queue, setQueue] = useState<QueuedAudio[]>([])
    const [src, setSrc] = useState<AudioBufferSourceNode | null>(null)
    const [playerState, setPlayerState] = useState("inactive")
    const [finishedId, setFinishedId] = useState<string | null>(null)
    const [lastPlayedOrderId, setLastPlayedOrderId] = useState(-1)

    useEffect(() => {
        setAudioContext(new AudioContext())
    }, []);

    const addToQueue = (toEnqueue: QueuedAudio) =>
        setQueue((prev) => {

            const newQueue = []
            let inserted = false

            if (prev.length == 0) return [toEnqueue]

            for (const el of prev) {
                if (!inserted && toEnqueue.order < el.order) {
                    newQueue.push(toEnqueue)
                    inserted = true
                }
                newQueue.push(el)
            }
            if (!inserted) {
                newQueue.push(toEnqueue)
            }
            return newQueue
        })
    const popFromQueue = () => {
        if (queue.length == 0) return undefined

        if (queue[0].order > lastPlayedOrderId + 1) return null

        const ret = queue[0]
        setQueue((prev) => {
            return prev.toSpliced(0, 1)
        })

        return ret
    }

    const queueAudio = async (message: SpeechFileEvent) => {
        const {data} = await axiosDefault({
            url: `/audio/${message.filename}`,
            responseType: "arraybuffer",
            headers: {
                "Content-Type": "audio/wav"
            }
        });

        console.log(`Fetched audio order ${message.order} ${message.text}`)

        const arrayBuffer = await audioContext!.decodeAudioData(data)

        addToQueue({
            buffer: arrayBuffer,
            audioId: message.filename,
            order: message.order
        })
        setPlayerState((prev) => {
            if (prev == "inactive") {
                return "shouldPlay"
            } else {
                return prev
            }
        })
    }

    useEffect(() => {
        console.log(playerState)
        console.log(queue)
        if (playerState == "shouldPlay") {
            const toPlay = popFromQueue()
            if (toPlay) {
                console.log(`Playing ${toPlay.order}`)
                setLastPlayedOrderId(toPlay.order)
                setPlayerState(() => {
                    playAudio(toPlay)
                    return "playing"
                })
            } else {
                setPlayerState("inactive")
            }
        }
    }, [playerState]);

    const playAudio = async (queuedAudio: QueuedAudio) => {
        const source = audioContext!.createBufferSource()
        setSrc(source)
        source.buffer = queuedAudio.buffer
        source.connect(audioContext!.destination)
        source.onended = async () => {
            setFinishedId(queuedAudio.audioId)
            setPlayerState("shouldPlay")
        };
        source.start()
    }

    return {
        queueAudio,
        audioContext,
        stop: () => {
            if (src) {
                src.stop()
                setLastPlayedOrderId(-1)
                setQueue([])
                setPlayerState("inactive")
            }
        },
        finishedId
    }
}
