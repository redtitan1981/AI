# Voice Agents

Research notebooks exploring real-time voice agent architecture: how to chain VAD, STT, LLM, and TTS into a low-latency conversational pipeline, and how to measure and systematically reduce latency at each stage.

---

## Research Question

> What is the minimum achievable end-to-end latency for a streaming voice pipeline built on commodity cloud APIs, and which stage dominates the budget?

**End-to-end latency** = time from the user stopping speaking to audio starting to play back. A natural conversation target is under 1.5 seconds. The pipeline has four independently optimisable stages, each with its own latency contribution.

---

## Pipeline

```
User speaks
    |
    v
VAD (Silero)               ← runs locally, ~0ms overhead
    | speech detected
    v
STT (OpenAI Whisper)       ← streaming transcription, EOU delay + transcription delay
    | transcript
    v
LLM (GPT-4o)               ← generation, TTFT + tokens/s
    | token stream
    v
TTS (ElevenLabs)           ← synthesis, TTFB + streaming audio
    |
    v
Speaker plays audio
```

Each stage is independently configurable. You can swap the STT provider (e.g. Deepgram for lower latency), the LLM (e.g. `gpt-4o-mini` to reduce TTFT), or the TTS voice without touching the rest of the pipeline.

### Stage-by-stage breakdown

| Stage | Component | Key latency metric | Typical range |
|-------|-----------|-------------------|---------------|
| VAD | Silero (local) | Detection delay | < 50ms |
| STT | OpenAI Whisper | EOU delay + transcription | 200–800ms |
| LLM | GPT-4o | Time to First Token (TTFT) | 300–700ms |
| TTS | ElevenLabs | Time to First Byte (TTFB) | 200–500ms |

**EOU (End of Utterance):** The delay between the user stopping speaking and VAD confirming silence. Tuning VAD sensitivity directly controls this.

**TTFT (Time to First Token):** How long the LLM takes to start generating. Shorter prompts and smaller models reduce TTFT.

**TTFB (Time to First Byte):** How long TTS takes before audio starts streaming. ElevenLabs supports chunk-level streaming — audio plays before the full response is synthesised.

---

## Notebooks

### 1. [Voice Agent Components](Voice%20Agent%20Components.ipynb)

Builds and explains each component of the voice pipeline from scratch, then wires them together into a working agent using LiveKit Agents.

**Topics covered:**

**LiveKit / WebRTC transport**
- How LiveKit manages real-time audio rooms and tracks
- Why WebRTC is used instead of HTTP for voice (sub-100ms transport, NAT traversal)
- `VoicePipelineAgent` as the orchestrator that connects all four stages

**Voice Activity Detection (VAD)**
- Why VAD is the first stage — it gates everything downstream
- Silero VAD: a small, local neural network that runs at ~30ms/chunk
- Tuning `min_silence_duration` to balance EOU delay vs. false positives (cutting off a speaker mid-sentence)
- How VAD prevents hallucinated STT transcriptions when no one is speaking

**Speech-to-Text (STT)**
- Streaming vs. batch transcription — why streaming matters for latency
- `openai.STT` plugin: sends audio chunks to Whisper as the user speaks
- How punctuation and language hints improve accuracy

**LLM**
- Using `openai.LLM` with streaming enabled — TTS can begin on the first token
- Voice-specific prompt engineering:
  - No markdown (the TTS will read `**bold**` aloud)
  - Short, direct sentences (easier for the listener)
  - No lists or headers
  - Acknowledge the user's input before answering

**Text-to-Speech (TTS)**
- `elevenlabs.TTS`: streams synthesised audio chunks back through LiveKit
- Voice persona selection — how voice choice affects perceived personality
- Turbo vs. standard models: faster synthesis vs. higher quality

---

### 2. [Optimizing Latency](Optimizing%20Latency.ipynb)

Instruments each pipeline stage using LiveKit's built-in metrics API to measure per-turn latency, identify the dominant bottleneck, and apply targeted optimisations.

**Metrics collected:**

