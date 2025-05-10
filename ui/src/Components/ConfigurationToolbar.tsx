import {
    Box,
    Button,
    FormControl,
    Input,
    InputLabel,
    ListItemText,
    MenuItem,
    OutlinedInput,
    Paper,
    Select,
    Slider,
    Stack,
    Typography
} from "@mui/material";
import {useServiceHealth} from "../hooks/useServiceHealth.ts";
import {Configuration} from "../types.ts";
import Grid from "@mui/material/Grid2";
import {useQuery} from "@tanstack/react-query";
import {axiosDefault} from "../api.ts";
import {useDelayedInput} from "../hooks/useDelayedInput.ts";
import {useEffect} from "react";


type ConfigurationToolbarProps = {
    config: Configuration
    setConfigField: (path: string, value: unknown) => void
}


export const ConfigurationToolbar = ({config, setConfigField}: ConfigurationToolbarProps) => {
    const status = useServiceHealth()

    const [delay, setDelayRT, delayRT] = useDelayedInput(config.app.after_user_speech_confirmation_delay_ms, 300)

    const {data: voices} = useQuery({
        queryKey: ['voices', config.tts.provider],
        queryFn: async () => axiosDefault({
            url: `/voices/${config.tts.provider}`,
            method: 'get'
        }).then(({data}) => {
            return data as string[]
        })
    })

    useEffect(() => {
        if (delay != config.app.after_user_speech_confirmation_delay_ms) {
            setConfigField('app.after_user_speech_confirmation_delay_ms', delay)
        }
    }, [delay, setConfigField, config.app.after_user_speech_confirmation_delay_ms]);

    return (
        <>
            <Paper elevation={1} sx={{padding: 2, margin: 2}}>
                <Stack direction="row" justifyContent="space-between">
                    <Typography variant="h6">Speech-to-text</Typography>
                    <Button disabled={status[config.stt.provider] !== 'healthy'} variant="outlined" onClick={() => {
                        setConfigField('app.voice_input_enabled', !config.app.voice_input_enabled)
                    }}>
                        {config.app.voice_input_enabled ? "Stop listening" : "Start listening"}
                    </Button>
                </Stack>

                <Stack direction='column' spacing={2} marginTop={1}>
                    <Box>
                        <Typography id="input-slider" gutterBottom>
                            After speech confirm delay
                        </Typography>
                        <Grid container spacing={2} sx={{alignItems: 'center'}}>
                            <Grid size={{md: 6}}>
                                <Slider
                                    min={200}
                                    max={4000}
                                    step={50}
                                    disabled={status[config.stt.provider] !== 'healthy'}
                                    value={delayRT}
                                    onChange={(_: Event, newValue: number | number[]) =>
                                        setDelayRT(newValue as number)
                                    }
                                />
                            </Grid>
                            <Grid size={{md: 6}}>
                                <Input
                                    size="small"
                                    value={delayRT}
                                    onChange={(event) => {
                                        setDelayRT(event.target.value as unknown as number)
                                    }}
                                    disabled={status[config.stt.provider] !== 'healthy'}
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
                <Stack direction="column">
                    <Stack direction="row" justifyContent="space-between" sx={{margin: 1}}>
                        <Typography variant="h6">Text-to-speech</Typography>
                        <Button variant="outlined" disabled={status[config.tts.provider] !== 'healthy'} onClick={() => {
                            setConfigField('app.voice_output_enabled', !config.app.voice_output_enabled)
                        }}>
                            {config.app.voice_output_enabled ? "Disable speech" : "Enable speech"}
                        </Button>
                    </Stack>
                    <FormControl>
                        <InputLabel id="voices">
                            Voice
                        </InputLabel>
                        { voices &&
                            <Select
                                variant={'outlined'}
                                labelId="voices"
                                disabled={status[config.tts.provider] !== 'healthy'}
                                value={config.tts.voice}
                                onChange={(e) => setConfigField('tts.voice', e.target.value)}
                                input={<OutlinedInput label={'Voice'}/>}
                            >
                                { (voices).map(voice => (
                                    <MenuItem key={voice} value={voice}>
                                        <ListItemText primary={voice}/>
                                    </MenuItem>
                                )) }
                            </Select>
                        }

                    </FormControl>
                </Stack>
            </Paper>
        </>
    )
}
