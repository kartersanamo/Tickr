export const theme = {
  accent: "#5865F2",
  accentHover: "#4752C4",
  bgPrimary: "#000000",
  bgSecondary: "#0a0a0a",
  bgTertiary: "#141414",
  border: "#2a2a2a",
  textPrimary: "#f9fafb",
  textSecondary: "#d1d5db",
  textMuted: "#9ca3af",
} as const;

export const siteConfig = {
  name: "Tickr",
  tagline: "Modern Discord ticket management for your server.",
  description:
    "Tickr is a multi-guild Discord ticket bot with setup wizards, transcripts, staff tools, and a web dashboard.",
  url: process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000",
  inviteUrl:
    process.env.NEXT_PUBLIC_BOT_INVITE_URL ||
    "https://discord.com/oauth2/authorize?client_id=1517000402208293026&permissions=268823744&scope=bot%20applications.commands",
  features: [
    {
      title: "Quick Setup",
      description: "Run /setup in Discord or configure everything from the web dashboard.",
    },
    {
      title: "Ticket Panels",
      description: "Beautiful ticket menus with categories, custom questions, and private modes.",
    },
    {
      title: "Staff Tools",
      description: "Close, rename, move, add, remove, and privatize tickets without leaving Discord.",
    },
    {
      title: "Transcripts",
      description: "Automatic ticket logs with duration, reason, and transcript links.",
    },
    {
      title: "Web Dashboard",
      description: "Manage config, ticket types, and live tickets from tickr.kartersanamo.com.",
    },
    {
      title: "Multi-Guild",
      description: "One bot, many servers — each with its own independent configuration.",
    },
  ],
};
