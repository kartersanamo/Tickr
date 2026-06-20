import Link from "next/link";
import { auth } from "@/auth";
import { siteConfig } from "@/lib/theme";
import { Ticket, Sparkles, Shield, LayoutDashboard, FileText, Users, Server } from "lucide-react";

const icons = [Sparkles, LayoutDashboard, Shield, FileText, Users, Server];

export default async function HomePage() {
  const session = await auth();

  return (
    <div className="min-h-screen">
      <header className="fixed top-0 inset-x-0 z-50 border-b border-[var(--border)] bg-black/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">
            <Ticket className="text-[var(--accent)]" size={22} />
            Tickr
          </Link>
          <nav className="flex items-center gap-3">
            {session ? (
              <Link href="/dashboard" className="btn-primary text-sm">
                Dashboard
              </Link>
            ) : (
              <Link href="/login" className="btn-primary text-sm">
                Sign in with Discord
              </Link>
            )}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 pt-32 pb-20">
        <section className="text-center">
          <p className="mb-4 text-sm uppercase tracking-[0.2em] text-[var(--accent)]">Discord Ticket Bot</p>
          <h1 className="mb-6 text-5xl font-bold leading-tight md:text-6xl">
            Tickets that feel
            <span className="block text-[var(--accent)]">effortless.</span>
          </h1>
          <p className="mx-auto mb-10 max-w-2xl text-lg text-[var(--text-secondary)]">
            {siteConfig.tagline} Set up panels, manage config, and handle live tickets from Discord or the web.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <a href={siteConfig.inviteUrl} className="btn-primary text-base" target="_blank" rel="noreferrer">
              Add to Discord
            </a>
            <Link href={session ? "/dashboard" : "/login"} className="btn-secondary text-base">
              Open Dashboard
            </Link>
          </div>
        </section>

        <section className="mt-24 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {siteConfig.features.map((feature, i) => {
            const Icon = icons[i] || Ticket;
            return (
              <article key={feature.title} className="glass-card p-6 transition hover:border-[var(--accent)]">
                <Icon className="mb-4 text-[var(--accent)]" size={28} />
                <h2 className="mb-2 text-xl font-semibold">{feature.title}</h2>
                <p className="text-[var(--text-secondary)]">{feature.description}</p>
              </article>
            );
          })}
        </section>

        <section className="mt-24 glass-card p-10 text-center">
          <h2 className="mb-4 text-3xl font-bold">Ready to get started?</h2>
          <p className="mb-8 text-[var(--text-secondary)]">
            Invite Tickr, run <code className="rounded bg-[var(--bg-tertiary)] px-2 py-1">/setup</code>, or sign in to configure from the web.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <a href={siteConfig.inviteUrl} className="btn-primary" target="_blank" rel="noreferrer">
              Invite Tickr
            </a>
            <Link href="/login" className="btn-secondary">
              Sign in
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-[var(--border)] py-8 text-center text-sm text-[var(--text-muted)]">
        <p>
          Tickr by{" "}
          <a href="https://kartersanamo.com" className="text-[var(--accent)] hover:underline" target="_blank" rel="noreferrer">
            kartersanamo.com
          </a>
        </p>
      </footer>
    </div>
  );
}
