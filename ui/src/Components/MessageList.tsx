import {Box, Button, Stack, TextField} from "@mui/material";
import ScrollableFeed from "react-scrollable-feed";
import {ManualPromptEvent, Message, STTOutputEvent, Token, TokenEvent, WebsocketEventType} from "../types.ts";
import {useEffect, useState} from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {useChatWebSocket} from "../hooks/WebSocketProvider.tsx";

type LiveTranscribedText = {
    stableWords: string[],
    undeterminedWords: string[]
}


type MessageBubbleProps = {
    msg: string,
    role: 'assistant' | 'user'
}


const MessageBubble = (props: MessageBubbleProps) =>
    <Stack direction="row" justifyContent={props.role == 'assistant' ? 'flex-start' : 'flex-end'} sx={{margin: 2}}>
        <Box sx={{
            maxWidth: '70%',
            borderRadius: 4,
            paddingRight: 2,
            paddingLeft: 2,
            border: 2,
            borderColor: 'darkgrey',
            bgcolor: 'background.paper'
        }}>
            <Markdown remarkPlugins={[remarkGfm]}>
                {props.msg}
            </Markdown>
        </Box>
    </Stack>


const renderUserMessage = (msg: LiveTranscribedText) => {
    return `${msg.stableWords.join(' ')} ${msg.undeterminedWords.join(' ')}`
}

export const MessageList = ({initialMessages}: {initialMessages: Message[]}) => {
    const {sendMessage: sendJsonMessage, subscribe} = useChatWebSocket()

    const [messages, setMessages] = useState<Message[]>(initialMessages)
    const [inProgressUserMessage, setInProgressUserMessage] = useState<LiveTranscribedText>({
        stableWords: [],
        undeterminedWords: []
    })
    const [inProgressAgentMessage, setInProgressAgentMessage] = useState<Array<Token>>([])
    const [textInputPrompt, setTextInputPrompt] = useState("")

    useEffect(() => {
        const handlerMap = {
            [WebsocketEventType.TOKEN]: (message: TokenEvent) => {
                if (inProgressUserMessage.stableWords.length > 0) {
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
                if (message.token != null) {
                    setInProgressAgentMessage((prevState) => ([...prevState, message.token!]))
                } else {
                    setMessages((previousMessages: Message[]) => [
                        ...previousMessages,
                        {
                            role: 'assistant',
                            content: inProgressAgentMessage.map(token => token.message.content.replaceAll('\n', '\r\n')).join('')
                        }
                    ])
                    setInProgressAgentMessage(() => [])
                }
            },
            [WebsocketEventType.MANUAL_PROMPT]: (message: ManualPromptEvent) => {
                setMessages((previousMessages: Message[]) => [
                    ...previousMessages,
                    {
                        role: 'user',
                        content: message.text
                    }
                ])
            },
            [WebsocketEventType.USER_TRANSCRIPTION]: (message: STTOutputEvent) => {
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
            }
        }

        const unsubscribeFns = Object.entries(handlerMap || {}).map(([eventType, handler]) => {
            // @ts-expect-error wtf
            return subscribe(eventType as WebsocketEventType, handler)
        })

        return () => {
            unsubscribeFns.forEach((unsubscribe) => unsubscribe())
        }
    }, [subscribe, setMessages, inProgressAgentMessage, inProgressUserMessage]);

    return (
        <Stack direction="column" justifyContent="space-between" sx={{height: "100%"}} spacing={2}>
            <ScrollableFeed>
                {messages.filter(({role}) => role === 'assistant' || role === 'user').map((message: Message, i: number) => (
                    <MessageBubble msg={message.content} role={message.role} key={i}/>
                ))}

                {inProgressAgentMessage.length > 0 && (
                    <MessageBubble
                        msg={inProgressAgentMessage.map(token => token.message.content.replaceAll('\n', '\r\n')).join('')}
                        role={'assistant'}
                    />
                )}

                {(inProgressUserMessage.undeterminedWords.length > 0 || inProgressUserMessage.stableWords.length > 0) && (
                    <MessageBubble msg={renderUserMessage(inProgressUserMessage)} role={'user'}/>
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
    )
}