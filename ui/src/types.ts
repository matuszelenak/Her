export type Configuration = {
    ollama: {
        model: string
        ctx_length: number
        temperature: number
        repeat_penalty: number
        system_prompt: string
    },
    xtts: {
        voice: string
        language: 'en'
    },
    app: {
        prevalidate_prompt: boolean
        speech_submit_delay_ms: number
    }
}


export type OllamaModel = {
    model: string
    name: string
    size: number
}


export type Token = {
    message: {
        role: 'assistant' | 'user'
        content: string
    }
    done: boolean
    prompt_eval_count?: number
    prompt_eval_duration?: number
    eval_count?: number
    eval_duration?: number
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
}
