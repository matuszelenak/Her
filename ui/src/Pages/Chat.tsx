import useWebSocket from "react-use-websocket";
import {useAudioPlayer} from "../utils/audioPlayer.ts";
import Grid from "@mui/material/Grid2";
import {Button, Paper, Slider, Stack, TextField, Typography} from "@mui/material";
import {useEffect, useState} from "react";
import Markdown from "react-markdown";
import ScrollableFeed from "react-scrollable-feed";
import {arrayBufferToBase64, base64ToArrayBuffer} from "../utils/encoding.ts";
import {useMicVAD} from "../utils/vad/useMic.tsx";
import {Token, WebsocketEvent} from "../types.ts";
import {ChatList} from "../Components/ChatList.tsx";
import {useQuery, useQueryClient} from "@tanstack/react-query";
import {axiosDefault} from "../api.ts";


type Message = {
    role: 'user' | 'assistant'
    message: string[]
}


export const Chat = ({chatId}: {chatId?: string}) => {
    const queryClient = useQueryClient()
    const [messages, setMessages] = useState<Message[]>([])
    const [userMessage, setUserMessage] = useState("")
    const [agentMessage, setAgentMessage] = useState<Array<Token>>([])

    const [speechEnabled, setSpeechEnabled] = useState(false)

    const {feeder, consumerCursor, producerCursor, freeSpace} = useAudioPlayer(speechEnabled)

    useQuery({
        queryKey: ['chat', chatId],
        queryFn: async () => axiosDefault({
            url: `/chat/${chatId}`,
            method: 'get'
        }).then(({data}) => {
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
        `${window.location.protocol == "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws${chatId ? "/" + chatId : ""}`,
        {
            onMessage: (event: WebSocketEventMap['message']) => {
                const message = JSON.parse(event.data) as WebsocketEvent

                if (message.type == 'speech') {
                    const audioData = new Float32Array(base64ToArrayBuffer(message.samples))
                    feeder(audioData)
                }

                if (message.type == 'token') {
                    if (userMessage !== "") {
                        setMessages((prevState: Message[]) => [...prevState, {role: 'user', message: [userMessage]}])
                        setUserMessage("")
                    }
                    setAgentMessage((prevState) => ([...prevState, message.token]))
                }

                if (message.type == 'stt_output') {
                    setUserMessage(message.text)
                }

                if (message.type == 'new_chat') {
                    queryClient.invalidateQueries({queryKey: ['chat_list']})
                }
            },
            reconnectAttempts: 1000,
            reconnectInterval: 2000
        }
    );

    useEffect(() => {
        if (agentMessage.length > 0 && agentMessage[agentMessage.length - 1].done) {
            setMessages((prevState: Message[]) => {
                return [...prevState, {role: 'assistant', message: agentMessage.map(token => token.message.content.replaceAll('\n', '\r\n'))}]
            })
            setAgentMessage((_) => [])
        }
    }, [agentMessage])

    useEffect(() => {
        sendJsonMessage({event: 'free_space', value: freeSpace})
    }, [freeSpace])

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
                    <Stack direction="column" justifyContent="space-between" sx={{height: "100%"}} spacing={2}>
                        <ScrollableFeed>
                            {messages.map((message: Message, i: number) => (
                                <Stack key={i} direction="row"
                                       justifyContent={message.role === 'assistant' ? 'flex-start' : 'flex-end'}
                                       sx={{margin: 2}}>
                                    <Paper elevation={2} square={false} sx={{padding: 2, maxWidth: '70%'}}>
                                        <Typography>
                                            <Markdown>
                                                {message.message.join('')}
                                            </Markdown>
                                        </Typography>

                                    </Paper>
                                </Stack>
                            ))}
                            {userMessage !== "" && (
                                <Stack direction="row" justifyContent={'flex-end'} sx={{margin: 2}}>
                                    <Paper elevation={2} square={false} sx={{padding: 2, maxWidth: '70%'}}>
                                        <Typography>
                                            <Markdown>
                                                {userMessage}
                                            </Markdown>
                                        </Typography>
                                    </Paper>
                                </Stack>
                            )}
                            {agentMessage.length > 0 && (
                                <Stack direction="row" justifyContent={'flex-start'} sx={{margin: 2}}>
                                    <Paper elevation={2} square={false} sx={{padding: 2, maxWidth: '70%'}}>
                                        <Typography>
                                            <Markdown>
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
                                variant="outlined"
                                size="medium"
                                value={textInputPrompt}
                                onChange={(e) => setTextInputPrompt(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.keyCode === 13) {
                                        sendJsonMessage({
                                            event: 'text_prompt',
                                            prompt: textInputPrompt
                                        })
                                        setTextInputPrompt("")
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
                <Grid size={3}>
                    <Button variant="outlined" onClick={() => {
                        vad.toggle()
                    }}>
                        { vad.listening ? "Stop listening" : "Start listening" }
                    </Button>

                    <Button variant="outlined" onClick={() => {
                        sendJsonMessage({
                            event: 'speech_toggle',
                            value: !speechEnabled
                        })
                        setSpeechEnabled((prevState) => !prevState)
                    }}>
                        { speechEnabled ? "Disable speech" : "Enable speech" }
                    </Button>
                    <Slider
                        min={200}
                        max={10000}
                        step={250}
                        value={speechConfirmDelay}
                        onChange={(_: Event, newValue: number | number[]) => setSpeechConfirmDelay(newValue as number)}
                    />
                    {/*<ConfigForm/>*/}
                    <Slider
                        track={false}
                        min={0}
                        max={262144}
                        value={consumerCursor}
                    />
                    <Slider
                        track={false}
                        min={0}
                        max={262144}
                        value={producerCursor}
                    />
                </Grid>
            </Grid>
        </>
    )
}
