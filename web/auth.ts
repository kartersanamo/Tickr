import NextAuth from "next-auth";
import Discord from "next-auth/providers/discord";

declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
    };
    accessToken?: string;
    guilds?: Array<{ id: string; name: string; permissions: string; icon?: string | null }>;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    guilds?: Array<{ id: string; name: string; permissions: string; icon?: string | null }>;
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Discord({
      clientId: process.env.DISCORD_CLIENT_ID!,
      clientSecret: process.env.DISCORD_CLIENT_SECRET!,
      authorization: {
        params: { scope: "identify guilds" },
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account?.access_token) {
        token.accessToken = account.access_token;
        try {
          const resp = await fetch("https://discord.com/api/users/@me/guilds", {
            headers: { Authorization: `Bearer ${account.access_token}` },
          });
          if (resp.ok) {
            const guilds = await resp.json();
            token.guilds = guilds.map((g: { id: string; name: string; permissions: string; icon?: string | null }) => ({
              id: g.id,
              name: g.name,
              permissions: g.permissions,
              icon: g.icon,
            }));
          }
        } catch {
          token.guilds = [];
        }
        if (profile && "id" in profile) {
          token.sub = String(profile.id);
        }
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user && token.sub) {
        session.user.id = token.sub;
      }
      session.accessToken = token.accessToken;
      session.guilds = token.guilds;
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
  trustHost: true,
});
