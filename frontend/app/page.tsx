"use client";

import { useEffect, useState } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  ControlBar,
  useConnectionState,
} from "@livekit/components-react";
import "@livekit/components-styles";

const LIVEKIT_URL = process.env.NEXT_PUBLIC_LIVEKIT_URL!;

function ConnectionStatus() {
  const connectionState = useConnectionState();

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-zinc-500">
        Connection
      </p>
      <p className="mt-1 text-lg font-semibold text-white">
        {connectionState}
      </p>
    </div>
  );
}

function DebugPanel() {
  return (
    <div className="mt-6 rounded-xl border border-zinc-800 bg-zinc-950 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-zinc-500">
            Generation Fence · Architecture
          </p>
          <h2 className="mt-1 text-xl font-semibold text-white">
            Protected
          </h2>
        </div>

        <div className="rounded-full border border-emerald-800 bg-emerald-950 px-3 py-1 text-xs font-medium text-emerald-400">
          ACTIVE
        </div>
      </div>

      <div className="mt-6 space-y-3">
        <div className="flex items-center gap-3">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
          <div>
            <p className="text-sm font-medium text-white">
              Generation 1
            </p>
            <p className="text-xs text-zinc-500">
              Example protected execution flow
            </p>
          </div>
        </div>

        <div className="ml-1 border-l border-zinc-800 pl-6">
          <div className="flex items-center gap-3 py-2">
            <span className="text-sm text-zinc-400">→</span>
            <div>
              <p className="text-sm text-white">
                modify_booking
              </p>
              <p className="text-xs text-zinc-500">
                Async operation
              </p>
            </div>
            <span className="ml-auto rounded-md bg-yellow-950 px-2 py-1 text-xs text-yellow-400">
              RUNNING
            </span>
          </div>

          <div className="flex items-center gap-3 py-2">
            <span className="text-sm text-zinc-400">→</span>
            <div>
              <p className="text-sm text-white">
                User interruption
              </p>
              <p className="text-xs text-zinc-500">
                Generation invalidated
              </p>
            </div>
            <span className="ml-auto rounded-md bg-red-950 px-2 py-1 text-xs text-red-400">
              INVALIDATED
            </span>
          </div>

          <div className="flex items-center gap-3 py-2">
            <span className="text-sm text-zinc-400">→</span>
            <div>
              <p className="text-sm text-white">
                modify_booking result
              </p>
              <p className="text-xs text-zinc-500">
                Superseded result
              </p>
            </div>
            <span className="ml-auto rounded-md bg-red-950 px-2 py-1 text-xs text-red-400">
              REJECTED
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
          <div>
            <p className="text-sm font-medium text-white">
              Generation 2
            </p>
            <p className="text-xs text-zinc-500">
              Revised user instruction accepted
            </p>
          </div>
          <span className="ml-auto rounded-md bg-emerald-950 px-2 py-1 text-xs text-emerald-400">
            ACTIVE
          </span>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <p className="text-xs text-zinc-500">
            Stale Results
          </p>
          <p className="mt-1 text-2xl font-bold text-white">
            1
          </p>
        </div>

        <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <p className="text-xs text-zinc-500">
            Fence
          </p>
          <p className="mt-1 text-2xl font-bold text-emerald-400">
            ON
          </p>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function getToken() {
      try {
        const response = await fetch("/api/token");

        if (!response.ok) {
          throw new Error("Failed to get LiveKit token");
        }

        const data = await response.json();
        setToken(data.token);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unknown connection error"
        );
      }
    }

    getToken();
  }, []);

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-black p-8">
        <div className="rounded-xl border border-red-900 bg-red-950/30 p-6">
          <h1 className="text-xl font-bold text-red-400">
            Connection Error
          </h1>
          <p className="mt-2 text-zinc-300">{error}</p>
        </div>
      </main>
    );
  }

  if (!token) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-black">
        <p className="text-zinc-400">
          Connecting to Travel Agent...
        </p>
      </main>
    );
  }

  return (
    <LiveKitRoom
      token={token}
      serverUrl={LIVEKIT_URL}
      connect={true}
      audio={true}
      video={false}
    >
      <main className="min-h-screen bg-black p-8">
        <div className="mx-auto w-full max-w-3xl">
          <div className="mb-8">
            <p className="text-sm font-medium text-zinc-500">
              DATAFORGE 2026 × Rime
            </p>

            <h1 className="mt-2 text-4xl font-bold tracking-tight text-white">
              Interruptible Travel Operations Agent
            </h1>

            <p className="mt-2 text-zinc-400">
              Voice-native travel assistant with protected asynchronous
              state.
            </p>
          </div>

          <ConnectionStatus />

          <div className="mt-6 rounded-xl border border-zinc-800 bg-zinc-950 p-6">
            <p className="text-sm text-zinc-400">
              Try saying:
            </p>

            <p className="mt-2 text-lg font-medium text-white">
              “Modify my Tokyo flight.”
            </p>

            <p className="mt-2 text-sm text-zinc-500">
              Then interrupt with a conflicting instruction while the
              operation is still running.
            </p>

            <div className="mt-5">
              <ControlBar
                variation="minimal"
                controls={{
                  microphone: true,
                  camera: false,
                  screenShare: false,
                }}
              />
            </div>
          </div>

          <DebugPanel />
        </div>

        <RoomAudioRenderer />
      </main>
    </LiveKitRoom>
  );
}