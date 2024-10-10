import {Controller, useForm} from "react-hook-form"
import {Configuration, OllamaModel} from "../types.ts";
import {
    Button,
    CircularProgress,
    FormControl,
    InputLabel,
    MenuItem,
    Select,
    Slider,
    Stack,
    TextField
} from "@mui/material";
import {useMutation, useQuery} from "@tanstack/react-query";
import {axiosDefault} from "../api.ts";

type ConfigFormProps = {
    chatId: string
}

export const ConfigForm = (props: ConfigFormProps) => {

    const {
        register,
        handleSubmit,
        clearErrors,
        setValue,
        getValues,
        control,
        formState: {errors},
    } = useForm<Configuration>({
        defaultValues: {
            ollama: {
                model: '',
                temperature: 0.5,
                repeat_penalty: 1,
                ctx_length: 8192,
                system_prompt: ''
            }
        }
    })

    const {data: config} = useQuery({
        queryKey: ['config'],
        queryFn: async () => axiosDefault({
            url: `/config/${props.chatId}`,
            method: 'get'
        }).then(({data}: {data: Configuration}) => {
            setValue('ollama', data.ollama)
            // setValue('ollama.model', data.ollama.model)
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

    const configMutation = useMutation({
        mutationFn: async (data: Configuration) => await axiosDefault({
            url: `/config/${props.chatId}`,
            method: 'POST',
            data: {

                ...config,
                ollama: data.ollama,
            }
        })
    })

    if (!models || !config) {
        return <CircularProgress/>
    }

    return (
        <>
            <form onSubmit={handleSubmit((data) => configMutation.mutate(data))}>
                <Stack direction="column" spacing={2} margin={4}>
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
                                    { models.map(({name, model}) => (
                                        <MenuItem key={name} value={model}>{name}</MenuItem>
                                    )) }
                                </Select>
                            )}
                            name={`ollama.model`}
                            control={control}
                            defaultValue={'mistral-nemo:12b-instruct-2407-q8_0'}
                        />
                    </FormControl>
                    <TextField
                        {...register('ollama.system_prompt')}
                    />
                    <FormControl>
                        <InputLabel>Context length</InputLabel>
                        <Controller
                            render={({field}) => (
                                <Slider step={1024} value={field.value} onChange={field.onChange} min={1024} max={32768} valueLabelDisplay="on"/>
                            )}
                            name={`ollama.ctx_length`}
                            control={control}
                        />
                    </FormControl>
                    <FormControl>
                        <InputLabel>Temperature</InputLabel>
                        <Controller
                            render={({field}) => (
                                <Slider step={0.05} value={field.value} onChange={field.onChange} min={0} max={1} valueLabelDisplay="on"/>
                            )}
                            name={`ollama.temperature`}
                            control={control}
                        />
                    </FormControl>
                    <FormControl>
                        <InputLabel>Repeat penalty</InputLabel>
                        <Controller
                            render={({field}) => (
                                <Slider step={0.1} value={field.value} onChange={field.onChange} min={0} max={1.5} valueLabelDisplay="on"/>
                            )}
                            name={`ollama.repeat_penalty`}
                            control={control}
                        />
                    </FormControl>
                    <Button variant='outlined' type='submit'>Save</Button>
                </Stack>
            </form>

        </>
    )
}
