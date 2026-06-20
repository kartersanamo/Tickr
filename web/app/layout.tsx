import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tickr — Discord Ticket Bot",
  description: "Modern Discord ticket management with a beautiful web dashboard.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="site-bg antialiased">{children}</body>
    </html>
  );
}
