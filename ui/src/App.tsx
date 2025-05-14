import { Route, Routes } from 'react-router-dom';
import { Chat } from "./Pages/Chat.tsx";
import {NewChatRedirect} from "./Pages/NewChatRedirect.tsx";
import {WebSocketAudioPlayer} from "./Pages/Test.tsx";


function App() {
    return (
        <>
            <Routes>
                <Route path="/" element={<NewChatRedirect/>}/>
                <Route path="/chat/:chatId" element={<Chat/>}/>
                <Route path="/test" element={<WebSocketAudioPlayer/>}/>
            </Routes>
        </>
    )
}

export default App
