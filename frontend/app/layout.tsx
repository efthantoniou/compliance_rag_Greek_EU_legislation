import type { Metadata } from "next";
import {
  GFS_Didot,
  IBM_Plex_Sans,
  JetBrains_Mono,
  Literata,
} from "next/font/google";
import "./globals.css";

// Every face here ships a `greek` unicode-range — see DESIGN.md, which treats
// that as a hard gate rather than a preference. The app renders Greek EUROVOC
// labels and Greek legislative bodies, so a Latin-only face means the corpus
// silently falls back to a system font. Geist Mono, which this file used to
// load, offers only cyrillic/latin/latin-ext.
const display = GFS_Didot({
  weight: "400",
  subsets: ["greek", "latin"],
  variable: "--ff-display",
});

const body = Literata({
  subsets: ["greek", "latin"],
  variable: "--ff-body",
});

const ui = IBM_Plex_Sans({
  weight: ["400", "500", "600"],
  subsets: ["greek", "latin"],
  variable: "--ff-ui",
});

const mono = JetBrains_Mono({
  subsets: ["greek", "latin"],
  variable: "--ff-mono",
});

export const metadata: Metadata = {
  title: "Compliance RAG",
  description: "Greek EU legislation retrieval",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="el"
      className={`${display.variable} ${body.variable} ${ui.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-background font-body text-foreground">
        <div className="mx-auto max-w-3xl px-4 py-8">{children}</div>
      </body>
    </html>
  );
}
