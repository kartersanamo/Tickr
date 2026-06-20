import Link from "next/link";
import Image from "next/image";
import { signOut } from "@/auth";
import { Ticket, LogOut } from "lucide-react";

type Props = {
  user: { name?: string | null; image?: string | null };
  guildId?: string;
  guildName?: string;
};

const tabs = (guildId: string) => [
  { href: `/dashboard/${guildId}`, label: "Overview" },
  { href: `/dashboard/${guildId}/config`, label: "Config" },
  { href: `/dashboard/${guildId}/tickets`, label: "Ticket Types" },
  { href: `/dashboard/${guildId}/live`, label: "Live Tickets" },
];

export function DashboardNav({ user, guildId, guildName }: Props) {
  return (
    <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-black/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="flex items-center gap-2 font-bold">
            <Ticket className="text-[var(--accent)]" size={20} />
            Tickr
          </Link>
          {guildName && (
            <span className="hidden text-sm text-[var(--text-muted)] md:inline">/ {guildName}</span>
          )}
        </div>
        {guildId && (
          <nav className="flex flex-wrap gap-2">
            {tabs(guildId).map((tab) => (
              <Link
                key={tab.href}
                href={tab.href}
                className="rounded-lg px-3 py-1.5 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-white"
              >
                {tab.label}
              </Link>
            ))}
          </nav>
        )}
        <div className="flex items-center gap-3">
          {user.image && (
            <Image src={user.image} alt="" width={32} height={32} className="rounded-full" />
          )}
          <span className="hidden text-sm md:inline">{user.name}</span>
          <form
            action={async () => {
              "use server";
              await signOut({ redirectTo: "/" });
            }}
          >
            <button type="submit" className="btn-secondary px-3 py-2 text-sm">
              <LogOut size={16} />
            </button>
          </form>
        </div>
      </div>
    </header>
  );
}
