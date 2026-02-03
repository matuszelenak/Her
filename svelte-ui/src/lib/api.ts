import type {Chat} from "$lib/types";


export const getChat = async (chatId: string) => {
    try {
        const res = await fetch(`/api/chat/${chatId}`)
        const json = await res.json()
        return json as Chat
    } catch (e) {
        return null
    }
}