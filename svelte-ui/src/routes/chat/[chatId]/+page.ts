import type { PageLoad } from './$types'
import {getChat} from "$lib/api";


export const load: PageLoad = async ({ parent, fetch, params }) => {
    const { queryClient } = await parent()

    const chatId = params.chatId

    await queryClient.prefetchQuery({
        queryKey: ['chat', chatId],
        queryFn: async () => await getChat(chatId),
    })

    return { chatId }
}
