import Link from "next/link";
import Image from "next/image";
import { AlertCircle, CheckCircle2 } from "lucide-react";

type Guild = {
  id: string;
  name: string;
  icon: string | null;
  configured: boolean;
  setupComplete: boolean;
  missingRequired: string[];
};

export function GuildCard({ guild }: { guild: Guild }) {
  return (
    <Link href={`/dashboard/${guild.id}`} className="glass-card block p-5 transition hover:border-[var(--accent)]">
      <div className="flex items-start gap-4">
        {guild.icon ? (
          <Image src={guild.icon} alt="" width={48} height={48} className="rounded-xl" />
        ) : (
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--bg-tertiary)] text-lg font-bold">
            {guild.name.charAt(0)}
          </div>
        )}
        <div className="flex-1">
          <h2 className="text-lg font-semibold">{guild.name}</h2>
          <div className="mt-2 flex items-center gap-2 text-sm">
            {guild.setupComplete ? (
              <>
                <CheckCircle2 size={16} className="text-green-400" />
                <span className="text-green-300">Fully configured</span>
              </>
            ) : (
              <>
                <AlertCircle size={16} className="text-amber-400" />
                <span className="text-amber-200">
                  {guild.missingRequired.length > 0
                    ? `${guild.missingRequired.length} required field(s) missing`
                    : "Setup incomplete"}
                </span>
              </>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
