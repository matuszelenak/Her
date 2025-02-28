export type ChatConfiguration = {
    llm: {
        model: string
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


export type LLMModel = {
    id: string
    created: number
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

export enum WebsocketEventType {
    TOKEN = 'token',
    STT_OUTPUT = 'stt_output',
    STT_OUTPUT_INVALIDATION = 'stt_output_invalidation',
    SPEECH_START = 'speech_start',
    SPEECH_FILE = 'speech_id',
    MANUAL_PROMPT = 'manual_prompt',
    CONFIG = 'config',
    NEW_CHAT = 'new_chat'
}


export interface TokenEvent {
    type: WebsocketEventType.TOKEN
    token: Token
}

export interface STTOutputEvent {
    type: WebsocketEventType.STT_OUTPUT
    segment: {
        words: string[],
        complete: boolean
        id: number
    }
}

export interface STTOutputInvalidationEvent {
    type: WebsocketEventType.STT_OUTPUT_INVALIDATION
}

export interface SpeechStartEvent {
    type: WebsocketEventType.SPEECH_START
}

export interface SpeechFileEvent {
    type: WebsocketEventType.SPEECH_FILE
    uuid: string
    filename: string
    text: string
    order: number
}

export interface NewChatEvent {
    type: WebsocketEventType.NEW_CHAT
    chat_id: string
}

export interface ConfigEvent {
    type: WebsocketEventType.CONFIG
    config: ChatConfiguration
}

export interface ManualPromptEvent {
    type: WebsocketEventType.MANUAL_PROMPT
    text: string
}

export type WebSocketEvent =
    TokenEvent
    | STTOutputEvent
    | STTOutputInvalidationEvent
    | SpeechFileEvent
    | SpeechStartEvent
    | NewChatEvent
    | ConfigEvent
    | ManualPromptEvent
