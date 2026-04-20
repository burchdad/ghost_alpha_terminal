import { NextRequest, NextResponse } from "next/server";

const AUTH_COOKIE = "ghost_auth_session";

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/alpha") ||
    pathname.startsWith("/terminal") ||
    pathname.startsWith("/brokerages")
  ) {
    const hasSessionCookie = Boolean(request.cookies.get(AUTH_COOKIE)?.value);
    if (!hasSessionCookie) {
      const url = request.nextUrl.clone();
      url.pathname = "/login";
      url.searchParams.set("next", `${pathname}${search}` || "/dashboard");
      return NextResponse.redirect(url);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/alpha/:path*", "/terminal/:path*", "/brokerages/:path*"],
};
