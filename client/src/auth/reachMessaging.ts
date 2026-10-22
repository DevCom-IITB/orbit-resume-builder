// Messaging with the REACH parent window that embeds Orbit in an iframe.
//
// Tokens must only be accepted from, and requests only sent to, the real REACH
// origin: any site could otherwise frame Orbit and inject its own token or
// read ours.

const configuredOrigin = import.meta.env.VITE_REACH_ORIGIN as string | undefined

// Fall back to the usual local REACH dev server only in development builds.
export const REACH_ORIGIN: string | null =
    configuredOrigin || (import.meta.env.DEV ? 'http://localhost:3000' : null)

if (!REACH_ORIGIN) {
    console.error(
        '[auth] VITE_REACH_ORIGIN is not set; messages from the parent window will be ignored.'
    )
}

/** True only for messages sent by the REACH window that embeds us. */
export function isFromReach(ev: MessageEvent): boolean {
    return (
        REACH_ORIGIN !== null &&
        ev.origin === REACH_ORIGIN &&
        ev.source === window.parent
    )
}

/** Post a message to the REACH parent window, and to nobody else. */
export function postToReach(message: unknown): void {
    if (REACH_ORIGIN === null || window.parent === window) return
    window.parent.postMessage(message, REACH_ORIGIN)
}
