import { auth } from "@/auth";
import { createDashboardToken, getApiBaseUrl } from "@/lib/dashboard-token";

export async function tickrFetch(path: string, init: RequestInit = {}) {
  const session = await auth();
  if (!session?.user?.id) {
    throw new Error("Unauthorized");
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
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const resp = await fetch(`${getApiBaseUrl()}${path}`, { ...init, headers, cache: "no-store" });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.detail || data.error || "Request failed");
  }
  return data;
}

export async function tickrFetchClient(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const resp = await fetch(`/api/tickr${path}`, { ...init, headers, cache: "no-store" });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.error || data.detail || "Request failed");
  }
  return data;
}
