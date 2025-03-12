import { Route, Routes } from 'react-router-dom';
import { Chat } from "./Pages/Chat.tsx";


function App() {
    return (
        <>
            <Routes>
                <Route path="/" element={<Chat/>}/>
                <Route path="/chat/:chatId" element={<Chat/>}/>
            </Routes>
        </>
    )
}

export default App
