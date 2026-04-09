import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "GHOST ALPHA TERMINAL",
  description: "AI-powered trading intelligence platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
