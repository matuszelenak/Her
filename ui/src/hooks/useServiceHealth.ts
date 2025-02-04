import useWebSocket from "react-use-websocket";
import { DependencyStatus } from "../types.ts";
import { useEffect, useState } from "react";

export const useServiceHealth = () => {
    const [status, setStatus] = useState<DependencyStatus>({
        tts: undefined,
        stt: undefined,
        llm: []
    })

    const {sendJsonMessage} = useWebSocket(
        `${window.location.protocol == "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws/health`,
        {
            onMessage: (event: WebSocketEventMap['message']) => {
                const message = JSON.parse(event.data) as DependencyStatus
                setStatus(message)
            },
            reconnectAttempts: 1000,
            reconnectInterval: 2000,
            share: true
        }
    );

    useEffect(() => {
        sendJsonMessage({})

        const interval = setInterval(() => {
            sendJsonMessage({})
        }, 5000);

        return () => clearInterval(interval);
    }, []);

    return status
}
