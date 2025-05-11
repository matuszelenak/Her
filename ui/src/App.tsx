import { Route, Routes } from 'react-router-dom';
import { Chat } from "./Pages/Chat.tsx";
import {NewChatRedirect} from "./Pages/NewChatRedirect.tsx";


function App() {
    return (
        <>
            <Routes>
                <Route path="/" element={<NewChatRedirect/>}/>
                <Route path="/chat/:chatId" element={<Chat/>}/>
            </Routes>
        </>
    )
}

export default App
