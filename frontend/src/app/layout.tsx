"use client";

import type Metadata from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Business Flow Skill",
  description: "AI-driven business process knowledge management",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh">
      <body>{children}</body>
    </html>
  );
}