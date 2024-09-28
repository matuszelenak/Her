import {Route, Routes} from 'react-router-dom';
import {ChatProvider} from "./Components/ChatProvider.tsx";
import {NewChatRedirect} from "./Components/NewChatRedirect.tsx";

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
