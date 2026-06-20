import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { tickrFetch } from "@/lib/api-client";
import { DashboardNav } from "@/components/dashboard-nav";
import { LiveTicketsPanel } from "@/components/live-tickets-panel";

type Props = { params: Promise<{ guildId: string }> };

export default async function GuildLivePage({ params }: Props) {
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
        <h1 className="mb-2 text-3xl font-bold">Live tickets</h1>
        <p className="mb-8 text-[var(--text-secondary)]">
          Active tickets in {summary.name}. Actions run through the Tickr bot.
        </p>
        <LiveTicketsPanel guildId={guildId} />
      </main>
    </div>
  );
}
