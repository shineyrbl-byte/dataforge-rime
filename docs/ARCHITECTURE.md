# Architecture

## 1. System Overview

The Interruptible Travel Operations Voice Agent is a realtime voice system designed to remain correct when asynchronous travel operations overlap with user interruptions.

The architecture separates:

1. Voice interaction
2. Reasoning
3. Asynchronous travel operations
4. Generation ownership
5. Authoritative state

The key component is the **Monotonic Generation Fence**.

Its purpose is to ensure that work started by an older user intent cannot commit after that intent has been superseded.

---

## 2. High-Level Architecture

```text
                         Browser
                            |
                            | WebRTC
                            v
                       LiveKit Cloud
                            |
                            v
                       Voice Agent
                            |
              +-------------+-------------+
              |             |             |
              v             v             v
          Silero VAD    Deepgram STT   Groq LLM
                                          |
                                          v
                                Generation Controller
                                          |
                         +----------------+----------------+
                         |                                 |
                         v                                 v
                  Async Travel Tools                    Rime TTS
                         |                                 |
                         v                                 v
                 Commit Boundary                    Spoken Response
                         |
                         v
                Authoritative State
```

---

## 3. Voice Layer

### LiveKit

LiveKit provides the realtime WebRTC transport between the browser and the voice agent.

It is responsible for carrying the user's microphone input and the agent's spoken output.

### Silero VAD

Silero VAD detects when the user begins speaking.

The user speaking event is important because it can indicate a barge-in while the agent is still processing an earlier request.

### Deepgram STT

Deepgram converts the user's speech into text for the agent.

### Groq LLM

The Groq-hosted language model interprets the user's instruction and determines which travel operation should be performed.

### Rime TTS

Rime provides the primary spoken-output layer.

The implementation uses the LiveKit Rime integration:

```python
tts = rime.TTS(
    model="coda",
    speaker="celeste",
    use_websocket=True,
    segment="bySentence",
)
```

---

## 4. Generation Model

Every active user interaction is associated with a generation.

Generations are monotonic:

```text
Generation 1
     |
     | user interruption
     v
Generation 1 INVALIDATED
     |
     v
Generation 2 ACTIVE
```

An invalidated generation can never become active again.

This gives asynchronous operations an explicit ownership relationship.

An operation started by Generation 1 belongs to Generation 1 even if it finishes much later.

---

## 5. Generation Lifecycle

The controller models generation state using:

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

### ACTIVE

The generation is currently allowed to produce and commit results.

### INVALIDATED

A newer user intent has superseded this generation.

No result belonging to this generation may become current state.

### DRAINING

Previously started work is being allowed to finish or respond to cancellation.

### TERMINATED

The generation is no longer relevant to the current interaction.

---

## 6. Operation Ownership

Each asynchronous operation is associated with:

```text
operation_id
generation_id
operation_type
operation_status
task
```

Examples of operation types include:

```text
modify_booking
check_availability
confirm_booking
```

The generation ID establishes ownership.

For example:

```text
Generation 1
    |
    +-- op-1: modify_booking
    +-- op-2: check_availability

Generation 2
    |
    +-- op-3: confirm_booking
```

An operation cannot become authoritative merely because it eventually completes.

Its generation must still be valid.

---

## 7. Barge-In Handling

The voice agent observes the user's speaking state.

When the user begins speaking while an active asynchronous operation exists:

```text
USER STARTS SPEAKING
        |
        v
Current generation identified
        |
        v
Generation invalidated
        |
        +----> cancellation requested
        |
        v
New generation becomes available
```

The important operation is **invalidation**.

Cancellation is best-effort because the underlying operation may not actually stop.

---

## 8. Cancellation-Resistant Operations

The prototype deliberately models an external operation that can survive cancellation.

The mock flight modification operation waits before returning and catches cancellation so that it can continue.

This reproduces an important real-world condition:

> An application cannot assume that every external asynchronous operation can be stopped.

This is precisely the situation the generation fence is designed to handle.

---

## 9. Commit Boundary

The most important correctness point is the commit boundary.

The flow is:

```text
Async operation
      |
      v
Operation completes
      |
      v
Generation validation
      |
      +---- invalid ----> REJECT
      |
      v
Operation validation
      |
      +---- invalid ----> REJECT
      |
      v
Commit authoritative state
```

The result is not trusted merely because the underlying operation succeeded.

Before committing, the controller verifies that the operation still belongs to the current active generation.

---

## 10. Stale Result Scenario

Consider:

```text
Generation 1
    |
    +--> modify_booking starts
    |
    |    operation still running
    |
    +--> User says:
         "Stop. Don't change it."
              |
              v
       Generation 1 invalidated
              |
              v
       Generation 2 starts
              
Generation 1 modify_booking
continues despite cancellation
              |
              v
       Operation completes
              |
              v
       Generation check
              |
              v
       STALE RESULT REJECTED
```

The old operation therefore cannot overwrite the current authoritative state.

---

## 11. Why This Is Stronger Than Cancellation

Cancellation answers:

> Can we stop the work?

The generation fence answers:

> Is the result still allowed to commit?

These are different questions.

A cancellation request can fail, race with completion, or be ignored by an external service.

Generation validation remains useful even when cancellation fails.

Therefore:

> **Cancellation improves responsiveness. The generation fence provides correctness.**

---

## 12. Authoritative State

The controller maintains authoritative travel state.

The important rule is:

```text
Only a valid current generation may commit state changes.
```

The authoritative state is therefore protected from stale asynchronous results.

For the demonstration scenario, the Tokyo flight remains unchanged when the user reverses the modification request.

---

## 13. Example End-to-End Execution

```text
User:
"Modify my Tokyo flight."

        |
        v

Generation 1 ACTIVE

        |
        v

modify_booking starts

        |
        | user interrupts
        v

Generation 1 INVALIDATED

        |
        +--> cancellation requested

        |
        v

Generation 2 ACTIVE

        |
        v

Old modify_booking eventually returns

        |
        v

Commit validation

        |
        v

STALE RESULT REJECTED

        |
        v

Generation 2 remains authoritative
```

The important property is that the old operation may physically complete without being logically accepted.

---

## 14. Correctness Invariant

The central invariant is:

> **A result can modify authoritative state only if it belongs to the current active generation and remains valid at the commit boundary.**

This converts an asynchronous race into an explicit ownership check.

---

## 15. Testing Strategy

The architecture is tested at multiple levels.

### Unit tests

Test generation lifecycle and controller behavior.

### Integration tests

Test normal voice-agent execution.

### Adversarial benchmark

B3 repeatedly creates the cancellation race:

```text
start operation
      |
invalidate generation
      |
allow operation to finish
      |
attempt commit
      |
verify rejection
```

The benchmark runs 50 trials.

Observed result:

```text
50/50 stale results rejected
100.0% correctness
PASS
```

---

## 16. Design Principle

The architecture intentionally assumes that asynchronous work may outlive the user intent that created it.

Instead of trying to guarantee that every task stops, the system guarantees that stale work cannot become authoritative.

This is the central design principle:

> **Do not make correctness depend on cancellation succeeding. Make correctness depend on ownership validation.**
