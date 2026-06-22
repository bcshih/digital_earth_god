import type { Metadata } from "next";
import { Noto_Serif_TC, Noto_Sans_TC, Space_Mono } from "next/font/google";
import "./globals.css";

// Divine voice / headings — weighty, tracked.
const notoSerifTC = Noto_Serif_TC({
  variable: "--font-noto-serif-tc",
  weight: ["500", "700", "900"],
  display: "swap",
  preload: false,
});

// Body.
const notoSansTC = Noto_Sans_TC({
  variable: "--font-noto-sans-tc",
  weight: ["400", "500", "700"],
  display: "swap",
  preload: false,
});

// Contract Net telemetry, scores, agent ids.
const spaceMono = Space_Mono({
  variable: "--font-space-mono",
  weight: ["400", "700"],
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "數位土地公 · Divine-Tech Explore",
  description:
    "A2UI reference renderer — divine negotiation as luminous ritual. 神・科技。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-Hant"
      className={`${notoSerifTC.variable} ${notoSansTC.variable} ${spaceMono.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
