import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HV TV — 차세대 미디어 플랫폼",
  description: "케이블 TV 셋탑박스 에뮬레이터 — FAST 광고 + 실시간 쇼핑",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="bg-tv-bg text-tv-text antialiased select-none">
        {children}
      </body>
    </html>
  );
}
