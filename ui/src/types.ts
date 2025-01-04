export type ChatConfiguration = {
    ollama: {
        model: string
        ctx_length: number
        temperature: number
        repeat_penalty: number
        system_prompt: string
        tools: string[]
    },
    xtts: {
        voice: string
        language: 'en' | 'cs'
    },
    whisper: {
        language: 'en' | 'cs'
        model: string
    }
    app: {
        prevalidate_prompt: boolean
    }
}


export type OllamaModel = {
    model: string
    size: number
}


export type Token = {
    message: {
        role: 'assistant' | 'user'
        content: string
    }
    done: boolean
}


export type DependencyStatus = {
    whisper: boolean
    xtts: boolean
    ollama: string[] | null
}


export type WebsocketEvent = {
    type: 'token'
    token: Token
} | {
    type: 'stt_output'
    text: string
} | {
    type: 'speech'
    samples: string
} | {
    type: 'new_chat'
    chat_id: string
} | {
    type: 'stt_output_invalidation'
} | {
    type: 'config'
    config: ChatConfiguration
}
