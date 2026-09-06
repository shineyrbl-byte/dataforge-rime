# DATAFORGE 2026 × Rime

# Interruptible Travel Operations Voice Agent

A voice-native travel operations agent designed to remain correct when users change their minds while asynchronous travel operations are already running.

The project focuses on one hard problem:

> **How can a realtime voice agent guarantee that stale asynchronous work cannot overwrite the user's latest intent?**

---

## Core Engineering Idea

### Monotonic Generation Fence

Every user interaction belongs to a monotonically increasing **generation**.

When the user interrupts the agent:

1. The current generation is immediately invalidated.
2. In-flight asynchronous work receives a best-effort cancellation request.
3. A new generation is created for the revised instruction.
4. Every asynchronous result is validated against the current generation before it can commit.
5. Results belonging to invalidated generations are rejected.

The key correctness guarantee is:

> **Superseded work cannot become current authoritative state.**

Cancellation is therefore an optimization for responsiveness, not the correctness mechanism.

Even if an external operation ignores cancellation and eventually returns, its result is still rejected if it belongs to an invalidated generation.

---

## 🚀 Live Demo

**[Try the deployed voice agent](https://dataforge-rime.vercel.app)**

> Public demo of the Interruptible Travel Operations Voice Agent, powered by LiveKit and Rime TTS.

---

## Why This Matters

Voice agents create a particularly difficult race condition.

Consider:

```text
User:
"Modify my Tokyo flight."

Agent:
Starts asynchronous booking modification.

User:
"Stop. Don't change it. Keep the flight as it is."
```

The first operation may already be running when the user changes their mind.

A naive implementation can allow the old operation to finish and update the system after the newer instruction has already arrived.

The generation fence prevents this.

```text
Generation 1
    |
    +--> modify_booking starts
    |
    +--> USER INTERRUPTS
             |
             v
       Generation 1 INVALIDATED
             |
             +--> cancellation requested
             |
             +--> Generation 2 created
             
Generation 1 operation eventually returns
             |
             v
       generation validation
             |
             v
       STALE RESULT REJECTED
```

The authoritative state remains governed by the newest valid generation.

---

## Product

The prototype is an **Interruptible Travel Operations Voice Agent** for hands-busy environments such as travel coordination and field operations.

The user can manage travel actions through voice while asynchronous operations are running.

The prototype currently demonstrates:

* Flight availability checking
* Flight modification
* Hotel confirmation
* User interruption / barge-in
* Generation invalidation
* Best-effort cancellation
* Stale-result rejection
* Preservation of authoritative booking state

External travel operations are deliberately mocked so that cancellation-resistant behavior can be reproduced deterministically.

---

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
Travel tools
       |
       v
Rime TTS
       |
       v
LiveKit audio
       |
       v
User
```

### Technology Stack

* Python
* LiveKit Agents
* LiveKit Cloud
* Groq LLM
* Deepgram STT
* Silero VAD
* Rime TTS
* Next.js
* React
* WebRTC

---

## Rime TTS Integration

Rime is used as the primary spoken-output layer of the voice agent through the official LiveKit Rime TTS integration.

```python
tts = rime.TTS(
    model="coda",
    speaker="celeste",
    lang="eng",
    use_websocket=True,
    segment="bySentence",
)
```

**Shipped Rime configuration**

* **Model:** `coda`
* **Speaker:** `celeste`
* **Language:** `eng`
* **Transport:** WebSocket
* **Endpoint:** `wss://users-ws.rime.ai/ws3`
* **Audio format:** PCM
* **Sampling rate:** `22050 Hz`
* **Segmentation:** `bySentence`

The endpoint and audio parameters above are the values used by the installed LiveKit Rime plugin for the shipped WebSocket configuration.

Rime was verified in the live prototype by producing spoken agent responses in the browser.

Voice is fundamental to the product rather than a cosmetic interface layer. The target workflow assumes a user who may be operating hands-busy and cannot continuously interact with a traditional text interface.

---

## Key Acceptance Test

The primary adversarial scenario deliberately uses a delayed, cancellation-resistant flight modification operation.

### Test

```text
1. User: "Modify my Tokyo flight."

2. Generation 1 starts modify_booking.

3. User interrupts:
   "Stop. Don't change it. Keep the flight as it is."

4. Generation 1 is invalidated.

5. Cancellation is requested.

6. The old operation deliberately continues running.

7. The old operation eventually returns.

8. The generation fence rejects its result.

9. The revised instruction is processed under Generation 2.

10. The Tokyo flight remains unchanged.
```

### Required behavior

The system must:

* Detect the interruption while the operation is running.
* Invalidate the current generation.
* Request cancellation on a best-effort basis.
* Prevent stale work from committing.
* Process the revised instruction under a newer generation.
* Preserve authoritative state.

---

# B3: Stale-Result Correctness

The most important automated evidence is the adversarial stale-result benchmark.

The benchmark runs **50 cancellation-resistant trials**.

Each trial:

1. Starts an operation under Generation 1.
2. Invalidates Generation 1 while the operation is running.
3. Allows the operation to finish despite cancellation.
4. Attempts to commit its result.
5. Verifies that the stale result is rejected.

### Observed result

```text
Trials:                  50
Stale results rejected:  50/50
Correctness:             100.0%
B3 Status:               PASS
```

This test specifically demonstrates why the generation fence is stronger than cancellation alone.

---

## Live Adversarial Demonstration

A live voice run produced the following sequence:

```text
OPERATION STARTED: op-1, modify_booking, generation=1

USER STARTED SPEAKING: invalidating generation 1

Generation 1 invalidated: True

STALE RESULT REJECTED: operation=op-1, generation=1
```

The important observation is that the operation returned **after the interruption**, yet its result was rejected because it belonged to the invalidated generation.

The revised instruction was subsequently processed under Generation 2.

The terminal logs provide the live execution evidence while the frontend provides a judge-facing visualization of the generation-fence architecture.

---

## Architecture

```text
                         Browser
                            |
                         WebRTC
                            |
                            v
                      LiveKit Cloud
                            |
                            v
                       Voice Agent
                            |
              +-------------+-------------+
              |             |             |
           Silero        Deepgram       Groq
             VAD            STT           LLM
                                          |
                                          v
                              Monotonic Generation
                                    Fence
                                          |
                              +-----------+-----------+
                              |                       |
                              v                       v
                       Async Travel Tools          Rime TTS
                              |                       |
                              v                       v
                       Commit Boundary        Spoken Output
                              |
                              v
                    Authoritative State
```

The Generation Fence acts as the control plane between asynchronous computation and authoritative state.

---

## Generation Model

Generations move monotonically through the lifecycle:

```text
CREATED
   |
   v
ACTIVE
   |
   v
INVALIDATED
   |
   v
DRAINING
   |
   v
TERMINATED
```

An invalidated generation can never become active again.

Every asynchronous operation is associated with the generation that created it.

Before committing a result, the system verifies that:

```text
operation generation == current generation
AND
current generation is ACTIVE
AND
operation is still valid
```

If any condition fails, the result is rejected.

---

## Why Cancellation Is Not Enough

Cancellation is inherently best-effort.

A real external system may:

* Ignore cancellation.
* Complete work after cancellation is requested.
* Return a result after a newer user instruction has arrived.
* Continue processing work outside the control of the voice agent.

Therefore:

> **Cancellation improves responsiveness. The generation fence provides correctness.**

The system does not assume that asynchronous work can always be stopped.

Instead, it assumes that stale work may finish and makes that outcome safe.

---

## Reproducibility

### Run the automated test suite

```bash
python -m pytest -q
```

### Run the stale-result benchmark

```bash
PYTHONPATH=. python benchmarks/test_b3_stale_correctness.py
```

Expected result:

```text
RESULT: 50/50 stale results rejected
CORRECTNESS: 100.0%
B3 STATUS: PASS
```

---

## Repository Structure

```text
backend/
  agent.py
  control/
    fence.py
    turn_controller.py
  tools/
    executor.py
    mock_tools.py
    registry.py
  state/
    conversation.py

frontend/
  app/
  src/

benchmarks/
  test_b3_stale_correctness.py
  test_b1_ttfa.py
  test_b2_interrupt_cutoff.py
  adversarial/

tests/
  unit/
  integration/

docs/
  ARCHITECTURE.md
  JUDGING_GUIDE.md

RIME_EVIDENCE.md
README.md
requirements.txt
pyproject.toml
```

---

## Demo Flow

For the strongest demonstration:

### 1. Start the backend

```bash
python -m backend.agent dev
```

### 2. Start the frontend

From the frontend directory:

```bash
npm run dev
```

### 3. Connect to the voice agent

Use the browser interface.

### 4. Say

```text
Modify my Tokyo flight.
```

Wait until the terminal shows that `modify_booking` has started.

### 5. Interrupt

Say:

```text
Stop. Don't change it. Keep the flight as it is.
```

### 6. Show the evidence

The terminal should demonstrate:

```text
operation started
        ↓
user interruption
        ↓
generation invalidated
        ↓
old operation returns
        ↓
stale result rejected
        ↓
new generation processes revised instruction
```

The frontend visualization provides the corresponding architecture view.

---

## Design Principle

Realtime voice systems are not only latency-sensitive. They are also **concurrency-sensitive**.

A user can change their mind while:

* An LLM response is being generated.
* A tool is executing.
* An external API request is in flight.
* Speech is being synthesized.

The central design principle of this project is therefore:

> **Never trust cancellation as the source of correctness. Validate ownership at the commit boundary.**

The generation fence turns asynchronous cancellation races into a deterministic ownership check.

---

## Project Summary

**Problem:**
Voice users can change their intent while asynchronous operations are still running.

**Failure mode:**
A stale operation completes after a newer instruction and incorrectly updates the system.

**Solution:**
A monotonic generation fence combined with best-effort cancellation and commit-time validation.

**Evidence:**
50/50 cancellation-resistant stale-result trials rejected successfully.

**Result:**
100% stale-result correctness in the adversarial benchmark.

**Voice layer:**
Rime TTS through the LiveKit voice pipeline.

**Core guarantee:**

> **Superseded work cannot become current authoritative state.**
