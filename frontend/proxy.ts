import { NextRequest, NextResponse } from "next/server";
import { checkAccess } from "@/lib/basic-auth";

export function proxy(request: NextRequest) {
  const decision = checkAccess(request.headers.get("authorization"), {
    required: process.env.REQUIRE_AUTH === "true",
    username: process.env.SCREENER_USER,
    password: process.env.SCREENER_PASSWORD,
  });
  if (decision === "unconfigured") {
    return new NextResponse("Website access credentials are not configured.", {
      status: 503, headers: { "Cache-Control": "no-store" },
    });
  }
  if (decision === "challenge") {
    return new NextResponse("Sign in to Basecamp Research.", {
      status: 401,
      headers: { "WWW-Authenticate": 'Basic realm="Basecamp Research", charset="UTF-8"', "Cache-Control": "no-store" },
    });
  }
  const response = NextResponse.next();
  if (process.env.REQUIRE_AUTH === "true" || process.env.SCREENER_PASSWORD) {
    response.headers.set("Cache-Control", "private, no-store");
  }
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/web-health$).*)"],
};
