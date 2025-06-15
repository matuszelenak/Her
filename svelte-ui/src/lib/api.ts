import type {Chat} from "$lib/types";


export const getChat = async (chatId: string) => {
    const res = await fetch(`/api/chat/${chatId}`)
    const json = await res.json()
    return json as Chat
}