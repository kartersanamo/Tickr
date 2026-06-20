export type LiveTicketEvent = {
  kind: "ticket_created";
  guildId: string;
  channelId: string;
  ticketNumber: string;
  ticketType: string;
  ownerId: string;
  channelName: string;
};

type Listener = (event: LiveTicketEvent) => void;

type Hub = {
  subscribers: Map<string, Set<Listener>>;
};

const globalKey = "__tickrLiveTicketHub";

function hub(): Hub {
  const g = globalThis as typeof globalThis & { [globalKey]?: Hub };
  if (!g[globalKey]) {
    g[globalKey] = { subscribers: new Map() };
  }
  return g[globalKey];
}

export function subscribeLiveTicketEvents(guildId: string, listener: Listener): () => void {
  const listeners = hub().subscribers.get(guildId) ?? new Set<Listener>();
  listeners.add(listener);
  hub().subscribers.set(guildId, listeners);
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) {
      hub().subscribers.delete(guildId);
    }
  };
}

export function publishLiveTicketEvent(event: LiveTicketEvent): void {
  const listeners = hub().subscribers.get(event.guildId);
  if (!listeners) {
    return;
  }
  for (const listener of listeners) {
    listener(event);
  }
}
