import { NextRequest, NextResponse } from "next/server";
import { apiBaseUrl } from "@/lib/api";

export async function POST(request: NextRequest) {
  // Same-origin browser use; this local research app has no public authentication boundary.
  const origin = request.headers.get("origin");
  if (origin && new URL(origin).host !== request.headers.get("host")) {
    return NextResponse.json({ detail: "Cross-origin scan requests are not allowed" }, { status: 403 });
  }
  try {
    const body = await request.json();
    const response = await fetch(`${apiBaseUrl}/api/screen/breakouts`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      signal: AbortSignal.timeout(120000), cache: "no-store",
    });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Could not complete scan. Check the backend connection." }, { status: 502 });
  }
}
