# ADR-005: Voice I/O as External Layer

**Status:** Draft
**Date:** 2026-07-26
**Project:** Synapsis

---

## Context

Synapsis supports voice input (speech-to-text) and voice output (text-to-speech).
During design, we considered making these agent capabilities — the Orchestrator
could "speak" results, or a dedicated VoiceAgent could handle the full pipeline.

We needed to decide: is voice an agent behavior or an I/O adapter?

## Decision

Voice is an **I/O adapter layer**, not part of the agent system.

- **Voice Listener:** Audio input → transcribed text. Adapter, not agent.
- **Voice Speaker:** Text → audio output. Adapter, not agent.
- **Text is the canonical format** inside the system. Agents never see audio.

### Rationale

The agent system operates on text. The Orchestrator receives a text query and
produces a text response. Whether that text came from a keyboard or a microphone
is irrelevant to the agents' decision-making.

Voice I/O is a modality adapter — like a GUI or a CLI. Making it an agent would
couple the reasoning system to a specific input format, making it harder to add
new modalities later (web UI, chat interface, API).

### Pipeline

[Microphone] → Listener (Whisper) → text → Orchestrator → ... → Scribe → text
│
┌──────────┘
▼
[Speaker] ← voice_script ← Scribe
│
[Audio out]


### Technology Choices

| Component | Local (Offline) | Cloud (API) |
|-----------|-----------------|-------------|
| STT | Whisper (local model) | Whisper API |
| TTS | Piper TTS (local) | ElevenLabs API |

The system defaults to local models for portfolio-friendliness (no API costs for
reviewers). Cloud APIs are configurable via environment variables.

## Alternatives Considered

### Option A: VoiceAgent that handles all voice logic
A dedicated agent that receives audio, transcribes, and decides how to respond.
Rejected: Transcription is a mechanical process, not a decision. An agent implies
choice — "should I transcribe this?" is not a meaningful decision.

### Option B: Voice as a tool on the Orchestrator
Orchestrator has `speak()` and `listen()` tools.
Rejected: Bloats Orchestrator with modality concerns. The Orchestrator should
reason about tasks, not audio codecs.

### Option C: Voice as external adapter layer (chosen)
Clean separation: agents reason in text, adapters handle modality conversion.
Easy to swap Whisper for another STT engine. Easy to add a web UI later without
touching agent code.

## Consequences

Easier:
- Testing: agents can be tested with text input, no audio files needed
- Swapping: change STT/TTS engines without touching agent logic
- Extending: add a web UI or chat interface — same agent system, different adapters

Harder:
- Voice-specific features (tone detection, emotion) would require adapter changes
- Real-time streaming voice I/O (interruptions, VAD) is more complex than
  the current push-to-talk model (deferred to future work)

Risks:
- Low. The separation is clean and the current scope (push-to-talk, not continuous
  conversation) maps well to a simple adapter pattern.

## References
- OpenAI Whisper: https://github.com/openai/whisper
- Piper TTS: https://github.com/rhasspy/piper
- ADR-001: System Architecture