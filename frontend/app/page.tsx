"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function BootPage() {
  const router = useRouter();
  const [phase, setPhase] = useState<"boot" | "profile">("boot");
  const [dotCount, setDotCount] = useState(0);

  useEffect(() => {
    const dotTimer = setInterval(() => setDotCount((d) => (d + 1) % 4), 400);
    const bootTimer = setTimeout(() => {
      clearInterval(dotTimer);
      setPhase("profile");
    }, 2500);
    return () => {
      clearInterval(dotTimer);
      clearTimeout(bootTimer);
    };
  }, []);

  useEffect(() => {
    if (phase === "profile") {
      // 프로필 설정 화면으로 이동
      router.push("/setup");
    }
  }, [phase, router]);

  return (
    <div className="fixed inset-0 bg-tv-bg flex flex-col items-center justify-center">
      <div className="text-center space-y-6">
        {/* HV 로고 */}
        <div className="text-6xl font-bold text-tv-primary tracking-wider tv-glow px-8 py-4 rounded-2xl border border-tv-primary/30">
          HV TV
        </div>
        <p className="text-tv-muted text-lg">차세대 미디어 플랫폼</p>
        {/* 부팅 인디케이터 */}
        <div className="flex items-center gap-2 text-tv-muted text-sm mt-8">
          <div className="w-2 h-2 rounded-full bg-tv-accent animate-ping" />
          <span>시스템 초기화 중{".".repeat(dotCount)}</span>
        </div>
        {/* 진행 바 */}
        <div className="w-64 h-1 bg-tv-surface rounded-full overflow-hidden">
          <div
            className="h-full bg-tv-primary transition-all duration-300"
            style={{ width: `${(dotCount / 3) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}
