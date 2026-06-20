import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { tickrFetch } from "@/lib/api-client";
import { DashboardNav } from "@/components/dashboard-nav";
import { GuildCard } from "@/components/guild-card";

type Guild = {
  id: string;
  name: string;
  icon: string | null;
  configured: boolean;
  setupComplete: boolean;
  missingRequired: string[];
};

export default async function DashboardPage() {
  const session = await auth();
  if (!session?.user) {
    redirect("/login");
  }
  let guilds: Guild[] = [];
  let error = "";
  try {
    const data = await tickrFetch("/me/guilds");
    guilds = data.guilds || [];
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load servers";
  }

  return (
    <div className="min-h-screen">
      <DashboardNav user={session.user} />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <h1 className="mb-2 text-3xl font-bold">Your servers</h1>
        <p className="mb-8 text-[var(--text-secondary)]">
          Select a server where Tickr is installed and you have manage permissions.
        </p>
        {error && (
          <div className="mb-6 rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-red-200">{error}</div>
        )}
        {guilds.length === 0 && !error ? (
          <div className="glass-card p-8 text-center">
            <p className="mb-4 text-[var(--text-secondary)]">
              No manageable servers found. Make sure Tickr is in your server and you have Administrator or Manage Server.
            </p>
            <a href={process.env.NEXT_PUBLIC_BOT_INVITE_URL} className="btn-primary" target="_blank" rel="noreferrer">
              Invite Tickr
            </a>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {guilds.map((guild) => (
              <GuildCard key={guild.id} guild={guild} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
