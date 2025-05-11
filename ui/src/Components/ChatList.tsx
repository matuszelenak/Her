import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { axiosDefault } from "../api.ts";
import { IconButton, Stack, Typography } from "@mui/material";
import { NavLink, useNavigate, useParams } from "react-router-dom";
import { Delete } from "@mui/icons-material";

export type ChatsResponse = {
    id: string
    header: string
}[]

export const ChatList = () => {
    const queryClient = useQueryClient()
    const navigate = useNavigate()
    const {chatId} = useParams<string>();


    const {data: chats} = useQuery({
        queryKey: ['chat_list'],
        queryFn: async () => axiosDefault({
            url: '/chats',
            method: 'get'
        }).then(({data}) => data as ChatsResponse),
        initialData: []
    })

    const deleteMutation = useMutation({
        mutationFn: async (chatId: string) => axiosDefault({
            url: `/chat/${chatId}`,
            method: "delete"
        }),
        onSuccess: async ({data}) => {
            await queryClient.invalidateQueries({queryKey: ['chat_list']})
            if (data.id == chatId) {
                navigate('/')
            }
        }
    })

    return (
        <Stack direction="column" spacing={2} padding={2}>
            <NavLink
                style={{textDecoration: 'none'}}
                key={'new'}
                to={`/`}
            >
                <Typography variant="h5">New chat</Typography>
            </NavLink>
            {chats.map((chat) => (
                <Stack
                    direction="row"
                    alignContent="center"
                    key={chat.id}
                    justifyContent="space-between"
                    sx={{
                        padding: 1,
                        border: 2,
                        borderColor: 'darkgrey',
                        maxWidth: 300
                    }}
                >
                    <NavLink
                        style={{textDecoration: 'none', margin: 0, padding: 0}}
                        key={chat.id}
                        to={`/chat/${chat.id}`}
                    >
                        <Typography variant="h5">{chat.header}</Typography>
                    </NavLink>
                    <IconButton onClick={() => deleteMutation.mutate(chat.id)}>
                        <Delete/>
                    </IconButton>
                </Stack>
            ))}
        </Stack>
    )
}
