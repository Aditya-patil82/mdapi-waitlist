"use client";

import React, { useState } from "react";

export default function WaitlistPage() {
  const [email, setEmail] = useState("");
  const [honeypot, setHoneypot] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!email || !email.includes("@")) {
      setStatus("error");
      setMessage("Please enter a valid email address.");
      return;
    }

    setStatus("loading");
    setMessage("");

    try {
      const res = await fetch("/api/waitlist", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, honeypot }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data.ok) {
        setStatus("error");
        setMessage(data.message || "Something went wrong. Please try again.");
      } else {
        setStatus("success");
        setMessage(data.message || "You're on the list! We'll notify you soon.");
        setEmail("");
      }
    } catch {
      setStatus("error");
      setMessage("Network error. Please check your connection and try again.");
    }
  };

  return (
    <main className="relative min-h-screen flex flex-col justify-between items-center px-4 py-12 md:py-20 overflow-hidden">
      {/* Subtle background ambient gradients */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[350px] bg-gradient-to-tr from-emerald-500/10 via-cyan-500/10 to-indigo-500/10 blur-3xl pointer-events-none -z-10 rounded-full" />
      
      {/* Header bar */}
      <header className="w-full max-w-4xl flex items-center justify-between pb-8">
        <div className="flex items-center space-x-2">
          <div className="h-3 w-3 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-sm font-semibold tracking-wider uppercase text-neutral-400">
            MdAPI
          </span>
        </div>
        <div className="text-xs font-mono px-3 py-1 rounded-full bg-neutral-900 border border-neutral-800 text-neutral-400">
          v0.1 Private Beta
        </div>
      </header>

      {/* Main hero section */}
      <div className="w-full max-w-2xl my-auto text-center flex flex-col items-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-neutral-800 bg-neutral-900/80 backdrop-blur-sm text-xs text-neutral-300 mb-8 shadow-sm">
          <span className="flex h-2 w-2 rounded-full bg-emerald-500" />
          <span>Fast, deterministic web extraction for LLMs</span>
        </div>

        {/* Headline */}
        <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-neutral-100 leading-[1.15] mb-6">
          Turn Any Web Page Into{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400">
            AI-Ready Markdown
          </span>
        </h1>

        {/* Subheadline */}
        <p className="text-base sm:text-lg text-neutral-400 max-w-xl mb-10 leading-relaxed">
          A simple API that converts web pages into clean, structured Markdown for AI agents,
          RAG pipelines, and LLM applications.
        </p>

        {/* Waitlist Form */}
        <form onSubmit={handleSubmit} className="w-full max-w-md space-y-3">
          {/* Honeypot field (hidden from real users) */}
          <div className="sr-only" aria-hidden="true">
            <label htmlFor="company_hp">Do not fill this out if you are human</label>
            <input
              id="company_hp"
              type="text"
              name="company_hp"
              tabIndex={-1}
              autoComplete="off"
              value={honeypot}
              onChange={(e) => setHoneypot(e.target.value)}
            />
          </div>

          <div className="flex flex-col sm:flex-row gap-2">
            <input
              id="email-input"
              type="email"
              required
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={status === "loading"}
              className="flex-1 px-4 py-3 rounded-xl bg-neutral-900/90 border border-neutral-800 text-neutral-100 placeholder-neutral-500 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all disabled:opacity-50"
            />
            <button
              id="submit-btn"
              type="submit"
              disabled={status === "loading"}
              className="px-6 py-3 rounded-xl bg-neutral-100 hover:bg-neutral-200 text-neutral-950 text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg active:scale-[0.98]"
            >
              {status === "loading" ? (
                <>
                  <svg
                    className="animate-spin -ml-1 mr-1 h-4 w-4 text-neutral-950"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  <span>Submitting...</span>
                </>
              ) : (
                "Join Private Beta"
              )}
            </button>
          </div>

          {/* Inline Feedback States */}
          {status === "success" && (
            <div
              id="waitlist-success"
              className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 text-xs text-center animate-in fade-in duration-200"
            >
              {message}
            </div>
          )}

          {status === "error" && (
            <div
              id="waitlist-error"
              className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs text-center animate-in fade-in duration-200"
            >
              {message}
            </div>
          )}
        </form>

        {/* Feature Highlights Minimal Strip */}
        <div className="mt-14 grid grid-cols-1 sm:grid-cols-3 gap-4 w-full text-left">
          <div className="p-4 rounded-xl bg-neutral-900/40 border border-neutral-900 backdrop-blur-xs">
            <p className="text-xs font-semibold text-neutral-300 mb-1">🚀 Clean Output</p>
            <p className="text-xs text-neutral-500">Stripped of navigation, ads, cookies, and boilerplate.</p>
          </div>
          <div className="p-4 rounded-xl bg-neutral-900/40 border border-neutral-900 backdrop-blur-xs">
            <p className="text-xs font-semibold text-neutral-300 mb-1">🛡️ SSRF Protected</p>
            <p className="text-xs text-neutral-500">Hop-by-hop IP validation & private subnet isolation.</p>
          </div>
          <div className="p-4 rounded-xl bg-neutral-900/40 border border-neutral-900 backdrop-blur-xs">
            <p className="text-xs font-semibold text-neutral-300 mb-1">⚡ Token Bounded</p>
            <p className="text-xs text-neutral-500">Accurate token calculation and paragraph truncation.</p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="w-full max-w-4xl text-center text-xs text-neutral-600 pt-8 border-t border-neutral-900">
        © 2026 MdAPI. Built for AI engineers and autonomous workflows.
      </footer>
    </main>
  );
}
