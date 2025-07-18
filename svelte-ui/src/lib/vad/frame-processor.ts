import type {SpeechProbabilities} from "./models"
import { Message } from "./messages"
import { log } from "./logging"

const RECOMMENDED_FRAME_SAMPLES = [512, 1024, 1536]

export interface FrameProcessorOptions {
    /** Threshold over which values returned by the Silero VAD model will be considered as positively indicating speech.
     * The Silero VAD model is run on each frame. This number should be between 0 and 1.
     */
    positiveSpeechThreshold: number

    /** Threshold under which values returned by the Silero VAD model will be considered as indicating an absence of speech.
     * Note that the creators of the Silero VAD have historically set this number at 0.15 less than `positiveSpeechThreshold`.
     */
    negativeSpeechThreshold: number

    /** After a VAD value under the `negativeSpeechThreshold` is observed, the algorithm will wait `redemptionFrames` frames
     * before running `onSpeechEnd`. If the model returns a value over `positiveSpeechThreshold` during this grace period, then
     * the algorithm will consider the previously-detected "speech end" as having been a false negative.
     */
    redemptionFrames: number

    /** Number of audio samples (under a sample rate of 16000) to comprise one "frame" to feed to the Silero VAD model.
     * The `frame` serves as a unit of measurement of lengths of audio segments and many other parameters are defined in terms of
     * frames. The authors of the Silero VAD model offer the following warning:
     * > WARNING! Silero VAD models were trained using 512, 1024, 1536 samples for 16000 sample rate and 256, 512, 768 samples for 8000 sample rate.
     * > Values other than these may affect model perfomance!!
     * In this context, audio fed to the VAD model always has sample rate 16000. It is probably a good idea to leave this at 1536.
     */
    frameSamples: number

    /** Number of frames to prepend to the audio segment that will be passed to `onSpeechEnd`. */
    preSpeechPadFrames: number

    /** If an audio segment is detected as a speech segment according to initial algorithm but it has fewer than `minSpeechFrames`,
     * it will be discarded and `onVADMisfire` will be run instead of `onSpeechEnd`.
     */
    minSpeechFrames: number

    /**
     * If true, when the user pauses the VAD, it may trigger `onSpeechEnd`.
     */
    submitUserSpeechOnPause: boolean
}

export const defaultLegacyFrameProcessorOptions: FrameProcessorOptions = {
    positiveSpeechThreshold: 0.5,
    negativeSpeechThreshold: 0.5 - 0.15,
    preSpeechPadFrames: 1,
    redemptionFrames: 8,
    frameSamples: 1536,
    minSpeechFrames: 3,
    submitUserSpeechOnPause: false,
}

export const defaultV5FrameProcessorOptions: FrameProcessorOptions = {
    positiveSpeechThreshold: 0.5,
    negativeSpeechThreshold: 0.5 - 0.15,
    preSpeechPadFrames: 3,
    redemptionFrames: 24,
    frameSamples: 512,
    minSpeechFrames: 9,
    submitUserSpeechOnPause: false,
}

export function validateOptions(options: FrameProcessorOptions) {
    if (!RECOMMENDED_FRAME_SAMPLES.includes(options.frameSamples)) {
        log.warn("You are using an unusual frame size")
    }
    if (
        options.positiveSpeechThreshold < 0 ||
        options.negativeSpeechThreshold > 1
    ) {
        log.error("postiveSpeechThreshold should be a number between 0 and 1")
    }
    if (
        options.negativeSpeechThreshold < 0 ||
        options.negativeSpeechThreshold > options.positiveSpeechThreshold
    ) {
        log.error(
            "negativeSpeechThreshold should be between 0 and postiveSpeechThreshold"
        )
    }
    if (options.preSpeechPadFrames < 0) {
        log.error("preSpeechPadFrames should be positive")
    }
    if (options.redemptionFrames < 0) {
        log.error("preSpeechPadFrames should be positive")
    }
}

export interface FrameProcessorInterface {
    resume: () => void
    process: (
        arr: Float32Array,
        handleEvent: (event: FrameProcessorEvent) => void
    ) => Promise<void>
    endSegment: (handleEvent: (event: FrameProcessorEvent) => void) => { msg?: Message; audio?: Float32Array }
}

const concatArrays = (arrays: Float32Array[]): Float32Array => {
    const sizes = arrays.reduce(
        (out, next) => {
            out.push((out.at(-1) as number) + next.length)
            return out
        },
        [0]
    )
    const outArray = new Float32Array(sizes.at(-1) as number)
    arrays.forEach((arr, index) => {
        const place = sizes[index]
        outArray.set(arr, place)
    })
    return outArray
}

