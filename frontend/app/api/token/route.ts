import { NextResponse } from "next/server";
import { AccessToken } from "livekit-server-sdk";

export async function GET() {
  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;

  if (!apiKey || !apiSecret) {
    return NextResponse.json(
      { error: "LiveKit credentials are missing" },
      { status: 500 }
    );
  }

  const roomName = `travel-demo-${Date.now()}`;

  const token = new AccessToken(apiKey, apiSecret, {
    identity: `user-${Date.now()}`,
    ttl: "1h",
  });

  token.addGrant({
    roomJoin: true,
    room: roomName,
    canPublish: true,
    canSubscribe: true,
  });

  return NextResponse.json({
    token: await token.toJwt(),
    roomName,
  });
}
