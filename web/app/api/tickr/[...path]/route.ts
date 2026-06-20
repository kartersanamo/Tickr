import { auth } from "@/auth";
import { createDashboardToken, getApiBaseUrl } from "@/lib/dashboard-token";
import { NextRequest, NextResponse } from "next/server";

async function proxy(request: NextRequest, path: string) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const token = await createDashboardToken({
    userId: session.user.id,
    username: session.user.name || "User",
    avatar: session.user.image,
    guilds: (session.guilds || []).map((g) => ({
      id: g.id,
      name: g.name,
      permissions: g.permissions,
    })),
  });
  const url = `${getApiBaseUrl()}/${path}${request.nextUrl.search}`;
  const headers = new Headers();
  headers.set("Authorization", `Bearer ${token}`);
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("Content-Type", contentType);
  }
  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
  };
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }
  const resp = await fetch(url, init);
  const data = await resp.text();
  return new NextResponse(data, {
    status: resp.status,
    headers: { "Content-Type": resp.headers.get("Content-Type") || "application/json" },
  });
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxy(request, path.join("/"));
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxy(request, path.join("/"));
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxy(request, path.join("/"));
}

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxy(request, path.join("/"));
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxy(request, path.join("/"));
}
