import {usePlayer} from "../hooks/useAudioPlayer.ts";
import {useEffect} from "react";

export const Test = () => {
    const {queueAudio, audioContext} = usePlayer()

    useEffect(() => {
        const pls = async () => {
            const ids = [
                "bb53793b-2d7b-4160-b299-af403883b18c",
                "c29a66c2-d47b-4f8c-95b1-f1287fe21129",
                "dd1b52a1-4ecb-4852-9343-b9cdb3f9ec92",
                "ddd048ed-e50b-4214-96a5-a662e7d93738",
                // "e856fa24-100e-42f7-b3b0-9be1d459d31e",
                // "eaefc21d-227c-49c4-8779-b7c52725bd7b",
                // "ee1f581a-86d2-4655-a009-85386d7b92f6",
                // "f71fd947-a1f0-446f-b216-71fc0b84ff32",
                // "f8bd03ef-3abb-45c0-a955-a0a0ad82a944",
                // "fd887c1a-14ca-44da-9967-93acd8819883"
            ]
            for (const id of ids) {
                await queueAudio(id)
            }
        }

        if (audioContext) {
            pls()
        }

    }, [audioContext]);

    return (
        <>
        </>
    )
}