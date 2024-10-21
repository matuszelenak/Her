# AI assistant project

This projects implements a backend glue that binds a speech-to-text, text-to-speech and LLM into a voice assistant 
that will eventually, hopefully be useful.
Also included is a React SPA to interface with it via browser.

## Dependencies

### Ollama

Install Ollama: https://ollama.com/

### Alltalk

Install Alltalk: https://github.com/erew123/alltalk_tts

## Running

### Dev setup
Make sure to copy the `.env.example` as `.env` and fill the correct values for the various dependency API addresses and database connection
Run `docker compose up` in the root of the project

### Prod setup

Ensure `.env` file content as with dev setup, but run `docker compose -f docker-compose.prod.yaml up`