export type FrameProcessorEvent =
    | {
    msg: Message.VADMisfire
}
    | {
    msg: Message.SpeechStart
}
    | {
    msg: Message.SpeechRealStart
}
    | {
    msg: Message.SpeechEnd
    audio: Float32Array
}
    | {
    msg: Message.SpeechContinue
    probs: SpeechProbabilities
    audio: Float32Array
}

export class FrameProcessor implements FrameProcessorInterface {
    speaking: boolean = false
    initialSpeechBuffer: { frame: Float32Array; isSpeech: boolean }[]
    preSpeechBuffer: Float32Array[]
    redemptionCounter = 0
    active = false

    constructor(
        public modelProcessFunc: (
            frame: Float32Array
        ) => Promise<SpeechProbabilities>,
        public modelResetFunc: () => void,
        public options: FrameProcessorOptions
    ) {
        this.initialSpeechBuffer = []
        this.preSpeechBuffer = []
        this.reset()
    }

    reset = () => {
        this.speaking = false
        this.initialSpeechBuffer = []
        this.preSpeechBuffer = []
        this.modelResetFunc()
        this.redemptionCounter = 0
    }

    pause = () => {
        this.active = false
        this.reset()
        return {}
    }

    resume = () => {
        this.active = true
    }

    endSegment = (handleEvent: (event: FrameProcessorEvent) => void) => {
        const audioBuffer = this.initialSpeechBuffer
        this.initialSpeechBuffer = []
        const speaking = this.speaking
        this.reset()

        const speechFrameCount = audioBuffer.reduce((acc, item) => {
            return item.isSpeech ? (acc + 1) : acc
        }, 0)

        if (speaking) {
            if (speechFrameCount >= this.options.minSpeechFrames) {
                const audio = concatArrays(audioBuffer.map((item) => item.frame))
                handleEvent({ msg: Message.SpeechEnd, audio })
            } else {
                handleEvent({ msg: Message.VADMisfire })
            }
        }
        return {}
    }

    process = async (
        frame: Float32Array,
        handleEvent: (event: FrameProcessorEvent) => void
    ) => {
        if (!this.active) {
            return
        }

        const probs = await this.modelProcessFunc(frame)

        if (
            probs.isSpeech >= this.options.positiveSpeechThreshold &&
            this.redemptionCounter
        ) {
            this.redemptionCounter = 0
        }

        if (
            probs.isSpeech >= this.options.positiveSpeechThreshold &&
            !this.speaking
        ) {
            this.speaking = true

            console.log('Potentially starting speech')
        }

        let speechEnded = false
        if (
            probs.isSpeech < this.options.negativeSpeechThreshold &&
            this.speaking &&
            ++this.redemptionCounter >= this.options.redemptionFrames
        ) {
            this.redemptionCounter = 0
            this.speaking = false

            this.initialSpeechBuffer = []

            console.log('Ending speech')
            speechEnded = true
        }
        if (this.speaking) {
            const speechFrameCount = this.initialSpeechBuffer.reduce((acc, item) => {
                return acc + +item.isSpeech
            }, 0)

            if (speechFrameCount <= this.options.minSpeechFrames) {
                console.log('Adding to initial speech buffer')
                this.initialSpeechBuffer.push({
                    frame,
                    isSpeech: probs.isSpeech >= this.options.positiveSpeechThreshold,
                })
                if (speechFrameCount === this.options.minSpeechFrames) {
                    const audioBuffer = this.initialSpeechBuffer

                    console.log('We hit a threshold')
                    handleEvent({
                        probs,
                        msg: Message.SpeechContinue,
                        audio: concatArrays([
                            concatArrays(this.preSpeechBuffer),
                            concatArrays(audioBuffer.map((item) => item.frame))
                        ])
                    })
                }
            }
            else if (speechFrameCount > this.options.minSpeechFrames) {
                console.log('Continuing speech')
                handleEvent({
                    probs,
                    msg: Message.SpeechContinue,
                    audio: frame
                })
            }
        } else {
            this.preSpeechBuffer.push(frame)

            while (this.preSpeechBuffer.length > this.options.preSpeechPadFrames) {
                this.preSpeechBuffer.shift()
            }
        }
        if (speechEnded) {
            handleEvent({ msg: Message.SpeechEnd, audio: frame})
        }
        return
    }
}
