import useWebSocket from "react-use-websocket";
import Grid from "@mui/material/Grid2";
import {Box, Button, Stack, TextField} from "@mui/material";
import {useEffect, useState} from "react";
import Markdown from "react-markdown";
import ScrollableFeed from "react-scrollable-feed";
import {arrayBufferToBase64} from "../utils/encoding.ts";
import {useMicVAD} from "../utils/vad/useMic.tsx";
import {Configuration, Token, WebSocketEvent, WebsocketEventType} from "../types.ts";
import {ChatList} from "../Components/ChatList.tsx";
import {useQuery, useQueryClient} from "@tanstack/react-query";
import {axiosDefault} from "../api.ts";
import {ConfigurationToolbar} from "../Components/ConfigurationToolbar.tsx";
import remarkGfm from "remark-gfm";
import {useNavigate, useParams} from "react-router-dom";
import {usePlayer} from "../hooks/useAudioPlayer.ts";


type Message = {
    role: 'user' | 'assistant' | 'tool'
    content: string
}


type LiveTranscribedText = {
    stableWords: string[],
    undeterminedWords: string[]
}


const renderUserMessage = (msg: LiveTranscribedText) => {
    return `${msg.stableWords.join(' ')} ${msg.undeterminedWords.join(' ')}`
}


