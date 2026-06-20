"use client";

import { useCallback, useEffect, useState } from "react";
import { tickrFetchClient } from "@/lib/api-client";
import { RefreshCw } from "lucide-react";

type Ticket = {
  channelId: string;
  ownerId: string;
  type: string;
  number: number;
  name: string;
  channelName: string;
  openedAt: number;
  durationSeconds: number;
  privated: string;
};

type Props = { guildId: string };

function formatDuration(seconds: number) {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m < 60) return `${m}m ${s}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

export function LiveTicketsPanel({ guildId }: Props) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionTicket, setActionTicket] = useState<Ticket | null>(null);
  const [actionMode, setActionMode] = useState<"close" | "rename" | null>(null);
  const [closeReason, setCloseReason] = useState("");
  const [renameName, setRenameName] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await tickrFetchClient(`/guilds/${guildId}/tickets/active`);
      setTickets(data.tickets || []);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tickets");
    } finally {
      setLoading(false);
    }
  }, [guildId]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, [load]);

  async function closeTicket(ticket: Ticket) {
    if (closeReason.length < 2) {
      setError("Reason must be at least 2 characters");
      return;
    }
    await tickrFetchClient(`/guilds/${guildId}/tickets/${ticket.channelId}/close`, {
      method: "POST",
      body: JSON.stringify({ reason: closeReason }),
    });
    setActionTicket(null);
    setCloseReason("");
    await load();
  }

  async function renameTicket(ticket: Ticket) {
    if (renameName.length < 2) return;
    await tickrFetchClient(`/guilds/${guildId}/tickets/${ticket.channelId}/command`, {
      method: "POST",
      body: JSON.stringify({ command: "rename", args: renameName }),
    });
    setActionTicket(null);
    setRenameName("");
    await load();
  }

  async function runCommand(ticket: Ticket, command: string, args = "") {
    await tickrFetchClient(`/guilds/${guildId}/tickets/${ticket.channelId}/command`, {
      method: "POST",
      body: JSON.stringify({ command, args }),
    });
    await load();
  }

  if (loading) return <p className="text-[var(--text-muted)]">Loading active tickets...</p>;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-[var(--text-secondary)]">{tickets.length} active ticket(s)</p>
        <button type="button" className="btn-secondary text-sm" onClick={load}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>
      {error && <div className="mb-4 text-red-300">{error}</div>}
      {tickets.length === 0 ? (
        <div className="glass-card p-8 text-center text-[var(--text-muted)]">No active tickets right now.</div>
      ) : (
        <div className="space-y-4">
          {tickets.map((ticket) => (
            <article key={ticket.channelId} className="glass-card p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold">
                    #{ticket.number} — {ticket.type}
                  </h3>
                  <p className="text-sm text-[var(--text-secondary)]">
                    {ticket.channelName} · Owner <span className="font-mono">{ticket.ownerId}</span>
                  </p>
                  <p className="text-sm text-[var(--text-muted)]">
                    Open <span suppressHydrationWarning>{formatDuration(ticket.durationSeconds)}</span> ago
                    {ticket.privated ? ` · ${ticket.privated}` : ""}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="btn-secondary text-sm"
                    onClick={() => {
                      setActionTicket(ticket);
                      setActionMode("close");
                      setCloseReason("");
                    }}
                  >
                    Close
                  </button>
                  <button
                    type="button"
                    className="btn-secondary text-sm"
                    onClick={() => {
                      setActionTicket(ticket);
                      setActionMode("rename");
                      setRenameName(ticket.channelName);
                    }}
                  >
                    Rename
                  </button>
                  <button type="button" className="btn-secondary text-sm" onClick={() => runCommand(ticket, "private")}>
                    Private
                  </button>
                  <button type="button" className="btn-secondary text-sm" onClick={() => runCommand(ticket, "management")}>
                    Management
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {actionTicket && actionMode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="glass-card w-full max-w-md p-6">
            <h3 className="mb-4 text-lg font-semibold">Ticket #{actionTicket.number}</h3>
            {actionMode === "rename" ? (
              <>
                <input
                  className="input-field mb-4"
                  value={renameName}
                  onChange={(e) => setRenameName(e.target.value)}
                  placeholder="New channel name"
                />
                <div className="flex gap-2">
                  <button type="button" className="btn-primary" onClick={() => renameTicket(actionTicket)}>
                    Rename
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => {
                      setActionTicket(null);
                      setActionMode(null);
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </>
            ) : (
              <>
                <input
                  className="input-field mb-4"
                  value={closeReason}
                  onChange={(e) => setCloseReason(e.target.value)}
                  placeholder="Close reason"
                />
                <div className="flex gap-2">
                  <button type="button" className="btn-primary" onClick={() => closeTicket(actionTicket)}>
                    Close ticket
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => {
                      setActionTicket(null);
                      setActionMode(null);
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
