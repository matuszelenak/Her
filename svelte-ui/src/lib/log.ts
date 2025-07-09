
export function log(level: string, message: string) {
    if (level === 'error') console.error(`[SveltePlayer] ${message}`)
    else console.log(`[SveltePlayer] ${message}`)
}