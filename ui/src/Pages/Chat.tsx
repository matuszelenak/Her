import useWebSocket from "react-use-websocket";
import {useAudioPlayer} from "../utils/audioPlayer.ts";
import {useAudioRecorder} from "../utils/audioRecorder.ts";
import Grid from "@mui/material/Grid2";
import {Paper, Slider, Stack, Typography} from "@mui/material";
import {useEffect, useState} from "react";
import Markdown from "react-markdown";
import ScrollableFeed from "react-scrollable-feed";
import {useMicVAD} from "@ricky0123/vad-react"
import {arrayBufferToBase64, base64ToArrayBuffer} from "../utils/encoding.ts";
import {ConfigForm} from "../Components/ConfigForm.tsx";


type Message = {
    role: 'user' | 'agent'
    message: string[]
}


export const Chat = () => {
    const audioContext = new AudioContext();

    const [messages, setMessages] = useState<Message[]>([])
    const [userMessage, setUserMessage] = useState("")
    const [agentMessage, setAgentMessage] = useState<Array<string | null>>([])

    const {feeder, consumerCursor, producerCursor, freeSpace} = useAudioPlayer(audioContext)

    const {
        sendJsonMessage,
    } = useWebSocket(
        `${window.location.protocol == "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws`,
        {
            onMessage: (event: WebSocketEventMap['message']) => {
                const message = JSON.parse(event.data)

                if (message.type == 'speech') {
                    const audioData = new Float32Array(base64ToArrayBuffer(message.samples))
                    const wasConsumed = feeder(audioData)
                }

                if (message.type == 'token') {
                    if (userMessage !== "") {
                        setMessages((prevState: Message[]) => [...prevState, {role: 'user', message: [userMessage]}])
                        setUserMessage("")
                    }
                    setAgentMessage((prevState) => ([...prevState, message.token?.replaceAll('\n', '\r\n')]))
                }

                if (message.type == 'stt_output') {
                    setUserMessage(message.text)
                }
            },
            reconnectAttempts: 1000,
            reconnectInterval: 2000
        }
    );

    useEffect(() => {
        if (agentMessage.length > 0 && agentMessage[agentMessage.length - 1] == null) {
            setMessages((prevState: Message[]) => {
                return [...prevState, {role: 'agent', message: agentMessage.filter(token => token !== null)}]
            })
            setAgentMessage((_) => [])
        }
    }, [agentMessage])

    useEffect(() => {
        sendJsonMessage({event: 'free_space', value: freeSpace})
    }, [freeSpace])

    useMicVAD({
        startOnLoad: true,
        onSpeechStart: () => {
            sendJsonMessage({
                'event': 'speech_start'
            })
        },
        onSpeechEnd: () => {
            sendJsonMessage({
                'event': 'speech_end'
            })
        },
        onVADMisfire: () => {
            sendJsonMessage({
                'event': 'speech_end'
            })
        },
        ortConfig: (ort) => {
            ort.env.wasm.wasmPaths = "/";
        }
    })

    useAudioRecorder((buffer: ArrayBuffer) => {
        sendJsonMessage({
            'event': 'samples',
            'data': arrayBufferToBase64(buffer)
        })
    })

    return (
        <>
            <Grid container spacing={2} sx={{height: '100vh', margin: 0}}>
                <Grid size={3}>

                </Grid>
                <Grid size={6} sx={{maxHeight: '100vh'}}>
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
                    <ScrollableFeed>
                        {messages.map((message: Message, i: number) => (
                            <Stack key={i} direction="row"
                                   justifyContent={message.role === 'agent' ? 'flex-start' : 'flex-end'}
                                   sx={{margin: 2}}>
                                <Paper elevation={2} square={false} sx={{padding: 2, maxWidth: '70%'}}>
                                    <Markdown>
                                        {message.message.join('')}
                                    </Markdown>
                                </Paper>
                            </Stack>
                        ))}
                        {userMessage !== "" && (
                            <Stack direction="row" justifyContent={'flex-end'} sx={{margin: 2}}>
                                <Paper elevation={2} square={false} sx={{padding: 2, maxWidth: '70%'}}>
                                    <Markdown>
                                        {userMessage}
                                    </Markdown>

                                </Paper>
                            </Stack>
                        )}
                        {agentMessage.length > 0 && (
                            <Stack direction="row" justifyContent={'flex-start'} sx={{margin: 2}}>
                                <Paper elevation={2} square={false} sx={{padding: 2, maxWidth: '70%'}}>
                                    <Markdown>
                                        {agentMessage.join('')}
                                    </Markdown>

                                </Paper>
                            </Stack>
                        )}
                    </ScrollableFeed>
                </Grid>
                <Grid size={3}>
                    <ConfigForm/>
                </Grid>
            </Grid>
        </>
    )
}
