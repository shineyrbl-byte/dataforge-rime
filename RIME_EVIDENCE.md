# Rime TTS Integration Evidence

## Overview

Rime is used as the primary spoken-output layer of the Interruptible Travel Operations Voice Agent.

The project uses the official LiveKit Rime TTS integration with WebSocket streaming.

## Configuration

The agent initializes Rime with:

```python
tts = rime.TTS(
    model="coda",
    speaker="celeste",
    use_websocket=True,
    segment="bySentence",
)
```

## Voice Pipeline

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
Rime TTS
      |
      v
LiveKit audio
      |
      v
User speaker
```

## Verification

Rime was verified in the live prototype by successfully generating spoken responses that were played to the user through the browser.

This confirms that Rime is part of the actual runtime voice pipeline rather than being included only as a dependency or documentation reference.

## Why Voice Is Necessary

The target workflow is designed for hands-busy travel operations.

The user should be able to issue and revise travel instructions without relying on continuous interaction with a text interface.

Voice therefore serves as the primary interaction mechanism.

## Voice-Specific Engineering Challenge

The primary engineering contribution of this project is the **Monotonic Generation Fence**.

The fence protects authoritative state from stale asynchronous operations when a user interrupts and changes their intent.

For example:

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
       Generation 2 created
             
Generation 1 operation eventually returns
             |
             v
       Generation validation
             |
             v
       STALE RESULT REJECTED
```

The important distinction is that cancellation is not treated as the correctness mechanism.

An asynchronous operation may continue even after cancellation is requested. The generation check at the commit boundary ensures that its result cannot overwrite the newer state.

## Rime's Role

Rime provides the spoken-output layer required for the realtime voice interaction.

The generation-fence experiment primarily demonstrates **state/tool correctness** under cancellation-resistant asynchronous work.

The current prototype does not claim that the Rime transport itself is independently cancellation-safe. Instead, the demonstrated correctness guarantee is that stale travel-operation results cannot become the current authoritative state.

## Evidence for Judges

The strongest reproducible evidence is the B3 adversarial benchmark:

```text
Trials:                  50
Stale results rejected:  50/50
Correctness:             100.0%
Status:                  PASS
```

A live demonstration additionally shows:

```text
Operation started
        |
        v
User interruption detected
        |
        v
Generation invalidated
        |
        v
Cancellation requested
        |
        v
Old operation returns
        |
        v
Stale result rejected
        |
        v
Revised instruction processed
```

## Summary

Rime is integrated into the working voice pipeline and provides the primary spoken interaction layer.

The project's core engineering contribution is the monotonic generation fence, which makes interruption correctness independent of whether an asynchronous operation can actually be cancelled.
