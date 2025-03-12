import { ChatConfiguration } from "../types.ts";
import {
    Box,
    Button,
    CircularProgress,
    FormControl,
    Grid,
    Input,
    InputLabel,
    MenuItem,
    Paper,
    Select,
    Slider,
    Stack,
    Typography
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { axiosDefault } from "../api.ts";
import { Dispatch, SetStateAction, useEffect, useState } from "react";
import { useServiceHealth } from "../hooks/useServiceHealth.ts";


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
    const [voice, setVoice] = useState(config.tts.voice)
    // const [xttsLang, setXttsLang] = useState(config.tts.language)

    const status = useServiceHealth()

    useEffect(() => {
        setVoice(config.tts.voice)
        // setXttsLang(config.tts.language)
    }, [config]);

    const {data: voices} = useQuery({
        queryKey: ['voices'],
        queryFn: async () => axiosDefault({
            url: '/voices',
            method: 'get'
        }).then(({data}) => data as string[]),
        enabled: status.tts == 'healthy',
        initialData: []
    })

    if (!voices) {
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
