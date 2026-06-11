# Voice Agents

Research notebooks exploring real-time voice agent architecture built on [LiveKit Agents](https://docs.livekit.io/agents/).

## Pipeline

```
Microphone → VAD (Silero) → STT (OpenAI Whisper) → LLM (GPT-4o) → TTS (ElevenLabs) → Speaker
```

Each stage is independently configurable and replaceable — swap the STT provider, change the TTS voice, or substitute the LLM without touching the rest of the pipeline.

## Notebooks

### 1. [Voice Agent Components](Voice%20Agent%20Components.ipynb)

Builds and explains each component of the voice pipeline end-to-end.

Topics covered:
- Real-time audio transport via LiveKit / WebRTC
- Voice Activity Detection (VAD) to gate speech recognition and avoid hallucinated transcriptions
- Streaming STT → LLM → TTS for low-latency response
- Voice persona selection with ElevenLabs voices
- Prompt engineering constraints specific to voice (no markdown, short sentences, no lists)

### 2. [Optimizing Latency](Optimizing%20Latency.ipynb)

Instruments each pipeline stage to measure, isolate, and reduce end-to-end latency.

**Metrics tracked:** `EOU Delay · Transcription Delay · LLM TTFT · Tokens/s · TTS TTFB`

Topics covered:
- Event-driven metrics collection using `livekit.agents.metrics`
- Per-turn latency breakdown across all four stages
- Identifying the dominant bottleneck from session summaries
- A/B model comparison via `LLM_MODEL` env var (`gpt-4o` vs `gpt-4o-mini`)
- Optimisation strategies: VAD tuning, streaming STT, faster TTS encodings, smaller models

## Setup

### 1. Install dependencies

From the repo root:

```bash
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
```

Edit `.env`:

```
OPENAI_API_KEY=sk-...        # https://platform.openai.com/api-keys
ELEVEN_API_KEY=...           # https://elevenlabs.io → Profile → API Key
```

> `ELEVENLABS_API_KEY` is also accepted as an alias for `ELEVEN_API_KEY`.

### 3. Run the notebooks

Open either notebook in JupyterLab and run all cells top to bottom.

## Files

| File | Description |
|------|-------------|
| `Voice Agent Components.ipynb` | Full pipeline walkthrough |
| `Optimizing Latency.ipynb` | Latency instrumentation and optimisation |
| `images/` | Architecture diagrams referenced in the notebooks |
