import {Dispatch, SetStateAction, useEffect, useState} from "react";

export function useDelayedInput<S>(initialValue: S, delayMs: number): [S, Dispatch<SetStateAction<S>>, S] {
    const [realValue, setRealValue] = useState<S>(initialValue)
    const [delayedValue, setDelayedValue] = useState<S>(initialValue)

    useEffect(() => {
        const delayDebounceFn = setTimeout(() => {
            setDelayedValue(realValue)
        }, delayMs)

        return () => clearTimeout(delayDebounceFn)
    }, [realValue, delayMs])

    return [delayedValue, setRealValue, realValue]
}