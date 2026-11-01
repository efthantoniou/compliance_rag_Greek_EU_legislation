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

// Follow the OS light/dark setting, including changes while the page is open.
// globals.css defines the dark tokens under `.dark`.
const FOLLOW_SYSTEM_THEME = `(function(){try{var m=window.matchMedia("(prefers-color-scheme: dark)");var a=function(){document.documentElement.classList.toggle("dark",m.matches)};a();m.addEventListener("change",a)}catch(e){}})()`;

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
    // The inline script picks the theme before first paint, so the server's
    // class list is corrected on the client; suppressHydrationWarning accepts it.
    <html
      lang="el"
      suppressHydrationWarning
      className={`${display.variable} ${body.variable} ${ui.variable} ${mono.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: FOLLOW_SYSTEM_THEME }} />
      </head>
      <body className="min-h-full bg-background font-body text-foreground">
        <div className="mx-auto max-w-3xl px-4 py-8">{children}</div>
      </body>
    </html>
  );
}
