export type ChatConfiguration = {
    ollama: {
        model: string
        ctx_length: number
        temperature: number
        repeat_penalty: number
        system_prompt: string
        tools: string[]
    },
    tts: {
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
    stt: 'healthy' | undefined
    tts: 'healthy' | undefined
    llm: string[] | null
}


export type WebsocketEvent = {
    type: 'token'
    token: Token
} | {
    type: 'stt_output'
    segment: {
        words: string[],
        complete: boolean
        id: number
    }
} | {
    type: 'new_chat'
    chat_id: string
} | {
    type: 'stt_output_invalidation'
} | {
    type: 'config'
    config: ChatConfiguration
} | {
    type: 'speech_id'
    filename: string
} | {
    type: 'manual_prompt'
    text: string
}