| Metric | What it measures |
|--------|-----------------|
| `eou_delay` | Time from user stopping → VAD confirming silence |
| `transcription_delay` | Time from VAD trigger → full transcript available |
| `llm_ttft` | Time from transcript → first LLM token |
| `llm_tokens_per_second` | LLM generation throughput |
| `tts_ttfb` | Time from first LLM token → first audio byte |

**Topics covered:**

**Collecting metrics**
- `livekit.agents.metrics` exposes per-turn events for all four stages
- Attaching handlers to `pipeline.on("metrics_collected", handler)`
- Aggregating across turns to get session-level statistics

**Reading the session summary**
- How to identify which stage dominates total latency
- Interpreting percentile distributions (P50 vs P95) — a high P95 indicates occasional stalls, not a throughput problem

**Optimisation strategies by stage**

| Stage | Technique | Typical saving |
|-------|-----------|---------------|
| VAD | Lower `min_silence_duration` (300ms → 200ms) | 100ms EOU reduction |
| STT | Use streaming mode; select a faster model | 100–300ms |
| LLM | Switch to `gpt-4o-mini`; shorten system prompt | 150–400ms TTFT |
| TTS | Use turbo model; stream chunks instead of waiting for full audio | 100–200ms TTFB |

**A/B model comparison**
- Set `LLM_MODEL=gpt-4o-mini` in `.env` and re-run to compare TTFT and quality
- Latency vs. response quality trade-off analysis

---

## Setup

### Prerequisites
- Python 3.11+
- OpenAI API key (Whisper STT + GPT-4o LLM)
- ElevenLabs API key (TTS)
- A LiveKit Cloud account or self-hosted LiveKit server (for the full pipeline; notebooks can run partially without it)

### 1. Install dependencies

From the **repo root** (not `voice agents/`):

```bash
pip install -r requirements.txt
```

The root `requirements.txt` contains all LiveKit, OpenAI, and ElevenLabs packages pinned to compatible versions.

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

Optional — to experiment with different LLM models without changing code:
```
LLM_MODEL=gpt-4o-mini        # default: gpt-4o
```

### 3. Run the notebooks

```bash
jupyter lab
```

Open either notebook and run all cells top to bottom. The notebooks are self-contained — all LiveKit transport is mocked where necessary so cells run without a live room session.

---

## Understanding Latency Targets

A natural conversation feels responsive when the agent replies within ~1.5 seconds. Here is how the budget typically splits:

```
EOU delay           ~250ms    (VAD confirming silence)
STT transcription   ~300ms    (Whisper processing)
LLM TTFT            ~400ms    (GPT-4o first token)
TTS TTFB            ~200ms    (ElevenLabs first audio chunk)
                    ───────
Total               ~1150ms   ← within comfortable range
```

With optimisations (faster models, streaming STT, lower VAD threshold):
```
EOU delay           ~150ms
STT transcription   ~150ms
LLM TTFT            ~200ms    (gpt-4o-mini)
TTS TTFB            ~100ms    (turbo model)
                    ───────
Total               ~600ms    ← near-native feel
```

---

## Files

| File | Description |
|------|-------------|
| `Voice Agent Components.ipynb` | Full pipeline walkthrough — VAD, STT, LLM, TTS, persona |
| `Optimizing Latency.ipynb` | Metrics collection, bottleneck analysis, optimisation strategies |
| `images/voice_agent_architecture.png` | End-to-end pipeline architecture diagram |
| `images/latency_architecture.png` | Per-stage latency breakdown diagram |

---

## Common Issues

**`ELEVEN_API_KEY not set`**
Make sure `.env` is in the **repo root** (`AI/`), not inside `voice agents/`. `load_dotenv()` searches up the directory tree.

**VAD cutting off speech mid-sentence**
Increase `min_silence_duration` in the VAD config. A value of 400–600ms is more conservative but prevents false positives.

**High P95 LLM latency**
Long system prompts increase TTFT. Try trimming the prompt or switching to `gpt-4o-mini` for latency-sensitive use cases.

**TTS audio choppy or delayed**
Ensure streaming is enabled in the ElevenLabs plugin config. Batch mode (waiting for the full response before synthesising) adds 500–1000ms.
