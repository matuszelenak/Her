import useWebSocket from "react-use-websocket";
import {useAudioPlayer} from "../utils/audioPlayer.ts";
import {useAudioRecorder} from "../utils/audioRecorder.ts";
import Grid from "@mui/material/Grid2";
import {Paper, Stack, Typography} from "@mui/material";
import {useState} from "react";
import Markdown from "react-markdown";


type Message = {
    role: 'user' | 'agent'
    message: string
}


export const Chat = ({chatId}: { chatId: string }) => {
    const audioContext = new AudioContext();

    const [messages, setMessages] = useState<Message[]>([])
    const [userMessage, setUserMessage] = useState("")
    const [agentMessage, setAgentMessage] = useState("")

    const {feeder} = useAudioPlayer(audioContext)
    const {
        sendJsonMessage,
    } = useWebSocket(
        `${window.location.protocol == "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws/${chatId}/output`,
        {
            onMessage: (event: WebSocketEventMap['message']) => {
                const message = JSON.parse(event.data)

                if (message.type == 'speech') {
                    const audioData = new Float32Array(message.samples)
                    const wasConsumed = feeder(audioData)

                    if (wasConsumed) {
                        sendJsonMessage({})
                    } else {
                        sendJsonMessage({command: 'wait'})
                    }
                }
            },
            reconnectAttempts: 1000,
            reconnectInterval: 2000
        }
    );

    const {
        sendMessage,
    } = useWebSocket(
        `${window.location.protocol == "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws/${chatId}/input`,
        {
            onMessage: (event: WebSocketEventMap['message']) => {
                const message = JSON.parse(event.data)

                if (message.type == 'token') {
                    if (userMessage !== "") {
                        setMessages((prevState: Message[]) => [...prevState, {role: 'user', message: userMessage}])
                        setUserMessage("")
                    }
                    if (message.token === null) {
                        setMessages((prevState: Message[]) => [...prevState, {role: 'agent', message: agentMessage}])
                        setAgentMessage("")
                    } else {
                        console.log(message.token)
                        setAgentMessage((prevState) => `${prevState}${message.token.replaceAll('\n', '\r\n')}`)
                    }

                }

                if (message.type == 'stt_output') {
                    console.log(message.text)
                    setUserMessage(message.text)
                }
            },
            reconnectAttempts: 1000,
            reconnectInterval: 2000
        }
    );

    useAudioRecorder((buffer: ArrayBuffer) => {
        sendMessage(buffer)
    })

    return (
        <>
            <Grid container spacing={2} sx={{height: '100vh'}}>
                <Grid size={3}>

                </Grid>
                <Grid size={6}>
                    <Stack direction="column" spacing={2} sx={{maxHeight: '100%', overflow: "auto", padding: 2}}>
                        {messages.map((message: Message) => (
                            <Stack direction="row"
                                   justifyContent={message.role === 'agent' ? 'flex-start' : 'flex-end'}>
                                <Paper elevation={2} square={false} sx={{padding: 2, maxWidth: '70%'}}>
                                    <Typography variant="body1">
                                        <Markdown>
                                            {message.message}
                                        </Markdown>
                                    </Typography>
                                </Paper>
                            </Stack>
                        ))}
                        {userMessage !== "" && (
                            <Stack direction="row" justifyContent={'flex-end'}>
                                <Paper elevation={2} square={false} sx={{padding: 2, maxWidth: '70%'}}>
                                    <Typography variant="body1">
                                        <Markdown>
                                            {userMessage}
                                        </Markdown>
                                    </Typography>

                                </Paper>
                            </Stack>
                        )}
                        {agentMessage !== "" && (
                            <Stack direction="row" justifyContent={'flex-start'}>
                                <Paper elevation={2} square={false} sx={{padding: 2, maxWidth: '70%'}}>
                                    <Typography variant="body1">
                                        <Markdown>
                                            {agentMessage}
                                        </Markdown>
                                    </Typography>

                                </Paper>
                            </Stack>
                        )}
                    </Stack>
                </Grid>
                <Grid size={3}>

                </Grid>
            </Grid>
        </>
    )
}
