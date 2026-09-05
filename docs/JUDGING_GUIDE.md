# Judging Guide

## Project

**DATAFORGE 2026 × Rime**

### Interruptible Travel Operations Voice Agent

---

# 1. What Problem Does This Project Solve?

The project addresses a race condition in realtime voice agents.

A user can change their mind while an asynchronous operation is already running.

Example:

```text
User:
"Modify my Tokyo flight."

        ↓

modify_booking starts

        ↓

User:
"Stop. Don't change it. Keep the flight as it is."
```

The first operation may already be impossible to cancel.

A naive system can allow the old operation to finish and overwrite the newer user intent.

This project prevents that failure.

---

# 2. Core Innovation

## Monotonic Generation Fence

Each user interaction belongs to a generation.

When the user interrupts:

```text
Generation 1
     |
     v
INVALIDATED
     |
     v
Generation 2
```

Every asynchronous operation remembers the generation that created it.

Before committing its result, the system verifies that the generation is still current and active.

If not, the result is rejected.

### Core guarantee

> **Superseded work cannot become current authoritative state.**

---

# 3. Why Cancellation Alone Is Insufficient

The prototype deliberately uses a cancellation-resistant mock operation.

The operation continues after cancellation is requested and eventually returns.

This demonstrates the actual race:

```text
Operation starts
      |
User interrupts
      |
Cancellation requested
      |
Operation ignores cancellation
      |
Operation returns
      |
Generation validation
      |
STALE RESULT REJECTED
```

This is the most important engineering distinction in the project.

> **Cancellation improves responsiveness. The generation fence provides correctness.**

---

# 4. Recommended Demo

## Step 1: Connect

Open the browser frontend and connect to the voice agent.

The frontend contains a judge-facing visualization of the generation-fence architecture.

## Step 2: Start the operation

Say:

> "Modify my Tokyo flight."

Wait until the backend terminal shows that `modify_booking` has started.

## Step 3: Interrupt

Say:

> "Stop. Don't change it. Keep the flight as it is."

## Step 4: Watch the terminal

The terminal should show a sequence similar to:

```text
OPERATION STARTED: op-1, modify_booking, generation=1

USER STARTED SPEAKING: invalidating generation 1

Generation 1 invalidated: True

STALE RESULT REJECTED: operation=op-1, generation=1
```

## Step 5: Observe the final response

The agent should acknowledge that the Tokyo flight remains unchanged.

---

# 5. What the Demo Proves

The demonstration proves all of the following:

### 1. Voice interaction

The user interacts with the system through speech.

### 2. Realtime interruption

The user can interrupt while asynchronous work is running.

### 3. Generation invalidation

The old generation is invalidated when the user changes intent.

### 4. Cancellation

The system requests cancellation on a best-effort basis.

### 5. Cancellation resistance

The deliberately delayed operation can continue despite cancellation.

### 6. Stale-result protection

The old result is rejected when it eventually returns.

### 7. Correct final state

The superseded operation does not become the authoritative travel state.

---

# 6. Reproducible Evidence

Run:

```bash
python -m pytest -q
```

Then:

```bash
PYTHONPATH=. python benchmarks/test_b3_stale_correctness.py
```

B3 tests the exact failure mode targeted by the project.

Expected evidence:

```text
RESULT: 50/50 stale results rejected
CORRECTNESS: 100.0%
B3 STATUS: PASS
```

The benchmark deliberately allows cancellation-resistant operations to complete before checking whether their results can commit.

---

# 7. Rime Integration

Rime is the primary spoken-output layer.

The implementation uses:

```python
tts = rime.TTS(
    model="coda",
    speaker="celeste",
    use_websocket=True,
    segment="bySentence",
)
```

The voice pipeline is:

```text
Microphone
    ↓
LiveKit WebRTC
    ↓
Silero VAD
    ↓
Deepgram STT
    ↓
Groq LLM
    ↓
Rime TTS
    ↓
LiveKit audio
```

Rime is therefore part of the working voice interaction rather than a cosmetic dependency.

---

# 8. Mapping to Judging Criteria

## Voice Problem / Necessity

The target user operates in hands-busy travel environments.

Voice allows travel instructions to be issued and revised without continuously interacting with a text interface.

The project specifically focuses on the interruption problem that becomes difficult in realtime voice systems.

---

## Hard Voice Engineering

The hard engineering problem is not simply speech recognition or speech synthesis.

It is concurrency correctness during realtime voice interaction.

The generation fence handles:

* User barge-in
* Generation invalidation
* Asynchronous operations
* Cancellation races
* Commit-time validation
* Stale-result rejection

The key design choice is to make correctness independent of cancellation succeeding.

---

## Evidence / Reproducibility

The adversarial B3 benchmark provides deterministic evidence.

```text
50 trials
50 stale results rejected
100.0% correctness
PASS
```

The live terminal demonstration provides additional runtime evidence.

The test is deliberately adversarial because the stale operation is allowed to finish.

---

## Rime Integration / Voice Experience

Rime is integrated as the primary TTS layer in the LiveKit voice pipeline.

The browser prototype demonstrates actual spoken interaction.

The target workflow requires voice because the intended environment is hands-busy operation.

---

## Demo Clarity

The entire project can be demonstrated with one scenario:

```text
Modify Tokyo flight
        ↓
Operation starts
        ↓
User interrupts
        ↓
Generation invalidated
        ↓
Old operation continues
        ↓
Stale result rejected
        ↓
Flight remains unchanged
```

This scenario directly exposes the project's core engineering contribution.

---

# 9. What to Look for in the Logs

The most important log messages are:

```text
OPERATION STARTED
```

This establishes that asynchronous work actually began.

```text
USER STARTED SPEAKING: invalidating generation
```

This establishes that the user's interruption invalidated the old generation.

```text
Generation 1 invalidated: True
```

This establishes that invalidation succeeded.

```text
STALE RESULT REJECTED
```

This is the key correctness event.

It proves that the old operation returned after invalidation but was prevented from committing.

---

# 10. Important Interpretation

The project does **not** claim that every external asynchronous operation can be physically cancelled.

Instead, it assumes the opposite:

> An old operation may continue running.

The correctness mechanism is therefore the commit-time generation check.

This makes the architecture applicable to external operations where cancellation is unavailable, unreliable, or too late.

---

# 11. One-Sentence Explanation for Judges

If asked to explain the project in one sentence:

> **We built a voice travel agent where every asynchronous operation belongs to a monotonic user-intent generation, so even if an old operation ignores cancellation and finishes later, its stale result cannot overwrite the latest state.**

---

# 12. Key Takeaway

The project is fundamentally about **correctness under interruption**.

The voice interface creates the realtime interaction.

The asynchronous travel operation creates the race.

The generation fence resolves the race.

The adversarial benchmark demonstrates that the stale result is rejected even when cancellation fails.

**Core principle:**

> **Cancellation improves responsiveness. Generation ownership provides correctness.**
