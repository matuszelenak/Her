export type Token = {
    message: {
        role: 'assistant' | 'user'
        content: string
    }
    done: boolean
}


export type DependencyStatus = {
    stt: 'healthy' | 'unhealthy' | undefined
    tts: 'healthy' | 'unhealthy'| undefined
    llm: string[] | null
}

export enum WebsocketEventType {
    TOKEN = 'token',
    USER_TRANSCRIPTION = 'user_speech_transcription',
    USER_TRANSCRIPTION_INVALIDATION = 'user_speech_transcription_invalidation',
    ASSISTANT_SPEECH_START = 'assistant_speech_start',
    SPEECH_FILE = 'speech_id',
    MANUAL_PROMPT = 'manual_prompt',
}


export interface TokenEvent {
    type: WebsocketEventType.TOKEN
    token: Token | null
}

export interface STTOutputEvent {
    type: WebsocketEventType.USER_TRANSCRIPTION
    segment: {
        words: string[],
        complete: boolean
        id: number
    }
}

export interface STTOutputInvalidationEvent {
    type: WebsocketEventType.USER_TRANSCRIPTION_INVALIDATION
}

export interface SpeechStartEvent {
    type: WebsocketEventType.ASSISTANT_SPEECH_START
}

export interface SpeechFileEvent {
    type: WebsocketEventType.SPEECH_FILE
    uuid: string
    filename: string
    text: string
    order: number
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
    | ManualPromptEvent
