import {Route, Routes} from 'react-router-dom';
import {ChatProvider} from "./Components/ChatProvider.tsx";
import {Chat} from "./Pages/Chat.tsx";

function App() {
    return (
        <>
            <Routes>
                <Route path="/" element={<Chat/>}/>
                <Route path="/chat/:chatId" element={<ChatProvider/>}/>
            </Routes>
        </>
    )
}

export default App
