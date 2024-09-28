import { v4 as uuidv4 } from 'uuid';
import {Navigate} from "react-router-dom";

export const NewChatRedirect = () => {
    const newChatId = uuidv4();

    return <Navigate to={`chat/${newChatId}`}/>
}