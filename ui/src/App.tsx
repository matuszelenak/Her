import { Route, Routes } from 'react-router-dom';
import { Chat } from "./Pages/Chat.tsx";
import { Test } from './Pages/Test.tsx';

function App() {
    return (
        <>
            <Routes>
                <Route path="/" element={<Chat/>}/>
                <Route path="/chat/:chatId" element={<Chat/>}/>
                <Route path='/test' element={<Test/>}/>
            </Routes>
        </>
    )
}

export default App
