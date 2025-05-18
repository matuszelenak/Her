import {Route, Routes} from 'react-router-dom';
import {NewChatRedirect} from "./Pages/NewChatRedirect.tsx";
import {ChatProvider} from "./Pages/ChatProvider.tsx";


function App() {
    return (
        <>
            <Routes>
                <Route path="/" element={<NewChatRedirect/>}/>
                <Route path="/chat/:chatId" element={<ChatProvider/>}/>
            </Routes>
        </>
    )
}

export default App
