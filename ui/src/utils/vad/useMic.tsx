import React, {useEffect, useState} from "react"
import {DEFAULT_MODEL, getDefaultRealTimeVADOptions, MicVAD, RealTimeVADOptions} from "./real-time-vad.ts";
import {SpeechProbabilities} from "./models";


interface ReactOptions {
    startOnLoad: boolean
    userSpeakingThreshold: number
}

export type ReactRealTimeVADOptions = RealTimeVADOptions & ReactOptions

const defaultReactOptions: ReactOptions = {
    startOnLoad: true,
    userSpeakingThreshold: 0.6,
}

export const getDefaultReactRealTimeVADOptions = (
    model: "legacy" | "v5"
): ReactRealTimeVADOptions => {
    return {
        ...getDefaultRealTimeVADOptions(model),
        ...defaultReactOptions,
    }
}

const reactOptionKeys = Object.keys(defaultReactOptions)
const vadOptionKeys = Object.keys(getDefaultRealTimeVADOptions("v5"))

const _filter = (keys: string[], obj: any) => {
    return keys.reduce((acc, key) => {
        acc[key] = obj[key]
        return acc
    }, {} as { [key: string]: any })
}

function useOptions(
    options: Partial<ReactRealTimeVADOptions>
): [ReactOptions, RealTimeVADOptions] {
    const model = options.model ?? DEFAULT_MODEL
    options = { ...getDefaultReactRealTimeVADOptions(model), ...options }
    const reactOptions = _filter(reactOptionKeys, options) as ReactOptions
    const vadOptions = _filter(vadOptionKeys, options) as RealTimeVADOptions
    return [reactOptions, vadOptions]
}

function useEventCallback<T extends (...args: unknown[]) => unknown>(fn: T): T {
    const ref = React.useRef(fn)

    // we copy a ref to the callback scoped to the current state/props on each render
    useIsomorphicLayoutEffect(() => {
        ref.current = fn
    })

    return React.useCallback(
        (...args: unknown[]) => ref.current.apply(void 0, args),
        []
    ) as T
}

export function useMicVAD(options: Partial<ReactRealTimeVADOptions>) {
    const [reactOptions, vadOptions] = useOptions(options)
    const [userSpeaking, updateUserSpeaking] = useState(false)
    const [loading, setLoading] = useState(true)
    const [errored, setErrored] = useState<false | { message: string }>(false)
    const [listening, setListening] = useState(false)
    const [vad, setVAD] = useState<MicVAD | null>(null)

    // @ts-expect-error wtf
    const userOnFrameProcessed = useEventCallback(vadOptions.onFrameProcessed)
    // @ts-expect-error wtf
    vadOptions.onFrameProcessed = useEventCallback((probs: SpeechProbabilities, frame) => {
        const isSpeaking = probs.isSpeech > reactOptions.userSpeakingThreshold
        updateUserSpeaking(isSpeaking)
        userOnFrameProcessed(probs, frame)
    })
    const { onSpeechFrames, onSpeechEnd } = vadOptions
    // @ts-expect-error wtf
    const _onSpeechFrames = useEventCallback(onSpeechFrames)
    // @ts-expect-error wtf
    const _onSpeechEnd = useEventCallback(onSpeechEnd)
    vadOptions.onSpeechFrames = _onSpeechFrames
    vadOptions.onSpeechEnd = _onSpeechEnd

    useEffect(() => {
        let myvad: MicVAD | null
        let canceled = false
        const setup = async (): Promise<void> => {
            try {
                myvad = await MicVAD.new(vadOptions)
                if (canceled) {
                    myvad.destroy()
                    return
                }
            } catch (e) {
                setLoading(false)
                if (e instanceof Error) {
                    setErrored({ message: e.message })
                } else {
                    // @ts-expect-error wtf
                    setErrored({ message: e })
                }
                return
            }
            setVAD(myvad)
            setLoading(false)
            if (reactOptions.startOnLoad) {
                myvad?.start()
                setListening(true)
            }
        }
        setup().catch(() => {
            console.log("Well that didn't work")
        })
        return function cleanUp() {
            myvad?.destroy()
            canceled = true
            if (!loading && !errored) {
                setListening(false)
            }
        }
    }, [])
    const pause = () => {
        if (!loading && !errored) {
            vad?.pause()
            setListening(false)
        }
    }
    const start = () => {
        if (!loading && !errored) {
            vad?.start()
            setListening(true)
        }
    }
    const toggle = () => {
        if (listening) {
            pause()
        } else {
            start()
        }
    }
    return {
        listening,
        errored,
        loading,
        userSpeaking,
        pause,
        start,
        toggle,
    }
}

const useIsomorphicLayoutEffect =
    typeof window !== "undefined" &&
    typeof window.document !== "undefined" &&
    typeof window.document.createElement !== "undefined"
        ? React.useLayoutEffect
        : React.useEffect
