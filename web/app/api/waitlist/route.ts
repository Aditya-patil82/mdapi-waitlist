import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { getSupabaseAdmin } from "@/lib/supabase";

// In-memory rate limiting map: ip -> array of request timestamps
const rateLimitMap = new Map<string, number[]>();
const RATE_LIMIT_WINDOW_MS = 60 * 1000; // 1 minute
const MAX_REQUESTS_PER_WINDOW = 5;

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const timestamps = rateLimitMap.get(ip) || [];

  // Filter out timestamps outside the active window
  const activeTimestamps = timestamps.filter(
    (timestamp) => now - timestamp < RATE_LIMIT_WINDOW_MS
  );

  if (activeTimestamps.length >= MAX_REQUESTS_PER_WINDOW) {
    rateLimitMap.set(ip, activeTimestamps);
    return true;
  }

  activeTimestamps.push(now);
  rateLimitMap.set(ip, activeTimestamps);
  return false;
}

const waitlistSchema = z.object({
  email: z
    .string()
    .min(1, { message: "Email is required" })
    .trim()
    .toLowerCase()
    .email({ message: "Please provide a valid email address" }),
  honeypot: z.string().optional(),
});

export async function POST(req: NextRequest) {
  try {
    // 1. Determine IP address for rate limiting
    const forwardedFor = req.headers.get("x-forwarded-for");
    const realIp = req.headers.get("x-real-ip");
    const clientIp = forwardedFor
      ? forwardedFor.split(",")[0].trim()
      : realIp || "127.0.0.1";

    if (isRateLimited(clientIp)) {
      return NextResponse.json(
        { ok: false, message: "Too many requests. Please try again in a minute." },
        { status: 429 }
      );
    }

    // 2. Parse and validate payload
    const body = await req.json().catch(() => null);
    if (!body) {
      return NextResponse.json(
        { ok: false, message: "Invalid JSON request body." },
        { status: 400 }
      );
    }

    const parseResult = waitlistSchema.safeParse(body);
    if (!parseResult.success) {
      const firstIssue = parseResult.error.issues?.[0]?.message || "Invalid input";
      return NextResponse.json({ ok: false, message: firstIssue }, { status: 400 });
    }

    const { email, honeypot } = parseResult.data;

    // 3. Honeypot check: reject bots silently
    if (honeypot && honeypot.trim() !== "") {
      // Return success without storing
      return NextResponse.json({
        ok: true,
        message: "You're on the list! We'll be in touch soon.",
      });
    }

    // 4. Insert into Supabase table `waitlist`
    let supabase;
    try {
      supabase = getSupabaseAdmin();
    } catch (e: any) {
      console.error("Supabase configuration error:", e);
      return NextResponse.json(
        { ok: false, message: "Server database configuration is missing." },
        { status: 500 }
      );
    }

    const { error } = await supabase.from("waitlist").insert([{ email }]);

    if (error) {
      // Postgres error 23505 is unique violation (duplicate email)
      if (error.code === "23505" || error.message?.includes("duplicate")) {
        // Return success to prevent email enumeration
        return NextResponse.json({
          ok: true,
          message: "You're on the list! We'll be in touch soon.",
        });
      }

      console.error("Supabase insert error:", error);
      return NextResponse.json(
        { ok: false, message: "Failed to join waitlist. Please try again later." },
        { status: 500 }
      );
    }

    return NextResponse.json({
      ok: true,
      message: "You're on the list! We'll be in touch soon.",
    });
  } catch (error: any) {
    console.error("Waitlist API handler error:", error);
    return NextResponse.json(
      { ok: false, message: "An unexpected error occurred. Please try again." },
      { status: 500 }
    );
  }
}
