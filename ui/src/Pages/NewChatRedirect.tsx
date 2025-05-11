import {Navigate} from "react-router-dom";
import {axiosDefault} from "../api.ts";
import {useQuery} from "@tanstack/react-query";
import {CircularProgress} from "@mui/material";

export const NewChatRedirect = () => {
    const {data: chatId} = useQuery({
        queryKey: ['newChat'],
        queryFn: async () => axiosDefault({
            url: `/chat/new`,
            method: 'post'
        }).then(({data}: { data: string }) => data)
    })

    if (!chatId) return <CircularProgress />;

    return <Navigate to={`chat/${chatId}`}/>
}
