import { Box, Button, Grid, Input, Paper, Slider, Stack, Typography } from "@mui/material";
import { Dispatch, SetStateAction } from "react";
import { useServiceHealth } from "../hooks/useServiceHealth.ts";


export const DependencyToolbar = (
    {
        vad, speech
    }: {
        vad: { listening: boolean, toggle: () => void },
        speech: {
            speaking: boolean,
            toggleSpeaking: () => void,
            confirmDelay: number,
            setConfirmDelay: Dispatch<SetStateAction<number>>
        }
    }
) => {
    const status = useServiceHealth()

    return (
        <>
            <Paper elevation={1} sx={{padding: 2, margin: 2}}>
                <Stack direction="row" justifyContent="space-between">
                    <Typography variant="h6">Whisper</Typography>
                    <Button disabled={status.stt !== 'healthy'} variant="outlined" onClick={() => {
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
                                    disabled={status.stt !== 'healthy'}
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
                    <Typography variant="h6">TTS</Typography>
                    <Button variant="outlined" disabled={status.tts !== 'healthy'} onClick={() => {
                        speech.toggleSpeaking()
                    }}>
                        {speech.speaking ? "Disable speech" : "Enable speech"}
                    </Button>
                </Stack>
            </Paper>
        </>
    )
}