export const Chat = () => {
    const {chatId} = useParams<string>();
    const queryClient = useQueryClient()
    const navigate = useNavigate()
    const [configuration, setConfiguration] = useState<Configuration | null>(null);
    const [messages, setMessages] = useState<Message[]>([])
    const [inProgressUserMessage, setInProgressUserMessage] = useState<LiveTranscribedText>({
        stableWords: [],
        undeterminedWords: []
    })
    const [inProgressAgentMessage, setInProgressAgentMessage] = useState<Array<Token>>([])

    const {queueAudio, finishedId, stop: audioPlayerStop} = usePlayer()
    useQuery({
        queryKey: ['chat', chatId],
        queryFn: async () => axiosDefault({
            url: `/chat/${chatId}`,
            method: 'get'
        }).then(({data}) => {
            setInProgressUserMessage({
                stableWords: [],
                undeterminedWords: []
            })
            setMessages(data.messages as Message[])
            return []
        }),
        enabled: !!chatId
    })

    useEffect(() => {
        const getNewChatId = async () => {
            const newChatId = await axiosDefault({
                url: `/chat/new`,
                method: 'post'
            }).then(({data}: { data: string }) => data)
            navigate(`/chat/${newChatId}`)
            await queryClient.invalidateQueries({queryKey: ['chat_list']})
        }

        if (!chatId) {
            getNewChatId()
        }
    }, [chatId]);

    const commitUserMessage = () => {
        setMessages((previousMessages: Message[]) => [
            ...previousMessages,
            {
                role: 'user',
                content: renderUserMessage(inProgressUserMessage)
            }
        ])
        setInProgressUserMessage({
            stableWords: [],
            undeterminedWords: []
        })
    }

    const commitAgentMessage = () => {
        setMessages((previousMessages: Message[]) => [
                ...previousMessages,
                {
                    role: 'assistant',
                    content: inProgressAgentMessage.map(token => token.message.content.replaceAll('\n', '\r\n')).join('')
                }
            ]
        )
        setInProgressAgentMessage(() => [])
    }

    const {
        sendJsonMessage,
    } = useWebSocket(
        `${window.location.protocol == "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws/chat/${chatId}`,
        {
            onMessage: async (event: WebSocketEventMap['message']) => {
                const message = JSON.parse(event.data) as WebSocketEvent

                switch (message.type) {
                    case WebsocketEventType.CONFIGURATION:
                        setConfiguration(message.configuration)
                        console.log(message.configuration)
                        break

                    case WebsocketEventType.USER_TRANSCRIPTION_INVALIDATION:
                        break;

                    case WebsocketEventType.TOKEN:
                        if (inProgressUserMessage.stableWords.length > 0) {
                            commitUserMessage()
                        }
                        if (message.token != null) {
                            setInProgressAgentMessage((prevState) => ([...prevState, message.token!]))
                        } else {
                            commitAgentMessage()
                        }

                        break;

                    case WebsocketEventType.USER_TRANSCRIPTION:
                        audioPlayerStop()
                        if (message.segment.complete) {
                            setInProgressUserMessage((prev) => ({
                                stableWords: [...prev.stableWords, ...message.segment.words],
                                undeterminedWords: []
                            }))
                        } else {
                            setInProgressUserMessage((prev) => ({
                                stableWords: prev.stableWords,
                                undeterminedWords: message.segment.words
                            }))
                        }
                        break;

                    case WebsocketEventType.SPEECH_FILE:
                        await queueAudio(message)
                        break;

                    case WebsocketEventType.ASSISTANT_SPEECH_START:
                        audioPlayerStop()
                        break;

                    case WebsocketEventType.MANUAL_PROMPT:
                        setMessages((previousMessages: Message[]) => [
                            ...previousMessages,
                            {
                                role: 'user',
                                content: message.text
                            }
                        ])
                        break;
                }
            },
            shouldReconnect: () => true,
            reconnectAttempts: 1000,
            reconnectInterval: 2000,
            share: true
        },
        !!chatId
    );

    useEffect(() => {
        if (finishedId) {
            sendJsonMessage({
                type: 'finished_speaking'
            })
        }
    }, [finishedId, sendJsonMessage]);

    const [notifySpeechEnd, setNotifySpeechEnd] = useState<NodeJS.Timeout | null>(null)

    const { pause, start } = useMicVAD({
        startOnLoad: false,
        model: 'v5',
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
            }, configuration?.app?.after_user_speech_confirmation_delay_ms || 0))
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
                            {messages.filter(({role}) => role === 'assistant' || role === 'user').map((message: Message, i: number) => (
                                <Stack key={i} direction="row"
                                       justifyContent={message.role === 'assistant' ? 'flex-start' : 'flex-end'}
                                       sx={{margin: 2}}>
                                    <Box sx={{
                                        maxWidth: '70%',
                                        borderRadius: 4,
                                        padding: 2,
                                        border: 2,
                                        borderColor: 'darkgrey',
                                        bgcolor: 'background.paper'
                                    }}>
                                        <Markdown remarkPlugins={[remarkGfm]}>
                                            {message.content}
                                        </Markdown>
                                    </Box>
                                </Stack>
                            ))}
                            {(inProgressUserMessage.undeterminedWords.length > 0 || inProgressUserMessage.stableWords.length > 0) && (
                                <Stack direction="row" justifyContent={'flex-end'} sx={{margin: 2}}>
                                    <Box sx={{
                                        maxWidth: '70%',
                                        borderRadius: 4,
                                        padding: 2,
                                        border: 2,
                                        borderColor: 'darkgrey',
                                        bgcolor: 'background.paper'
                                    }}>
                                        <Markdown remarkPlugins={[remarkGfm]}>
                                            {renderUserMessage(inProgressUserMessage)}
                                        </Markdown>
                                    </Box>
                                </Stack>
                            )}
                            {inProgressAgentMessage.length > 0 && (
                                <Stack direction="row" justifyContent={'flex-start'} sx={{margin: 2}}>
                                    <Box sx={{
                                        maxWidth: '70%',
                                        borderRadius: 4,
                                        padding: 2,
                                        border: 2,
                                        borderColor: 'darkgrey',
                                        bgcolor: 'background.paper'
                                    }}>
                                        <Markdown remarkPlugins={[remarkGfm]}>
                                            {inProgressAgentMessage.map(token => token.message.content.replaceAll('\n', '\r\n')).join('')}
                                        </Markdown>
                                    </Box>
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
                                                type: 'text_prompt',
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
                                    type: 'text_prompt',
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
        </>
    )
}
