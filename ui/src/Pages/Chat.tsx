import useWebSocket from "react-use-websocket";
import Grid from "@mui/material/Grid2";
import { Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import Markdown from "react-markdown";
import ScrollableFeed from "react-scrollable-feed";
import { arrayBufferToBase64 } from "../utils/encoding.ts";
import { useMicVAD } from "../utils/vad/useMic.tsx";
import { ChatConfiguration, Token, WebSocketEvent, WebsocketEventType } from "../types.ts";
import { ChatList } from "../Components/ChatList.tsx";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { axiosDefault } from "../api.ts";
import { DependencyToolbar } from "../Components/DependencyToolbar.tsx";
import remarkGfm from "remark-gfm";
import { useNavigate, useParams } from "react-router-dom";
import { usePlayer } from "../hooks/useAudioPlayer.ts";


type Message = {
    role: 'user' | 'assistant' | 'tool'
    message: string[]
}


type UserMessage = {
    completedWords: string[],
    uncertainWords: string[]
}


const renderUserMessage = (msg: UserMessage) => {
    return `${msg.completedWords.join(' ')} ${msg.uncertainWords.join(' ')}`
}


export const Chat = () => {
    const {chatId} = useParams<string>();
    const queryClient = useQueryClient()
    const navigate = useNavigate()
    const [messages, setMessages] = useState<Message[]>([])
    const [userMessage, setUserMessage] = useState<UserMessage>({
        completedWords: [],
        uncertainWords: []
    })
    const [agentMessage, setAgentMessage] = useState<Array<Token>>([])
    const [config, setConfig] = useState<ChatConfiguration | null>(null)

    const [speechEnabled, setSpeechEnabled] = useState(true)

    const {queueAudio, finishedId, stop: audioPlayerStop} = usePlayer()
    useQuery({
        queryKey: ['chat', chatId],
        queryFn: async () => axiosDefault({
            url: `/chat/${chatId}`,
            method: 'get'
        }).then(({data}) => {
            setUserMessage({
                completedWords: [],
                uncertainWords: []
            })
            setMessages(data.messages.map((msg: any) => ({
                ...msg,
                message: [msg.content]
            })))
            return []
        }),
        enabled: !!chatId
    })

    const {
        sendJsonMessage,
    } = useWebSocket(
        `${window.location.protocol == "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws/chat`,
        {
            onMessage: async (event: WebSocketEventMap['message']) => {
                const message = JSON.parse(event.data) as WebSocketEvent

                console.log(`Received websocket msg`)
                console.log(message)

                switch (message.type) {
                    case WebsocketEventType.STT_OUTPUT_INVALIDATION:
                        break;
                    case WebsocketEventType.TOKEN:
                        if (userMessage.completedWords.length > 0) {
                            setMessages((prevState: Message[]) => [...prevState, {
                                role: 'user',
                                message: [renderUserMessage(userMessage)]
                            }])
                            setUserMessage({
                                completedWords: [],
                                uncertainWords: []
                            })
                        }
                        setAgentMessage((prevState) => ([...prevState, message.token]))
                        break;
                    case WebsocketEventType.STT_OUTPUT:
                        audioPlayerStop()
                        if (message.segment.complete) {
                            setUserMessage((prev) => ({
                                completedWords: [...prev.completedWords, ...message.segment.words],
                                uncertainWords: []
                            }))
                        } else {
                            setUserMessage((prev) => ({
                                completedWords: prev.completedWords,
                                uncertainWords: message.segment.words
                            }))
                        }
                        break;
                    case WebsocketEventType.SPEECH_FILE:
                        await queueAudio(message)
                        break;
                    case WebsocketEventType.SPEECH_START:
                        audioPlayerStop()
                        break;
                    case WebsocketEventType.NEW_CHAT:
                        navigate(`/chat/${message.chat_id}`)
                        await queryClient.invalidateQueries({queryKey: ['chat_list']})
                        break;
                    case WebsocketEventType.CONFIG:
                        setConfig(message.config)
                        break;
                    case WebsocketEventType.MANUAL_PROMPT:
                        setUserMessage({
                            completedWords: [message.text],
                            uncertainWords: []
                        })
                        break;
                }


                // if (message.type == 'stt_output_invalidation') {
                //     if (userMessage !== "") {
                //         setMessages((prevState: Message[]) => [...prevState, {
                //             role: 'user',
                //             message: [`~~${userMessage}~~`]
                //         }])
                //     }
                //     setUserMessage("")
                // }

            },
            reconnectAttempts: 1000,
            reconnectInterval: 2000,
            share: true
        }
    );

    useEffect(() => {
        sendJsonMessage({
            event: 'load_chat',
            chat_id: chatId || null
        })
        if (!chatId) {
            setMessages([])
        }
    }, [chatId]);

    useEffect(() => {
        if (finishedId) {
            sendJsonMessage({
                event: 'finished_speaking'
            })
        }
    }, [finishedId]);

    useEffect(() => {
        if (agentMessage.length > 0 && agentMessage[agentMessage.length - 1].done) {
            setMessages((prevState: Message[]) => {
                return [...prevState, {
                    role: 'assistant',
                    message: agentMessage.map(token => token.message.content.replaceAll('\n', '\r\n'))
                }]
            })
            setAgentMessage((_) => [])
        }
    }, [agentMessage])

    const [notifySpeechEnd, setNotifySpeechEnd] = useState<NodeJS.Timeout | null>(null)
    const [speechConfirmDelay, setSpeechConfirmDelay] = useState(2000)

    const vad = useMicVAD({
        startOnLoad: false,
        onSpeechFrames: (audio: Float32Array) => {
            sendJsonMessage({
                'event': 'samples',
                'data': arrayBufferToBase64(audio.buffer)
            })
        },
        onSpeechEnd: () => {
            sendJsonMessage({
                'event': 'speech_end'
            })
            if (notifySpeechEnd !== null) {
                clearTimeout(notifySpeechEnd)
            }
            setNotifySpeechEnd(setTimeout(() => {
                console.log('Confirm speech submission')
                sendJsonMessage({
                    'event': 'speech_prompt_end'
                })
            }, speechConfirmDelay))
        }
    })

    const [textInputPrompt, setTextInputPrompt] = useState("")

    return (
        <>
            <Grid container spacing={2} sx={{height: '100vh', margin: 0}}>
                <Grid size={3}>
                    <ChatList/>
                </Grid>
                <Grid size={6} sx={{maxHeight: '100vh'}}>
                    <Typography>{vad.listening}</Typography>
                    <Stack direction="column" justifyContent="space-between" sx={{height: "100%"}} spacing={2}>
                        <ScrollableFeed>
                            {messages.filter(({role}) => role === 'assistant' || role === 'user').map((message: Message, i: number) => (
                                <Stack key={i} direction="row"
                                       justifyContent={message.role === 'assistant' ? 'flex-start' : 'flex-end'}
                                       sx={{margin: 2}}>
                                    <Paper elevation={2} square={false} sx={{padding: 2, maxWidth: '70%'}}>
                                        <Markdown remarkPlugins={[remarkGfm]}>
                                            {message.message.join('')}
                                        </Markdown>

                                    </Paper>
                                </Stack>
                            ))}
                            {(userMessage.uncertainWords.length > 0 || userMessage.completedWords.length > 0) && (
                                <Stack direction="row" justifyContent={'flex-end'} sx={{margin: 2}}>
                                    <Paper elevation={2} square={false} sx={{padding: 2, maxWidth: '70%'}}>
                                        <Markdown remarkPlugins={[remarkGfm]}>
                                            {renderUserMessage(userMessage)}
                                        </Markdown>
                                    </Paper>
                                </Stack>
                            )}
                            {agentMessage.length > 0 && (
                                <Stack direction="row" justifyContent={'flex-start'} sx={{margin: 2}}>
                                    <Paper elevation={2} square={false} sx={{padding: 2, maxWidth: '70%'}}>
                                        <Typography>
                                            <Markdown remarkPlugins={[remarkGfm]}>
                                                {agentMessage.map(token => token.message.content.replaceAll('\n', '\r\n')).join('')}
                                            </Markdown>
                                        </Typography>
                                    </Paper>
                                </Stack>
                            )}
                        </ScrollableFeed>
                        <Stack direction="row" spacing={1} justifyContent="space-between" padding={2}>
                            <TextField
                                fullWidth
                                multiline
                                variant="outlined"
                                size="medium"
                                value={textInputPrompt}
                                onChange={(e) => setTextInputPrompt(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.keyCode === 13) {
                                        if (!e.shiftKey) {
                                            sendJsonMessage({
                                                event: 'text_prompt',
                                                prompt: textInputPrompt
                                            })
                                            setTextInputPrompt("")
                                            e.preventDefault()
                                        }
                                    }
                                }}
                            />
                            <Button variant="outlined" onClick={() => {
                                sendJsonMessage({
                                    event: 'text_prompt',
                                    prompt: textInputPrompt
                                })
                                setTextInputPrompt("")
                            }}>
                                Submit
                            </Button>
                        </Stack>
                    </Stack>
                </Grid>
                <Grid size={3} sx={{maxHeight: '100vh'}}>
                    {config && <DependencyToolbar
                        config={config}
                        setConfigValue={(field, value) => {
                            sendJsonMessage({
                                event: 'config',
                                field: field,
                                value: value
                            })
                        }}
                        vad={vad}
                        speech={{
                            speaking: speechEnabled,
                            toggleSpeaking: () => {
                                setSpeechEnabled((prevState) => {
                                    sendJsonMessage({
                                        event: 'speech_toggle',
                                        value: !prevState
                                    })
                                    return !prevState
                                })
                            },
                            confirmDelay: speechConfirmDelay,
                            setConfirmDelay: setSpeechConfirmDelay
                        }}
                    />
                    }
                </Grid>
            </Grid>
        </>
    )
}
