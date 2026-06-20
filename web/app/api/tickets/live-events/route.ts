import { auth } from "@/auth";
import { createDashboardToken, getApiBaseUrl } from "@/lib/dashboard-token";
import {
  LiveTicketEvent,
  publishLiveTicketEvent,
  subscribeLiveTicketEvents,
} from "@/lib/live-ticket-events";
import { NextRequest } from "next/server";
import type { Session } from "next-auth";

const SSE_HEADERS = {
  "Content-Type": "text/event-stream",
  "Cache-Control": "no-cache, no-transform",
  Connection: "keep-alive",
};

async function canAccessGuild(session: Session, guildId: string): Promise<boolean> {
  const token = await createDashboardToken({
    userId: session.user!.id,
    username: session.user!.name || "User",
    avatar: session.user!.image,
    guilds: (session.guilds || []).map((g) => ({
      id: g.id,
      name: g.name,
      permissions: g.permissions,
    })),
  });
  const resp = await fetch(`${getApiBaseUrl()}/guilds/${guildId}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  return resp.ok;
}

export async function GET(request: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return new Response("Unauthorized", { status: 401 });
  }

  const guildId = request.nextUrl.searchParams.get("guildId");
  if (!guildId) {
    return new Response("Missing guildId", { status: 400 });
  }

  if (!(await canAccessGuild(session as Session, guildId))) {
    return new Response("Forbidden", { status: 403 });
  }

  const encoder = new TextEncoder();
  let unsubscribe = () => {};
  let heartbeat: ReturnType<typeof setInterval> | undefined;
  let closed = false;

  const stream = new ReadableStream({
    start(controller) {
      const send = (payload: string) => {
        if (closed) {
          return;
        }
        controller.enqueue(encoder.encode(payload));
      };

      send(": connected\n\n");
      heartbeat = setInterval(() => send(": ping\n\n"), 25000);

      unsubscribe = subscribeLiveTicketEvents(guildId, (event) => {
        send(`data: ${JSON.stringify(event)}\n\n`);
      });
    },
    cancel() {
      closed = true;
      if (heartbeat) {
        clearInterval(heartbeat);
      }
      unsubscribe();
    },
  });

  return new Response(stream, { headers: SSE_HEADERS });
}

export async function POST(request: NextRequest) {
  const expected = process.env.TICKETS_BOT_API_SECRET;
  if (!expected) {
    return Response.json({ error: "Live events not configured" }, { status: 503 });
  }

  const key = request.headers.get("X-Tickets-Key");
  if (!key || key !== expected) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: LiveTicketEvent;
  try {
    body = (await request.json()) as LiveTicketEvent;
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  if (body.kind !== "ticket_created" || !body.guildId) {
    return Response.json({ error: "Invalid payload" }, { status: 400 });
  }

  publishLiveTicketEvent(body);
  return Response.json({ ok: true });
}
