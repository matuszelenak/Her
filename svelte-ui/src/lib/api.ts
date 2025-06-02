import axios from "axios";
import type {Chat, ChatsResponse} from "$lib/types";

export const axiosDefault = axios.create({
    baseURL: `http://192.168.100.5:8000/api`,
    headers: {
        'Content-Type': 'application/json'
    },
})

export const getChat = async (chatId: string) => {
    const res = await fetch(`http://192.168.1.91:8000/chat/${chatId}`)
    const json = await res.json()
    console.log(json)
    return json as Chat
}