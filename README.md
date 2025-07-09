# Her - a fully self-hosted voice assistant

The aim of this project is to provide an orchestration/communication platform for various open-source components that come together to form a low-latency conversational voice assistant capable of tool use.

We leverage (at this point) quite rich ecosystem of Speech-to-text (STT), Large language (LLM) and Text-to-speech (TTS) models with corresponding inference engines to form a comprehensive software stack capable of seamlessly interacting with a user without ever needing to send any data to external services.

## Dependencies

As new and better models/frameworks are released on monthly, sometimes weekly basis, we try to provide support for the most promising ones.

### STT

- [Whisper]()
- [Parakeet]()

### LLM

Any provider with an OpenAI spec API will suffice, though in the future we will migrate to a custom API
  
### TTS
- [Kokoro TTS]() through [Kokoro FastAPI](https://github.com/remsky/Kokoro-FastAPI)
- [Orpheus TTS]() through [Orpheus FastAPI](https://github.com/Lex-au/Orpheus-FastAPI/issues)
- [Chatterbox TTS]() through [Chatterbox TTS API](https://github.com/travisvn/chatterbox-tts-api)
- [XTTS2]() through [Alltalk](https://github.com/erew123/alltalk_tts)

## Project structure
There are three modules:
- Assistant - this FastAPI module houses the LLM agent\[s\] code and prompts, as well as tools and MCP servers connections. It exposes an OpenAI spec `/completions` endpoint.
- Server - This is the "glue" of the entire project. The FastAPI server accepts websocket connections from a web browser client, receives users voice audio samples, passes them to the STT engine, submits the received transcription to an LLM, pipes the LLM output to TTS and streams the synthesized speech back to the user. It does all of this in an asynchronous manner leveraging streaming whenever the particular engine implements it.
- UI - A browser UI capable of both recording and playing back audio, utilizing [Silero VAD] for speech recognition.

## Configuration

### Assistant

Env variables:

- `OPENAI_API_URL` - a URL to an OpenAI spec API, e.g. `http://10.0.0.2:8000/v1`
- `OPENAI_MODEL`- a valid model name served on the API , e.g. `Qwen/Qwen3-32B-AWQ`
- `LOGFIRE_TOKEN` - optional, a token to Logfire API for monitoring
- `TAVILY_API_TOKEN` - optional, token to Tavily API to enable web search tool

### Server

Env variables:

- `WHISPER_API_URL` - e.g. http://10.0.0.2:9090
- `ASSISTANT_API_URL` - e.g.  http://assistant:8001/v1
- `KOKORO_API_URL` e.g. http://10.0.0.2:8880
- `ORPHEUS_API_URL` e.g. http://10.0.0.2:5005
- `CHATTERBOX_API_URL` e.g. http://10.0.0.2:4123

JSON configuration
```json
{
  "stt": {
    "provider": "whisper", # right now, only whisper is supported
    "model": "medium.en",
    "language": "en"
  },
  "tts": {
    "provider": "chatterbox", # One of [chatterbox, orpheus, kokoro]
    "voice": "nichalia_schwartz" # For kokoro and orpheus, see available voices in their provider code file, for chatterbox specify one from voices folder
  },
  "app": {
    "prevalidate_prompt": true, # Whether the user speech should be checked for validity (time since last interaction)
    "inactivity_timeout_ms": 30000, # How long to wait in ms  before a wake phrase is required
    "voice_input_enabled": true, 
    "voice_output_enabled": true
  }
}

```

### Shared
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `POSTGRES_HOST`
- `POSTGRES_PORT`

## Running the project

### Dev setup
Make sure to copy the `.env.example` as `.env`,`server/.env.example` to `server/.env` and `assistant/.env.example` to `assistant/.env` and fill the correct values for the various dependency API addresses and database connection
Run `docker compose up --build` in the root of the project

### Prod setup

Ensure `.env` file content as with dev setup, but run `docker compose -f docker-compose.prod.yaml up`
