import { ChatConfiguration, OllamaModel } from "../types.ts";
import {
    Box,
    Button,
    Checkbox,
    CircularProgress,
    FormControl,
    Grid,
    Input,
    InputLabel,
    ListItemText,
    MenuItem,
    OutlinedInput,
    Paper,
    Select,
    Slider,
    Stack,
    TextField,
    Typography
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { axiosDefault } from "../api.ts";
import { Dispatch, SetStateAction, useEffect, useState } from "react";
import { useDelayedInput } from "../utils/useDelayedInput.ts";
import { useServiceHealth } from "../hooks/useServiceHealth.ts";


// const languages = ['cs', 'en']


export const DependencyToolbar = ({
                                      config, vad, speech, setConfigValue
                                  }: {
    config: ChatConfiguration
    setConfigValue: (field: string, value: any) => void
    vad: { listening: boolean, toggle: () => void },
    speech: {
        speaking: boolean,
        toggleSpeaking: () => void,
        confirmDelay: number,
        setConfirmDelay: Dispatch<SetStateAction<number>>
    }
}) => {
    const [model, setModel] = useState(config.ollama.model)
    const [temperature, rtTemperature, setRTTemperature] = useDelayedInput<number | null>(config.ollama.temperature, 200)
    const [repeatPenalty, rtRepeatPenalty, setRTRepeatPenalty] = useDelayedInput<number | null>(config.ollama.repeat_penalty, 200)
    const [ctxLength, rtCtxLength, setRTCtxLength] = useDelayedInput<number | null>(config.ollama.ctx_length, 200)
    const [sysPrompt, rtSystemPrompt, setRTSystemPrompt] = useDelayedInput<string | null>(config.ollama.system_prompt, 200)
    const [tools, setTools] = useState<string[]>(config.ollama.tools)
    const [voice, setVoice] = useState(config.tts.voice)
    // const [xttsLang, setXttsLang] = useState(config.tts.language)

    const status = useServiceHealth()

    useEffect(() => {
        setModel(config.ollama.model)
        setRTTemperature(config.ollama.temperature)
        setRTRepeatPenalty(config.ollama.repeat_penalty)
        setRTCtxLength(config.ollama.ctx_length)
        setRTSystemPrompt(config.ollama.system_prompt)
        setTools(config.ollama.tools)

        setVoice(config.tts.voice)
        // setXttsLang(config.tts.language)
    }, [config]);


    useEffect(() => {
        if (temperature !== null) {
            setConfigValue('ollama.temperature', temperature)
        }
    }, [temperature]);

    useEffect(() => {
        if (ctxLength !== null) {
            setConfigValue('ollama.ctx_length', ctxLength)
        }
    }, [ctxLength]);

    useEffect(() => {
        if (repeatPenalty !== null) {
            setConfigValue('ollama.repeat_penalty', repeatPenalty)
        }
    }, [repeatPenalty]);

    useEffect(() => {
        if (sysPrompt !== null) {
            setConfigValue('ollama.system_prompt', sysPrompt)
        }
    }, [sysPrompt]);

    const {data: models} = useQuery({
        queryKey: ['models'],
        queryFn: async () => axiosDefault({
            url: '/models',
            method: 'get'
        }).then(({data}) => data as OllamaModel[]),
    })

    const {data: voices} = useQuery({
        queryKey: ['voices'],
        queryFn: async () => axiosDefault({
            url: '/voices',
            method: 'get'
        }).then(({data}) => data as string[]),
        enabled: status.tts == 'healthy',
        initialData: []
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
                    <Button disabled={!status.stt} variant="outlined" onClick={() => {
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
                                    disabled={!status.stt}
                                    value={speech.confirmDelay}
                                    onChange={(_: Event, newValue: number | number[]) => speech.setConfirmDelay(newValue as number)}
                                />
                            </Grid>
                            <Grid item>
                                <Input
                                    size="small"
                                    value={speech.confirmDelay}
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

                {status.llm !== null && <Stack direction='column' spacing={2} marginTop={1}>
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
                                setConfigValue('ollama.model', e.target.value)
                            }}
                        >
                            <MenuItem key={'none'} value={'none'}></MenuItem>
                            {models.map(({model}) => (
                                <MenuItem key={model}
                                          value={model}>{status.llm?.includes(model) ? '[loaded]' : ''} {model}</MenuItem>
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
                                setConfigValue('ollama.tools', e.target.value)
                            }}
                            input={<OutlinedInput label="Tools"/>}
                            renderValue={(selected) => selected.join(', ')}
                        >
                            {toolChoices.map((name) => (
                                <MenuItem key={name} value={name}>
                                    <Checkbox checked={tools.includes(name)}/>
                                    <ListItemText primary={name}/>
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </Stack>}
            </Paper>

            <Paper elevation={1} sx={{padding: 2, margin: 2}}>
                <Stack direction="row" justifyContent="space-between" sx={{margin: 1}}>
                    <Typography variant="h6">XTTS</Typography>
                    <Button variant="outlined" disabled={!status.tts} onClick={() => {
                        speech.toggleSpeaking()
                    }}>
                        {speech.speaking ? "Disable speech" : "Enable speech"}
                    </Button>
                </Stack>

                {status.tts && <Stack direction='column' spacing={2} marginTop={1}>
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
                                setConfigValue('tts.voice', e.target.value)
                            }}
                        >
                            {voices.map((voice) => (
                                <MenuItem key={voice} value={voice}>{voice}</MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    {/*<FormControl>*/}
                    {/*    <InputLabel id="language-select-label">Language</InputLabel>*/}
                    {/*    <Select*/}
                    {/*        sx={{minWidth: 300}}*/}
                    {/*        variant='outlined'*/}
                    {/*        labelId="language-select-label"*/}
                    {/*        id="language-select"*/}
                    {/*        label='Language'*/}
                    {/*        value={xttsLang}*/}
                    {/*        onChange={(e) => {*/}
                    {/*            setXttsLang(e.target.value as 'en' | 'cs')*/}
                    {/*            setConfigValue('tts.language', e.target.value)*/}
                    {/*        }*/}
                    {/*        }*/}
                    {/*    >*/}
                    {/*        {languages.map((lang) => (*/}
                    {/*            <MenuItem key={lang} value={lang}>{lang}</MenuItem>*/}
                    {/*        ))}*/}
                    {/*    </Select>*/}
                    {/*</FormControl>*/}
                </Stack>}
            </Paper>
        </>
    )
}
