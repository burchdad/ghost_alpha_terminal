import { NextRequest, NextResponse } from "next/server";

const AUTH_COOKIE = "ghost_auth_session";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/dashboard")) {
    const hasSessionCookie = Boolean(request.cookies.get(AUTH_COOKIE)?.value);
    if (!hasSessionCookie) {
      const url = request.nextUrl.clone();
      url.pathname = "/login";
      url.searchParams.set("next", pathname || "/dashboard");
      return NextResponse.redirect(url);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*"],
};
