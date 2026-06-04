# AI Research Notebooks

A collection of research notebooks exploring real-time AI agent architectures, with a focus on voice and latency optimization.

---

## Notebooks

### 1. [Voice Agent Components](AI%20research/Voice%20Agent%20Components.ipynb)

Explores the core components of a real-time, voice-enabled AI agent built on the [LiveKit Agents](https://docs.livekit.io/agents/) framework.

**Pipeline:** `VAD (Silero) → STT (OpenAI Whisper) → LLM (GPT-4o) → TTS (ElevenLabs)`

Topics covered:
- Real-time audio transport via LiveKit / WebRTC
- Voice Activity Detection to gate speech recognition
- Streaming STT → LLM → TTS pipeline for low-latency response
- Voice persona selection with ElevenLabs
- Prompt engineering constraints specific to voice interfaces

### 2. [Optimizing Latency](AI%20research/Optimizing%20Latency.ipynb)

Research into techniques for reducing end-to-end latency in AI agent pipelines.

---

## Setup

### Requirements

```bash
pip install -r requirements.txt
```

### API Keys

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-...        # https://platform.openai.com/api-keys
ELEVEN_API_KEY=...           # https://elevenlabs.io → Profile → API Key
```

> `ELEVENLABS_API_KEY` is also accepted as an alias for `ELEVEN_API_KEY`.

---

## Project Structure

```
AI/
├── AI research/
│   ├── Voice Agent Components.ipynb
│   └── Optimizing Latency.ipynb
├── requirements.txt
├── .env.example
└── README.md
```
