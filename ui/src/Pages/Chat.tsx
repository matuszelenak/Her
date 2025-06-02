import Grid from "@mui/material/Grid2";
import {useEffect, useState} from "react";
import {arrayBufferToBase64} from "../utils/encoding.ts";
import {useMicVAD} from "../utils/vad/useMic.tsx";
import {Configuration, Message, ReceivedConfigEvent, WebsocketEventType} from "../types.ts";
import {ChatList} from "../Components/ChatList.tsx";
import {useQuery} from "@tanstack/react-query";
import {axiosDefault} from "../api.ts";
import {ConfigurationToolbar} from "../Components/ConfigurationToolbar.tsx";
import {useChatWebSocket} from "../hooks/WebSocketProvider.tsx";
import {MessageList} from "../Components/MessageList.tsx";
import {CircularProgress} from "@mui/material";
import {useWebsocketAudioPlayer} from "../hooks/useWebsocketAudioPlayer.ts";


export const Chat = ({chatId}: { chatId: string }) => {
    const [configuration, setConfiguration] = useState<Configuration | null>(null);

    useWebsocketAudioPlayer()

    const {data: messages} = useQuery({
        queryKey: ['chat', chatId],
        queryFn: async () => axiosDefault({
            url: `/chat/${chatId}`,
            method: 'get'
        }).then(({data}) => {
            return data.messages as Message[]
        }).catch(() => {
            return []
        })
    })

    const {sendMessage: sendJsonMessage, subscribe} = useChatWebSocket()

    useEffect(() => {
        const handlerMap = {
            [WebsocketEventType.CONFIGURATION]: (message: ReceivedConfigEvent) => {
                setConfiguration(message.configuration)
            },
        }

        const unsubscribeFns = Object.entries(handlerMap || {}).map(([eventType, handler]) => {
            // @ts-expect-error wtf
            return subscribe(eventType as WebsocketEventType, handler)
        })

        return () => {
            unsubscribeFns.forEach((unsubscribe) => unsubscribe())
        }
    }, [subscribe]);

    const [notifySpeechEnd, setNotifySpeechEnd] = useState<NodeJS.Timeout | null>(null)

    const {pause, start} = useMicVAD({
        startOnLoad: true,
        model: 'legacy',
        onSpeechFrames: (audio: Float32Array) => {
            sendJsonMessage({
                'type': 'samples',
                'data': arrayBufferToBase64(audio.buffer)
            })
        },
        onSpeechEnd: () => {
            sendJsonMessage({
                'type': 'speech_end'
            })
            if (notifySpeechEnd !== null) {
                clearTimeout(notifySpeechEnd)
            }
            setNotifySpeechEnd(setTimeout(() => {
                console.log('Confirm speech submission')
                sendJsonMessage({
                    'type': 'speech_prompt_end'
                })
            }, configuration?.app?.after_user_speech_confirmation_delay_ms || 500))
        }
    })

    useEffect(() => {
        if (configuration) {
            if (configuration.app.voice_input_enabled) {
                start()
            } else {
                pause()
            }
        }
    }, [configuration, start, pause]);

    return (
        <Grid container spacing={2} sx={{height: '100vh', margin: 0}}>
            <Grid size={3}>
                <ChatList/>
            </Grid>
            <Grid size={6} sx={{maxHeight: '100vh'}}>
                { messages !== undefined ? <MessageList initialMessages={messages}/> : <CircularProgress/> }
            </Grid>
            <Grid size={3} sx={{maxHeight: '100vh'}}>
                {configuration && <ConfigurationToolbar
                    config={configuration}
                    setConfigField={(path, value) => {
                        sendJsonMessage({
                            type: 'config_change',
                            path: path,
                            value: value
                        })
                    }}
                />}
            </Grid>
        </Grid>
    )
}
