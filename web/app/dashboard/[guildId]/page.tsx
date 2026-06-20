import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { tickrFetch } from "@/lib/api-client";
import { DashboardNav } from "@/components/dashboard-nav";
import Link from "next/link";

type Props = { params: Promise<{ guildId: string }> };

export default async function GuildOverviewPage({ params }: Props) {
  const session = await auth();
  if (!session?.user) redirect("/login");
  const { guildId } = await params;
  let summary;
  try {
    summary = await tickrFetch(`/guilds/${guildId}`);
  } catch {
    redirect("/dashboard");
  }

  return (
    <div className="min-h-screen">
      <DashboardNav user={session.user} guildId={guildId} guildName={summary.name} />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <h1 className="mb-2 text-3xl font-bold">{summary.name}</h1>
        <p className="mb-8 text-[var(--text-secondary)]">Server overview and quick links.</p>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Active tickets" value={summary.activeTickets} />
          <StatCard label="Closed tickets" value={summary.closedTickets} />
          <StatCard label="Configured" value={summary.configured ? "Yes" : "No"} />
          <StatCard label="Tickets enabled" value={summary.ticketsGlobalEnabled ? "Yes" : "No"} />
        </div>
        {summary.missingRequired?.length > 0 && (
          <div className="mt-6 rounded-lg border border-amber-500/40 bg-amber-500/10 p-4">
            <p className="font-medium text-amber-100">Missing required settings</p>
            <ul className="mt-2 list-inside list-disc text-sm text-amber-200">
              {summary.missingRequired.map((item: string) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <QuickLink href={`/dashboard/${guildId}/config`} title="Configuration" desc="Edit all Tickr settings" />
          <QuickLink href={`/dashboard/${guildId}/tickets`} title="Ticket types" desc="Manage panels and questions" />
          <QuickLink href={`/dashboard/${guildId}/live`} title="Live tickets" desc="View and action open tickets" />
        </div>
      </main>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="glass-card p-5">
      <p className="text-sm text-[var(--text-muted)]">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  );
}

function QuickLink({ href, title, desc }: { href: string; title: string; desc: string }) {
  return (
    <Link href={href} className="glass-card block p-5 transition hover:border-[var(--accent)]">
      <h2 className="font-semibold">{title}</h2>
      <p className="mt-1 text-sm text-[var(--text-secondary)]">{desc}</p>
    </Link>
  );
}
