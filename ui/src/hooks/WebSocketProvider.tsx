import useWebSocket from "react-use-websocket";
import {WebSocketEvent, WebsocketEventType} from "../types.ts";
import {createContext, ReactNode, useCallback, useContext, useRef} from "react";


type WebSocketContextData = {
    sendMessage: (msg: unknown) => void
    subscribe: (eventType: WebsocketEventType, handler: (event: WebSocketEvent) => void) => () => void
    chatId: string;
}


type HandlerSetMap = {
    [key in WebsocketEventType]?: Set<(msg: WebSocketEvent) => void>
}


const WebSocketContext = createContext(null);

type ProviderProps = {
    children: ReactNode,
    chatId: string
}

export const WebSocketProvider = ({children, chatId}: ProviderProps) => {
    const messageTypeHandlersRef = useRef<HandlerSetMap>({});
    const {
        sendJsonMessage,
    } = useWebSocket(
        `${window.location.protocol == "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws/chat/${chatId}`,
        {
            onMessage: async (event: WebSocketEventMap['message']) => {
                const message = JSON.parse(event.data) as WebSocketEvent

                const handlers = messageTypeHandlersRef.current[message.type];
                if (handlers && handlers.size > 0) {
                    handlers.forEach(handler => {
                        try {
                            handler(message)
                        } catch (e) {
                            console.error(`WebSocket: Error in message handler for type "${message.type}":`, e);
                        }
                    })
                }
            },
            shouldReconnect: () => true,
            reconnectAttempts: 1000,
            reconnectInterval: 2000,
            share: true
        }
    )

    const subscribe = useCallback((messageType: WebsocketEventType, callback: (msg: WebSocketEvent) => void) => {
        if (typeof messageType !== 'string' || !messageType.trim()) {
            console.warn("WebSocket: `messageType` must be a non-empty string.");
            return () => {};
        }
        if (typeof callback !== 'function') {
            console.warn(`WebSocket: Callback for messageType "${messageType}" must be a function.`);
            return () => {};
        }

        if (messageTypeHandlersRef.current[messageType] == undefined) {
            messageTypeHandlersRef.current[messageType] = new Set();
        }
        const handlers = messageTypeHandlersRef.current[messageType];
        handlers!.add(callback);
        console.log(`WebSocket: Handler registered for message type "${messageType}" for provider ${chatId}`);

        return () => {
            const currentHandlers = messageTypeHandlersRef.current[messageType];
            if (currentHandlers) {
                currentHandlers.delete(callback);
                console.log(`WebSocket: Handler unregistered for message type "${messageType}" for provider ${chatId}`);
                if (currentHandlers.size === 0) {
                    delete messageTypeHandlersRef.current[messageType]
                }
            }
        };
    }, [chatId]);

    const contextValue: WebSocketContextData = {
        sendMessage: sendJsonMessage,
        subscribe,
        chatId
    }

    return (
        // @ts-expect-error wtf
        <WebSocketContext.Provider value={contextValue}>
            {children}
        </WebSocketContext.Provider>
    );
}

export const useChatWebSocket = () => {
    const context = useContext(WebSocketContext);

    if (context === null) {
        throw new Error('useWebSocket must be used within a WebSocketProvider. Make sure to wrap your component tree with <WebSocketProvider id="yourId">.');
    }

    return context as WebSocketContextData;
}