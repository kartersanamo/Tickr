import Link from "next/link";
import { signIn } from "@/auth";
import { siteConfig } from "@/lib/theme";
import { Ticket } from "lucide-react";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="glass-card w-full max-w-md p-8 text-center">
        <div className="mb-6 flex justify-center">
          <Ticket className="text-[var(--accent)]" size={40} />
        </div>
        <h1 className="mb-2 text-2xl font-bold">Welcome back</h1>
        <p className="mb-8 text-[var(--text-secondary)]">
          Sign in with Discord to manage Tickr settings for your servers.
        </p>
        <form
          action={async () => {
            "use server";
            await signIn("discord", { redirectTo: "/dashboard" });
          }}
        >
          <button type="submit" className="btn-primary w-full">
            Continue with Discord
          </button>
        </form>
        <p className="mt-6 text-sm text-[var(--text-muted)]">
          Don&apos;t have Tickr yet?{" "}
          <a href={siteConfig.inviteUrl} className="text-[var(--accent)] hover:underline" target="_blank" rel="noreferrer">
            Invite the bot
          </a>
        </p>
        <Link href="/" className="mt-4 inline-block text-sm text-[var(--text-muted)] hover:text-white">
          Back to home
        </Link>
      </div>
    </div>
  );
}
