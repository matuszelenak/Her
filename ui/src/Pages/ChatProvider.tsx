import {Navigate, useParams} from "react-router-dom";
import {WebSocketProvider} from "../hooks/WebSocketProvider.tsx";
import {Chat} from "./Chat.tsx";

export const ChatProvider = () => {
    const {chatId} = useParams<string>();

    if (!chatId) {
        return <Navigate to={'/chat'}/>;
    }

    return (
        <WebSocketProvider chatId={chatId}>
            <Chat chatId={chatId}/>
        </WebSocketProvider>
    )
}