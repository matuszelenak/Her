import {DependencyStatus, OllamaModel, WebsocketEvent} from "../types.ts";
import {
    Box,
    Button, Checkbox,
    CircularProgress,
    FormControl,
    Grid,
    Input,
    InputLabel, ListItemText,
    MenuItem, OutlinedInput,
    Paper,
    Select,
    Slider,
    Stack,
    TextField,
    Typography
} from "@mui/material";
import {useQuery} from "@tanstack/react-query";
import {axiosDefault} from "../api.ts";
import useWebSocket from "react-use-websocket";
import {Dispatch, SetStateAction, useEffect, useState} from "react";
import {useDelayedInput} from "../utils/useDelayedInput.ts";


const languages = ['cs', 'en']


export const DependencyToolbar = ({
                                      chatId,
                                      vad,
                                      speechConfirmDelay,
                                      setSpeechConfirmDelay,
                                      speechEnabled,
                                      setSpeechEnabled
                                  }: {
    chatId: string | undefined,
    vad: { listening: boolean, toggle: () => void },
    speechConfirmDelay: number,
    setSpeechConfirmDelay: Dispatch<SetStateAction<number>>,
    speechEnabled: boolean,
    setSpeechEnabled: Dispatch<SetStateAction<boolean>>
}) => {

    const [model, setModel] = useState('none')
    const [temperature, rtTemperature, setRTTemperature] = useDelayedInput<number | null>(null, 200)
    const [repeatPenalty, rtRepeatPenalty, setRTRepeatPenalty] = useDelayedInput<number | null>(null, 200)
    const [ctxLength, rtCtxLength, setRTCtxLength] = useDelayedInput<number | null>(null, 200)
    const [sysPrompt, rtSystemPrompt, setRTSystemPrompt] = useDelayedInput<string | null>(null, 200)
    const [tools, setTools] = useState<string[]>([])
    const [voice, setVoice] = useState("aloy.wav")
    const [xttsLang, setXttsLang] = useState("en")

    const [status, setStatus] = useState<DependencyStatus>({
        xtts: false,
        whisper: false,
        ollama: []
    })

    const {sendJsonMessage} = useWebSocket(
        `${window.location.protocol == "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws${chatId ? "/" + chatId : ""}`,
        {
            onMessage: (event: WebSocketEventMap['message']) => {
                const message = JSON.parse(event.data) as WebsocketEvent

                if (message.type == 'dependency_status') {
                    setStatus(message.status)
                }

                if (message.type == 'config') {
                    console.log(message.config)
                    setModel(message.config.ollama.model)
                    setRTTemperature(message.config.ollama.temperature)
                    setRTRepeatPenalty(message.config.ollama.repeat_penalty)
                    setRTCtxLength(message.config.ollama.ctx_length)
                    setRTSystemPrompt(message.config.ollama.system_prompt)
                }
            },
            reconnectAttempts: 1000,
            reconnectInterval: 2000,
            share: true
        }
    );

    useEffect(() => {
        sendJsonMessage({
            event: 'config_request'
        })
    }, []);

    useEffect(() => {
        if (temperature !== null) {
            sendJsonMessage({
                event: 'config',
                field: 'ollama.temperature',
                value: temperature
            })
        }
    }, [temperature]);

    useEffect(() => {
        if (ctxLength !== null) {
            sendJsonMessage({
                event: 'config',
                field: 'ollama.ctx_length',
                value: ctxLength
            })
        }
    }, [ctxLength]);

    useEffect(() => {
        if (repeatPenalty !== null) {
            sendJsonMessage({
                event: 'config',
                field: 'ollama.repeat_penalty',
                value: repeatPenalty
            })
        }
    }, [repeatPenalty]);

    useEffect(() => {
        if (sysPrompt !== null) {
            sendJsonMessage({
                event: 'config',
                field: 'ollama.system_prompt',
                value: sysPrompt
            })
        }
    }, [sysPrompt]);

    const {data: models} = useQuery({
        queryKey: ['models'],
        queryFn: async () => axiosDefault({
            url: '/models',
            method: 'get'
        }).then(({data}) => data as OllamaModel[])
    })

    const {data: voices} = useQuery({
        queryKey: ['voices'],
        queryFn: async () => axiosDefault({
            url: '/xtts',
            method: 'get'
        }).then(({data}) => data.voices as string[]),
    })

    const {data: toolChoices} = useQuery({
        queryKey: ['tools'],
        queryFn: async () => axiosDefault({
            url: '/tools',
            method: 'get'
        }).then(({data}) => data as string[]),
    })

    if (!models || !voices || toolChoices == undefined) {
        return <CircularProgress/>
    }

    return (
        <>
            <Paper elevation={1} sx={{padding: 2, margin: 2}}>
                <Stack direction="row" justifyContent="space-between">
                    <Typography variant="h6">Whisper</Typography>
                    <Button disabled={!status.whisper} variant="outlined" onClick={() => {
                        vad.toggle()
                    }}>
                        {vad.listening ? "Stop listening" : "Start listening"}
                    </Button>
                </Stack>

                <Stack direction='column' spacing={2} marginTop={1}>
                    <Box>
                        <Typography id="input-slider" gutterBottom>
                            After speech confirm delay
                        </Typography>
                        <Grid container spacing={2} sx={{alignItems: 'center'}}>
                            <Grid item xs>
                                <Slider
                                    min={200}
                                    max={10000}
                                    step={100}
                                    disabled={!status.whisper}
                                    value={speechConfirmDelay}
                                    onChange={(_: Event, newValue: number | number[]) => setSpeechConfirmDelay(newValue as number)}
                                />
                            </Grid>
                            <Grid item>
                                <Input
                                    size="small"
                                    value={speechConfirmDelay}
                                    onChange={(event) => {
                                        // @ts-ignore
                                        setSpeechConfirmDelay(event.target.value as number)
                                    }}
                                    inputProps={{
                                        min: 200,
                                        max: 10000,
                                        step: 100,
                                        type: 'number'
                                    }}
                                />
                            </Grid>
                        </Grid>
                    </Box>
                </Stack>


            </Paper>

            <Paper elevation={1} sx={{padding: 2, margin: 2}}>
                <Typography variant="h6">Ollama</Typography>

                <Stack direction='column' spacing={2} marginTop={1}>
                    <FormControl>
                        <InputLabel id="model-select-label">Model</InputLabel>
                        <Select
                            sx={{minWidth: 300}}
                            variant='outlined'
                            labelId="model-select-label"
                            id="model-select"
                            label='Model'
                            value={model}
                            onChange={(e) => {
                                setModel(e.target.value)
                                sendJsonMessage({
                                    event: 'config',
                                    field: 'ollama.model',
                                    value: e.target.value
                                })
                            }}
                        >
                            <MenuItem key={'none'} value={'none'}></MenuItem>
                            {models.map(({name, model}) => (
                                <MenuItem key={name}
                                          value={model}>{status.ollama?.includes(name) ? '[loaded]' : ''} {name}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    <TextField
                        value={rtSystemPrompt || ""}
                        onChange={(e) => setRTSystemPrompt(e.target.value)}
                        multiline
                    />
                    <Box>
                        <Typography id="input-slider" gutterBottom>
                            Context length
                        </Typography>
                        <Grid container spacing={2} sx={{alignItems: 'center'}}>
                            <Grid item xs>
                                <Slider step={1024} value={rtCtxLength || 1024}
                                        onChange={(_, v) => setRTCtxLength(v as number)}
                                        min={1024} max={32768}/>
                            </Grid>
                            <Grid item>
                                <Input
                                    size="small"
                                    value={rtCtxLength}
                                    onChange={(e) => setRTCtxLength(Number.parseInt(e.target.value))}
                                    inputProps={{
                                        min: 1024,
                                        max: 32768,
                                        step: 1024,
                                        type: 'number'
                                    }}
                                />
                            </Grid>
                        </Grid>
                    </Box>
                    <Box>
                        <Typography id="input-slider" gutterBottom>
                            Temperature
                        </Typography>
                        <Grid container spacing={2} sx={{alignItems: 'center'}}>
                            <Grid item xs>
                                <Slider step={0.05} value={rtTemperature || 0}
                                        onChange={(_, v) => setRTTemperature(v as number)} min={0} max={2}/>
                            </Grid>
                            <Grid item>
                                <Input
                                    size="small"
                                    value={rtTemperature}
                                    onChange={(e) => setRTTemperature(Number.parseFloat(e.target.value))}
                                    inputProps={{
                                        min: 0,
                                        max: 2,
                                        step: 0.05,
                                        type: 'number'
                                    }}
                                />
                            </Grid>
                        </Grid>
                    </Box>
                    <Box>
                        <Typography id="input-slider" gutterBottom>
                            Repeat penalty
                        </Typography>
                        <Grid container spacing={2} sx={{alignItems: 'center'}}>
                            <Grid item xs>
                                <Slider step={0.1} value={rtRepeatPenalty || 1}
                                        onChange={(_, v) => setRTRepeatPenalty(v as number)} min={0} max={1.5}/>
                            </Grid>
                            <Grid item>
                                <Input
                                    size="small"
                                    value={rtRepeatPenalty}
                                    onChange={(e) => setRTRepeatPenalty(Number.parseFloat(e.target.value))}
                                    inputProps={{
                                        min: 0,
                                        max: 1.5,
                                        step: 0.1,
                                        type: 'number'
                                    }}
                                />
                            </Grid>
                        </Grid>
                    </Box>

                    <FormControl>
                        <InputLabel id="tools-label">Tools</InputLabel>
                        <Select
                            labelId="tools-label"
                            id="tools-checkbox"
                            multiple
                            value={tools}
                            onChange={(e) => {
                                setTools(e.target.value as string[])
                                sendJsonMessage({
                                    event: 'config',
                                    field: 'ollama.tools',
                                    value: e.target.value
                                })
                            }}
                            input={<OutlinedInput label="Tools" />}
                            renderValue={(selected) => selected.join(', ')}
                        >
                            {toolChoices.map((name) => (
                                <MenuItem key={name} value={name}>
                                    <Checkbox checked={tools.includes(name)} />
                                    <ListItemText primary={name} />
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </Stack>
            </Paper>

            <Paper elevation={1} sx={{padding: 2, margin: 2}}>
                <Stack direction="row" justifyContent="space-between" sx={{margin: 1}}>
                    <Typography variant="h6">XTTS</Typography>
                    <Button variant="outlined" onClick={() => {
                        sendJsonMessage({
                            event: 'speech_toggle',
                            value: !speechEnabled
                        })
                        setSpeechEnabled((prevState) => !prevState)
                    }}>
                        {speechEnabled ? "Disable speech" : "Enable speech"}
                    </Button>
                </Stack>

                <Stack direction='column' spacing={2} marginTop={1}>
                    <FormControl>
                        <InputLabel id="voice-select-label">Voice</InputLabel>
                        <Select
                            sx={{minWidth: 300}}
                            variant='outlined'
                            labelId="voice-select-label"
                            id="voice-select"
                            label='Voice'
                            value={voice}
                            onChange={(e) => {
                                setVoice(e.target.value)
                                sendJsonMessage({
                                    event: 'config',
                                    field: 'xtts.voice',
                                    value: e.target.value
                                })
                            }}
                        >
                            {voices.map((voice) => (
                                <MenuItem key={voice} value={voice}>{voice}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <FormControl>
                        <InputLabel id="language-select-label">Language</InputLabel>
                        <Select
                            sx={{minWidth: 300}}
                            variant='outlined'
                            labelId="language-select-label"
                            id="language-select"
                            label='Language'
                            value={xttsLang}
                            onChange={(e) => {
                                setXttsLang(e.target.value)
                                sendJsonMessage({
                                    event: 'config',
                                    field: 'xtts.language',
                                    value: e.target.value
                                })
                            }
                            }
                        >
                            {languages.map((lang) => (
                                <MenuItem key={lang} value={lang}>{lang}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </Stack>
            </Paper>
        </>
    )
}
