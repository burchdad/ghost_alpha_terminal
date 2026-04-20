import { NextResponse } from "next/server";

export function GET(request: Request) {
  const url = new URL("/images/security-shield.svg", request.url);
  return NextResponse.redirect(url, 307);
}
