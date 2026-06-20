import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { tickrFetch } from "@/lib/api-client";
import { DashboardNav } from "@/components/dashboard-nav";
import { ConfigEditor } from "@/components/config-editor";

type Props = { params: Promise<{ guildId: string }> };

export default async function GuildConfigPage({ params }: Props) {
  const session = await auth();
  if (!session?.user) redirect("/login");
  const { guildId } = await params;
  let schema;
  let config;
  let summary;
  try {
    [schema, config, summary] = await Promise.all([
      tickrFetch(`/guilds/${guildId}/config/schema`),
      tickrFetch(`/guilds/${guildId}/config`),
      tickrFetch(`/guilds/${guildId}`),
    ]);
  } catch {
    redirect("/dashboard");
  }

  return (
    <div className="min-h-screen">
      <DashboardNav user={session.user} guildId={guildId} guildName={summary.name} />
      <main className="mx-auto max-w-4xl px-6 py-10">
        <h1 className="mb-2 text-3xl font-bold">Configuration</h1>
        <p className="mb-8 text-[var(--text-secondary)]">Edit Tickr settings for {summary.name}.</p>
        <ConfigEditor
          guildId={guildId}
          categories={schema.categories}
          fields={schema.fields}
          initialValues={config.values}
          missingRequired={config.missingRequired || []}
        />
      </main>
    </div>
  );
}
