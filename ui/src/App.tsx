import './App.css'
import useWebSocket from "react-use-websocket";
import {useAudioPlayer} from "./utils/audioPlayer.ts";
import {useAudioRecorder} from "./utils/audioRecorder.ts";
import {markdownLookBack} from "@llm-ui/markdown";
import {type LLMOutputComponent, throttleBasic, useLLMOutput} from "@llm-ui/react";
import {
    allLangs,
    allLangsAlias,
    codeBlockLookBack,
    CodeToHtmlOptions,
    findCompleteCodeBlock,
    findPartialCodeBlock,
    loadHighlighter,
    useCodeBlockToHtml,
} from "@llm-ui/code";
import remarkGfm from "remark-gfm";
import ReactMarkdown from "react-markdown";
import parseHtml from "html-react-parser";
import {useState} from "react";
import {bundledLanguagesInfo, bundledThemes, getHighlighterCore} from "shiki";
import getWasm from "shiki/wasm";


const MarkdownComponent: LLMOutputComponent = ({blockMatch}) => {
    const markdown = blockMatch.output;
    return (
        <ReactMarkdown className={"markdown"} remarkPlugins={[remarkGfm]}>
            {markdown}
        </ReactMarkdown>
    );
};


const highlighter = loadHighlighter(
    getHighlighterCore({
        langs: allLangs(bundledLanguagesInfo),
        langAlias: allLangsAlias(bundledLanguagesInfo),
        themes: Object.values(bundledThemes),
        loadWasm: getWasm,
    }),
);

const codeToHtmlOptions: CodeToHtmlOptions = {
    theme: "github-dark",
};

// Customize this component with your own styling
const CodeBlock: LLMOutputComponent = ({blockMatch}) => {
    const {html, code} = useCodeBlockToHtml({
        markdownCodeBlock: blockMatch.output,
        highlighter,
        codeToHtmlOptions,
    });
    if (!html) {
        // fallback to <pre> if Shiki is not loaded yet
        return (
            <pre className="shiki">
        <code>{code}</code>
      </pre>
        );
    }
    return <>{parseHtml(html)}</>;
};


const throttle = throttleBasic({
    readAheadChars: 10,
    targetBufferChars: 7,
    adjustPercentage: 0.35,
    frameLookBackMs: 10000,
    windowLookBackMs: 2000,
});


function App() {
    const audioContext = new AudioContext();
    const {audioNode} = useAudioPlayer(audioContext)

    const {
        sendMessage,
    } = useWebSocket(
        `${window.location.protocol == "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws/totallyrandom`,
        {
            onMessage: (event: WebSocketEventMap['message']) => {
                const message = JSON.parse(event.data)

                if (message.type == 'speech') {
                    audioNode?.port?.postMessage({message: 'audioData', audioData: new Float32Array(message.samples)});
                }

                if (message.type == 'token') {
                    if (message.token === null) {
                        console.log(message)
                        setIsStreamFinished(true)
                    } else {
                        setIsStreamFinished(false)
                        setLLMOutput((prevState) => {
                            return `${prevState}${message.token}`
                        })
                    }
                }

                if (message.type == 'stt_output') {
                    console.log(message)
                    setLLMOutput((prevState) => {
                        return `${prevState}\n\n**${message.text}**\n\n`
                    })
                }
            },
            reconnectAttempts: 1000,
            reconnectInterval: 2000
        }
    );

    useAudioRecorder((buffer: ArrayBuffer) => {
        sendMessage(buffer)
    })

    const [llmOutput, setLLMOutput] = useState("")
    const [isStreamFinished, setIsStreamFinished] = useState(false)

    const {blockMatches} = useLLMOutput({
        llmOutput: llmOutput,
        fallbackBlock: {
            component: MarkdownComponent,
            lookBack: markdownLookBack(),
        },
        blocks: [
            {
                component: CodeBlock,
                findCompleteMatch: findCompleteCodeBlock(),
                findPartialMatch: findPartialCodeBlock(),
                lookBack: codeBlockLookBack(),
            },
        ],
        throttle: throttle,
        isStreamFinished
    });

    return (
        <>
            <div>
                {blockMatches.map((blockMatch, index) => {
                    const Component = blockMatch.block.component;
                    return <Component key={index} blockMatch={blockMatch}/>;
                })}
            </div>
        </>
    )
}

export default App
