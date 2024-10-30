import {Controller, useForm} from "react-hook-form"
import {Configuration, DependencyStatus, OllamaModel, WebsocketEvent} from "../types.ts";
import {
    Box,
    Button,
    CircularProgress,
    FormControl,
    Grid, Input,
    InputLabel,
    MenuItem, Paper,
    Select,
    Slider,
    Stack,
    TextField,
    Typography
} from "@mui/material";
import {useMutation, useQuery} from "@tanstack/react-query";
import {axiosDefault} from "../api.ts";
import useWebSocket from "react-use-websocket";
import {Dispatch, SetStateAction, useState} from "react";


const languages = ['cs', 'en']


export const DependencyToolbar = ({
                                      sessionId,
                                      chatId,
                                      vad,
                                      speechConfirmDelay,
                                      setSpeechConfirmDelay,
                                      speechEnabled,
                                      setSpeechEnabled
                                  }: {
    sessionId: string,
    chatId: string | undefined,
    vad: { listening: boolean, toggle: () => void },
    speechConfirmDelay: number,
    setSpeechConfirmDelay: Dispatch<SetStateAction<number>>,
    speechEnabled: boolean,
    setSpeechEnabled: Dispatch<SetStateAction<boolean>>
}) => {
    const {
        register,
        handleSubmit,
        setValue,
        control,
    } = useForm<Configuration>({
        defaultValues: {
            ollama: {
                model: '',
                temperature: 0.5,
                repeat_penalty: 1,
                ctx_length: 8192,
                system_prompt: ''
            },
            xtts: {
                voice: 'aloy.wav',
                language: 'en'
            },
            whisper: {
                language: 'en',
                model: 'medium.en'
            }
        }
    })

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
            },
            reconnectAttempts: 1000,
            reconnectInterval: 2000,
            share: true
        }
    );

    const {data: config} = useQuery({
        queryKey: ['config'],
        queryFn: async () => axiosDefault({
            url: `/config?session_id=${sessionId}`,
            method: 'get'
        }).then(({data}: { data: Configuration }) => {
            setValue('ollama', data.ollama)
            return data
        })
    })

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
        initialData: []
    })

    const configMutation = useMutation({
        mutationFn: async (data: Configuration) => await axiosDefault({
            url: `/config?session_id=${sessionId}`,
            method: 'POST',
            data: {
                ...config,
                ...data
            }
        })
    })

    if (!models || !config) {
        return <CircularProgress/>
    }

    return (
        <>
            <form onSubmit={handleSubmit((data) => configMutation.mutate(data))}>
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
                        <FormControl>
                            <InputLabel id="model-select-label">Model</InputLabel>
                            <Controller
                                render={({field}) => (
                                    <Select
                                        sx={{minWidth: 300}}
                                        variant='outlined'
                                        labelId="model-select-label"
                                        id="model-select"
                                        label='Model'
                                        value={field.value}
                                        onChange={field.onChange}
                                    >
                                        {['medium.en', 'large-v3'].map((model) => (
                                            <MenuItem key={model} value={model}>{model}</MenuItem>
                                        ))}
                                    </Select>
                                )}
                                name={`whisper.model`}
                                control={control}
                                defaultValue={'medium.en'}
                            />
                        </FormControl>
                        <FormControl>
                            <InputLabel id="language-select-label">Language</InputLabel>
                            <Controller
                                render={({field}) => (
                                    <Select
                                        sx={{minWidth: 300}}
                                        variant='outlined'
                                        labelId="language-select-label"
                                        id="language-select"
                                        label='Language'
                                        value={field.value}
                                        onChange={field.onChange}
                                    >
                                        {languages.map((lang) => (
                                            <MenuItem key={lang} value={lang}>{lang}</MenuItem>
                                        ))}
                                    </Select>
                                )}
                                name={`whisper.language`}
                                control={control}
                                defaultValue={'en'}
                            />
                        </FormControl>
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
                            <Controller
                                render={({field}) => (
                                    <Select
                                        sx={{minWidth: 300}}
                                        variant='outlined'
                                        labelId="model-select-label"
                                        id="model-select"
                                        label='Model'
                                        value={field.value}
                                        onChange={field.onChange}
                                    >
                                        {models.map(({name, model}) => (
                                            <MenuItem key={name}
                                                      value={model}>{status.ollama?.includes(name) ? '[loaded]' : ''} {name}</MenuItem>
                                        ))}
                                    </Select>
                                )}
                                name={`ollama.model`}
                                control={control}
                                defaultValue={'mistral-nemo:12b-instruct-2407-q8_0'}
                            />
                        </FormControl>
                        <TextField
                            {...register('ollama.system_prompt')}
                            multiline
                        />
                        <Box>
                            <Typography id="input-slider" gutterBottom>
                                Context length
                            </Typography>
                            <Grid container spacing={2} sx={{alignItems: 'center'}}>
                                <Grid item xs>
                                    <Controller
                                        render={({field}) => (
                                            <Slider step={1024} value={field.value} onChange={field.onChange} min={1024}
                                                    max={32768}/>
                                        )}
                                        name={`ollama.ctx_length`}
                                        control={control}
                                    />
                                </Grid>
                                <Grid item>
                                    <Controller
                                        render={({field}) => (
                                            <Input
                                                size="small"
                                                value={field.value}
                                                onChange={field.onChange}
                                                inputProps={{
                                                    min: 1024,
                                                    max: 32768,
                                                    step: 1024,
                                                    type: 'number'
                                                }}
                                            />
                                        )}
                                        name={`ollama.ctx_length`}
                                        control={control}
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
                                    <Controller
                                        render={({field}) => (
                                            <Slider step={0.05} value={field.value} onChange={field.onChange} min={0}
                                                    max={2}/>
                                        )}
                                        name={`ollama.temperature`}
                                        control={control}
                                    />
                                </Grid>
                                <Grid item>
                                    <Controller
                                        render={({field}) => (
                                            <Input
                                                size="small"
                                                value={field.value}
                                                onChange={field.onChange}
                                                inputProps={{
                                                    min: 0,
                                                    max: 2,
                                                    step: 0.05,
                                                    type: 'number'
                                                }}
                                            />
                                        )}
                                        name={`ollama.temperature`}
                                        control={control}
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
                                    <Controller
                                        render={({field}) => (
                                            <Slider step={0.1} value={field.value} onChange={field.onChange} min={0}
                                                    max={1.5}/>
                                        )}
                                        name={`ollama.repeat_penalty`}
                                        control={control}
                                    />
                                </Grid>
                                <Grid item>
                                    <Controller
                                        render={({field}) => (
                                            <Input
                                                size="small"
                                                value={field.value}
                                                onChange={field.onChange}
                                                inputProps={{
                                                    min: 0,
                                                    max: 1.5,
                                                    step: 0.1,
                                                    type: 'number'
                                                }}
                                            />
                                        )}
                                        name={`ollama.repeat_penalty`}
                                        control={control}
                                    />
                                </Grid>
                            </Grid>
                        </Box>
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
                            <Controller
                                render={({field}) => (
                                    <Select
                                        sx={{minWidth: 300}}
                                        variant='outlined'
                                        labelId="voice-select-label"
                                        id="voice-select"
                                        label='Voice'
                                        value={field.value}
                                        onChange={field.onChange}
                                    >
                                        {voices.map((voice) => (
                                            <MenuItem key={voice} value={voice}>{voice}</MenuItem>
                                        ))}
                                    </Select>
                                )}
                                name={`xtts.voice`}
                                control={control}
                                defaultValue={'aloy.wav'}
                            />
                        </FormControl>

                        <FormControl>
                            <InputLabel id="language-select-label">Language</InputLabel>
                            <Controller
                                render={({field}) => (
                                    <Select
                                        sx={{minWidth: 300}}
                                        variant='outlined'
                                        labelId="language-select-label"
                                        id="language-select"
                                        label='Language'
                                        value={field.value}
                                        onChange={field.onChange}
                                    >
                                        {languages.map((lang) => (
                                            <MenuItem key={lang} value={lang}>{lang}</MenuItem>
                                        ))}
                                    </Select>
                                )}
                                name={`xtts.language`}
                                control={control}
                                defaultValue={'en'}
                            />
                        </FormControl>
                    </Stack>
                </Paper>

                <Stack direction="column" spacing={2} margin={2}>

                    <Button variant='outlined' type='submit'>Save</Button>
                </Stack>
            </form>
        </>
    )
}
