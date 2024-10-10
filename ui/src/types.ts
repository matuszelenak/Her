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
