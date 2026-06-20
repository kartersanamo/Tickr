import { SignJWT } from "jose";

type GuildEntry = { id: string; name: string; permissions: string };

export async function createDashboardToken(payload: {
  userId: string;
  username: string;
  avatar?: string | null;
  guilds: GuildEntry[];
}) {
  const secret = process.env.DASHBOARD_INTERNAL_SECRET;
  if (!secret) {
    throw new Error("DASHBOARD_INTERNAL_SECRET is not set");
  }
  const key = new TextEncoder().encode(secret);
  return new SignJWT({
    username: payload.username,
    avatar: payload.avatar,
    guilds: payload.guilds,
  })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(payload.userId)
    .setIssuedAt()
    .setExpirationTime("24h")
    .sign(key);
}

export function getApiBaseUrl() {
  return process.env.TICKR_API_URL || "http://127.0.0.1:8790";
}
