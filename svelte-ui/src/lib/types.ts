export type Token = {
    message: {
        role: 'assistant' | 'user'
        content: string
    }
    done: boolean
}


export type DependencyStatus = {
    [key: string]: 'healthy' | 'unhealthy' | undefined
}

export enum WebsocketEventType {
    TOKEN = 'token',
    USER_TRANSCRIPTION = 'user_speech_transcription',
    USER_TRANSCRIPTION_INVALIDATION = 'user_speech_transcription_invalidation',
    ASSISTANT_SPEECH_START = 'assistant_speech_start',
    SPEECH_FILE = 'speech_id',
    MANUAL_PROMPT = 'manual_prompt',
    CONFIGURATION = 'configuration',
    SPEECH_SAMPLES = 'speech_samples'
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

export interface ReceivedConfigEvent {
    type: WebsocketEventType.CONFIGURATION
    configuration: Configuration
}

export interface SpeechSamplesEvent {
    type: WebsocketEventType.SPEECH_SAMPLES
    samples: string
}

export type WebSocketEvent =
    TokenEvent
    | STTOutputEvent
    | STTOutputInvalidationEvent
    | SpeechFileEvent
    | SpeechStartEvent
    | ManualPromptEvent
    | ReceivedConfigEvent
    | SpeechSamplesEvent


export type STTConfiguration = {
    provider: 'whisper'
    model: 'medium.en'
}


export type KokoroConfiguration = {
    provider: 'kokoro'
    voice: 'bf_emma' | 'bf_isabella'
}


export type OrpheusConfiguration = {
    provider: 'orpheus'
    voice: 'tara'
}


export type Configuration = {
    stt: STTConfiguration
    tts: KokoroConfiguration | OrpheusConfiguration
    app: {
        prevalidate_prompt: boolean
        inactivity_timeout_ms: number
        voice_input_enabled: boolean
        voice_output_enabled: boolean
        after_user_speech_confirmation_delay_ms: number
    }
}
export type Message = {
    role: 'user' | 'assistant'
    content: string
}


export type ChatsResponse = {
    id: string
    header: string
}[]

export type Chat = {
    id: string
    messages: Message[]
}

export type LiveTranscribedText = {
    stableWords: string[],
    undeterminedWords: string[]
}