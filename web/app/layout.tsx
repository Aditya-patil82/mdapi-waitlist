import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Turn Any Web Page Into AI-Ready Markdown",
  description:
    "A simple API that converts web pages into clean, structured Markdown for AI agents, RAG pipelines, and LLM applications.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} min-h-screen bg-neutral-950 text-neutral-100 font-sans antialiased selection:bg-neutral-800 selection:text-neutral-100`}
      >
        {children}
      </body>
    </html>
  );
}
