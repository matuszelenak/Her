<script lang="ts">
    import {createQuery} from '@tanstack/svelte-query'
    import {page} from '$app/state';
    import SvelteMarkdown from '@humanspeak/svelte-markdown'

    import type {PageData} from './$types'
    import {getChat} from "$lib/api";
    import {log} from "$lib/log";
    import {type Message, type WebSocketEvent, WebsocketEventType} from "$lib/types";

    let data: PageData
    let webSocket: WebSocket | null = null
    let isConnected = $state(false)
    let messages: Message[] = $state([])
    let manualUserMessage = $state("")
    let agentMessage = $state("")

    function connectWebSocket() {
        const WEBSOCKET_URL = `${window.location.protocol == "https:" ? "wss:" : "ws:"}//localhost:8000/ws/chat/${page.params.chatId}`
        webSocket = new WebSocket(WEBSOCKET_URL)
        webSocket.binaryType = 'arraybuffer';

        webSocket.onopen = () => {
            isConnected = true
        }

        webSocket.onmessage = (event: MessageEvent) => {
            const message = JSON.parse(event.data) as WebSocketEvent

            if (message.type == WebsocketEventType.TOKEN) {
                if (message.token != null) {
                    agentMessage = `${agentMessage}${message.token.message.content}`
                } else {
                    messages = [...messages, {role: 'assistant', content: agentMessage}]
                    agentMessage = ""
                }
            }
            if (message.type == WebsocketEventType.MANUAL_PROMPT) {
                messages = [...messages, {role: 'user', content: message.text}]
            }
        }

        webSocket.onerror = (errEvent) => {
            isConnected = false;
        }

        webSocket.onclose = (event) => {
            isConnected = false
            log('info', `WebSocket disconnected. Code: ${event.code}, Reason: "${event.reason}"`)
        }
    }
    $effect(() => {
        connectWebSocket()

        return () => {
            if (webSocket) {
                webSocket.close()
                webSocket = null
            }
        }
    })

    const query = createQuery({
        queryKey: ['chat', page.params.chatId],
        queryFn: async () => await getChat(page.params.chatId),
    })

    $effect(() => {
        if ($query.isSuccess) {
            messages = $query.data.messages
        }
    })

</script>

<main>
    {#each messages as message}
        <p>
            <SvelteMarkdown source={message.content} />
        </p>
    {/each}
    <p>
        <SvelteMarkdown source={agentMessage} />
    </p>
    <input bind:value={manualUserMessage} onkeydown={(e) => {
        if (e.keyCode === 13 && !e.shiftKey && webSocket) {
            webSocket.send(JSON.stringify({type: 'text_prompt', prompt: manualUserMessage}))
            manualUserMessage = ""
            e.preventDefault()
        }
    }}>
</main>

<style>
    main {
        font-family: Arial, sans-serif;
        padding: 20px;
        max-width: 900px;
        margin: 0 auto;
        background-color: #f4f4f4;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
</style>
