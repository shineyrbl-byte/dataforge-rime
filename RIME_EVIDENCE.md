# Rime TTS Integration Evidence

## 1. Overview

Rime is the **primary spoken-output layer** of the Interruptible Travel Operations Voice Agent.

The project uses the official LiveKit Rime TTS integration with HTTP transport. Rime is used in the live end-to-end voice pipeline rather than only as a dependency or optional demonstration component.

## 2. Shipped Rime Configuration

The agent initializes Rime as follows:

```python
tts = rime.TTS(
    model="coda",
    speaker="celeste",
    lang="eng",
    use_websocket=False,
    segment="bySentence",
)
```

**Shipped configuration**

* **Model:** `coda`
* **Speaker:** `celeste`
* **Language:** `eng`
* **Transport:** HTTP
* **Endpoint:** Rime HTTP API endpoint (managed by the official LiveKit Rime integration)
* **Audio format:** PCM
* **Sampling rate:** 22050 Hz
* **Segmentation:** `bySentence`

Credentials are supplied through environment configuration and are not committed to the repository.

## 3. Runtime Voice Pipeline

```text
User microphone
      |
      v
LiveKit WebRTC
      |
      v
Silero VAD
      |
      v
Deepgram STT
      |
      v
Groq LLM
      |
      v
Generation Fence / Turn Controller
      |
      v
Rime TTS
      |
      v
LiveKit audio
      |
      v
User speaker
```

Rime is responsible for generating the spoken response audio. The surrounding application owns speech detection, transcription, reasoning, orchestration, interruption handling, and authoritative state management.

## 4. Live Rime Verification

Rime was verified in the working prototype by generating spoken responses during live browser-based voice interactions.

The generated audio was delivered through the LiveKit audio pipeline and played to the user.

This establishes that Rime is part of the actual runtime voice path rather than being present only in project configuration or documentation.

## 5. Why Voice Is Necessary

The target user is a travel or field-operations coordinator working in a hands-busy environment.

The workflow involves issuing and revising multi-step travel instructions while interacting with external operations such as flight and hotel actions.

A text-only interface would require the user to repeatedly shift attention toward a screen. Voice allows the user to:

* issue travel instructions hands-free,
* interrupt an operation,
* change their intent while the agent is working,
* receive spoken confirmation of the resulting state.

Voice is therefore fundamental to the product workflow rather than an additional UI layer.

## 6. Voice-Specific Engineering Challenge

The primary engineering contribution is the **Monotonic Generation Fence**.

Realtime voice agents perform multiple asynchronous operations simultaneously. When a user interrupts an active request, previously started LLM, tool, or TTS work may still be running.

Simply requesting cancellation is insufficient because cancellation is cooperative and an asynchronous operation may still return after the cancellation request.

The generation fence provides a correctness boundary:

```text
Generation 1
     |
     +--> modify_booking starts
     |
     +--> User interrupts
              |
              v
       Generation 1 invalidated
              |
              v
       New generation becomes active
              
Generation 1 operation eventually returns
              |
              v
       Generation validation
              |
              v
       STALE RESULT REJECTED
              |
              v
       Result cannot become
       authoritative state
```

Every asynchronous operation is associated with the generation in which it started.

Before its result can modify authoritative state, the operation must pass generation validation.

Therefore:

> **Superseded work cannot become the current authoritative state.**

This makes correctness independent of whether the underlying asynchronous operation can actually be cancelled.

## 7. Adversarial Interruption Test

The primary stress scenario is:

```text
User: "Modify my Tokyo flight."

Agent:
    modify_booking starts
    Generation 1

User interrupts:
    "Stop. Don't change my flight."
    "Keep it as it is."

System:
    Generation 1 invalidated

The cancellation-resistant operation later returns.

System:
    Generation 1 result rejected as stale

Agent:
    Confirms that the flight remains unchanged.
```

Observed live execution:

```text
14:33:18.868  OPERATION STARTED:
              op-1 type=modify_booking generation=1

14:33:20.877  USER STARTED SPEAKING:
              invalidating generation 1

14:33:20.878  Generation 1 invalidated: True

14:33:22.879  STALE RESULT REJECTED:
              operation=op-1 generation=1

14:33:30.578  Assistant:
              "Got it, your flight stays unchanged..."
```

The operation was deliberately designed to remain cancellation-resistant long enough to demonstrate why cancellation alone cannot provide correctness.

The important result is not that the underlying operation disappeared. The important result is that its superseded result was prevented from becoming authoritative state.

## 8. Reproducible Correctness Evidence

The B3 adversarial benchmark evaluates whether stale asynchronous results are rejected after an interruption.

Current benchmark result:

```text
Trials:                  50
Stale results rejected:  50/50
Correctness:             100.0%
Status:                  PASS
```

The benchmark exercises the generation-fence validation path repeatedly rather than relying on a single successful demonstration.

The repository contains the benchmark implementation and the relevant generation-validation logic so that the result can be reproduced.

## 9. What the Demonstration Proves

The demonstrated guarantee is:

> When a user interrupts an in-flight operation, the current generation is invalidated, and a result belonging to the superseded generation is rejected before it can become authoritative state.

This is stronger than relying solely on task cancellation.

The system explicitly separates:

1. **Cancellation:** a best-effort mechanism for stopping obsolete work.
2. **Generation invalidation:** immediately declares the previous intent obsolete.
3. **Commit validation:** prevents obsolete results from mutating current authoritative state.

This separation is the core correctness mechanism.

## 10. Rime's Role in the System

Rime provides the primary spoken-output layer for the realtime interaction.

The generation-fence experiment focuses on **state and tool correctness under interruption**. Rime is the TTS provider used by the live voice agent, while the application controls the higher-level interruption and state-management logic.

The current prototype does **not** claim that the Rime transport itself is independently cancellation-safe.

Similarly, the current evidence does not use an unverified audio-cutoff measurement to establish the correctness claim.

The verified claim is specifically that superseded asynchronous travel-operation results cannot become authoritative current state.

## 11. Limitations

The prototype uses cancellation-resistant asynchronous operations to make stale-result behavior observable and reproducible.

This means cancellation should be understood as **best effort**, not as the correctness mechanism.

The system therefore does not claim that an external operation that has already reached an irreversible external side effect can always be physically undone.

Instead, the generation fence guarantees that obsolete results cannot be accepted as the current conversational state after the user has changed intent.

Rime transport behavior is also not presented as independently cancellation-safe unless separately measured and verified.

## 12. Summary

Rime is integrated into the working realtime voice pipeline and provides the primary spoken interaction layer.

The central engineering contribution is the **Monotonic Generation Fence**, which protects authoritative state when users interrupt an agent while asynchronous work is still in flight.

The key design principle is:

```text
Cancellation may fail.
Correctness must not.
```

By invalidating the old generation immediately and validating every asynchronous result before commit, the system prevents superseded work from becoming the authoritative state of the current voice interaction.
