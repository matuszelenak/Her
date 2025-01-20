import {axiosDefault} from "../api.ts";
import {useEffect, useState} from "react";


type QueuedAudio = {
    buffer: AudioBuffer,
    audioId: string
}

export const usePlayer = () => {
    const [audioContext, setAudioContext] = useState<AudioContext | null>(null)

    const [queue, setQueue] = useState<QueuedAudio[]>([])
    const [src, setSrc] = useState<AudioBufferSourceNode | null>(null)
    const [playerState, setPlayerState] = useState("inactive")
    const [finishedId, setFinishedId] = useState<string | null>(null)

    useEffect(() => {
        setAudioContext(new AudioContext())
    }, []);

    const addToQueue = (toEnqueue: QueuedAudio) => setQueue((prev) => [...prev, toEnqueue])
    const popFromQueue = () => {
        if (queue.length == 0) return undefined

        const ret = queue[0]
        setQueue((prev) => {
            return prev.toSpliced(0, 1)
        })

        return ret
    }

    const queueAudio = async (audioId: string) => {
        const { data } = await axiosDefault({
            url: `/audio/${audioId}`,
            responseType: "arraybuffer",
            headers: {
                "Content-Type": "audio/wav"
            }
        });

        const arrayBuffer = await audioContext!.decodeAudioData(data)

        addToQueue({
            buffer: arrayBuffer,
            audioId: audioId
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
        if (playerState == "shouldPlay") {
            const toPlay = popFromQueue()
            if (toPlay) {
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
                setQueue([])
                setPlayerState("inactive")
            }
        },
        finishedId
    }
}
