import {useParams} from "react-router-dom";
import {CircularProgress} from "@mui/material";
import {Chat} from "../Pages/Chat.tsx";

export const ChatProvider = () => {
    const { chatId } = useParams<string>();

    if (!chatId) {
        return <CircularProgress/>;
    }

    return <Chat chatId={chatId}/>
}
