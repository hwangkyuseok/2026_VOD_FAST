"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api, type Channel } from "@/lib/api";
import ChannelPlayer from "@/components/ChannelPlayer";
import CommerceChannel from "@/components/CommerceChannel";

// 0번 채널 — TV 커머스 (2026_TV_COMMERCE 통합)
const VIRTUAL_CH0: Channel = {
  channel_no: 0,
  channel_nm: "HV 쇼핑TV",
  category: "SHOPPING",
  channel_color: "#00e676",
  is_active: "Y",
  sort_order: 0,
};

export default function ChannelPage() {
  const router = useRouter();
  const [dbChannels, setDbChannels] = useState<Channel[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0); // 0 = 0번채널(커머스) ← 기본값
  const [showGuide, setShowGuide] = useState(false);
  const [userId, setUserId] = useState("");

  useEffect(() => {
    const uid = localStorage.getItem("tv_user_id");
    if (!uid) { router.push("/setup"); return; }
    setUserId(uid);
    api.channels.list().then(setDbChannels).catch(console.error);
  }, [router]);

  // 전체 채널 배열: [CH0(커머스), CH1, CH2, ..., CH30]
  const allChannels = [VIRTUAL_CH0, ...dbChannels];

  const handleChannelChange = useCallback((delta: number) => {
    setCurrentIdx((prev) => {
      const next = prev + delta;
      if (next < 0) return allChannels.length - 1;
      if (next >= allChannels.length) return 0;
      return next;
    });
    setShowGuide(false);
  }, [allChannels.length]);

  const currentChannel = allChannels[currentIdx];

  // 일반 채널 전용: L 키로 편성표 토글, ESC로 닫기
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (currentIdx === 0) return; // 0번 채널에서는 무시
      if (e.key === "l" || e.key === "L") {
        setShowGuide((v) => !v);
      }
      if (e.key === "Escape") {
        setShowGuide(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [currentIdx]);

  if (!currentChannel) {
    return (
      <div className="fixed inset-0 bg-tv-bg flex items-center justify-center">
        <div className="text-tv-muted animate-pulse">채널 로딩 중...</div>
      </div>
    );
  }

  const isCommerceChannel = currentChannel.channel_no === 0;

  return (
    <div className="fixed inset-0 bg-tv-bg flex flex-col">
      {/* 메인 플레이어 영역 */}
      <div className="flex-1 relative overflow-hidden">
        {isCommerceChannel ? (
          <CommerceChannel onChannelChange={handleChannelChange} />
        ) : (
          <ChannelPlayer
            channel={currentChannel}
            onChannelChange={handleChannelChange}
            userId={userId}
          />
        )}
      </div>

      {/* 하단 컨트롤 바: 0번 채널에서만 표시 */}
      {isCommerceChannel && (
        <div className="bg-tv-surface/90 backdrop-blur-sm border-t border-white/5 px-4 py-2 flex items-center justify-between">
          {/* 채널 정보 */}
          <div className="flex items-center gap-3">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: currentChannel.channel_color }}
            />
            <span className="text-tv-text font-medium text-sm">
              CH {currentChannel.channel_no} — {currentChannel.channel_nm}
            </span>
            <span className="text-tv-muted text-xs px-2 py-0.5 bg-tv-bg rounded">
              {currentChannel.category}
            </span>
            <span className="text-tv-muted text-xs opacity-60">
              B키: 사이드바 &nbsp;·&nbsp; Enter: 상품선택
            </span>
          </div>

          {/* 컨트롤 버튼 */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => router.push("/vod")}
              className="text-tv-muted hover:text-tv-text text-xs px-3 py-1.5 rounded-lg hover:bg-tv-bg transition-colors"
            >
              VOD
            </button>
            <div className="flex gap-1">
              <button
                onClick={() => handleChannelChange(1)}
                className="bg-tv-bg text-white px-2 py-1.5 rounded text-xs hover:bg-tv-primary transition-colors"
                title="채널 올리기 (▲)"
              >
                ▲
              </button>
              <button
                onClick={() => handleChannelChange(-1)}
                className="bg-tv-bg text-white px-2 py-1.5 rounded text-xs hover:bg-tv-primary transition-colors"
                title="채널 내리기 (▼)"
              >
                ▼
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 일반 채널: L키 편성표 안내 배지 */}
      {!isCommerceChannel && (
        <div
          className="fixed bottom-3 right-4 z-20 flex items-center gap-2 px-3 py-1.5 rounded-full text-[11px]"
          style={{
            background: "rgba(0,0,0,0.45)",
            border: "1px solid rgba(255,255,255,0.08)",
            backdropFilter: "blur(8px)",
            color: "#7070a0",
          }}
        >
          <span>채널 편성표</span>
          <kbd
            className="px-1.5 py-0.5 rounded text-[10px] font-mono"
            style={{ background: "rgba(255,255,255,0.1)", color: "#a0a0c0" }}
          >
            L
          </kbd>
        </div>
      )}

      {/* 채널 편성표 오버레이 (일반 채널, L키) */}
      {showGuide && !isCommerceChannel && (
        <div className="absolute inset-0 bg-black/80 backdrop-blur-sm z-50 flex">
          <div className="w-80 bg-tv-surface h-full overflow-y-auto">
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
              <h2 className="font-bold text-tv-text">채널 편성표</h2>
              <div className="flex items-center gap-2">
                <kbd
                  className="px-2 py-0.5 rounded text-[10px] font-mono text-tv-muted"
                  style={{ background: "rgba(255,255,255,0.08)" }}
                >
                  ESC
                </kbd>
                <button onClick={() => setShowGuide(false)} className="text-tv-muted hover:text-white">×</button>
              </div>
            </div>
            <div className="p-2">
              {/* 0번 채널 */}
              <button
                onClick={() => { setCurrentIdx(0); setShowGuide(false); }}
                className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors ${
                  currentIdx === 0 ? "bg-tv-primary/20 text-tv-text" : "hover:bg-tv-bg text-tv-muted"
                }`}
              >
                <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: VIRTUAL_CH0.channel_color }} />
                <span className="text-sm font-mono w-6">0</span>
                <span className="text-sm flex-1 truncate">{VIRTUAL_CH0.channel_nm}</span>
                <span className="text-xs text-tv-muted">{VIRTUAL_CH0.category}</span>
              </button>
              {/* DB 채널들 */}
              {dbChannels.map((ch, idx) => (
                <button
                  key={ch.channel_no}
                  onClick={() => { setCurrentIdx(idx + 1); setShowGuide(false); }}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors ${
                    currentIdx === idx + 1 ? "bg-tv-primary/20 text-tv-text" : "hover:bg-tv-bg text-tv-muted"
                  }`}
                >
                  <div
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ backgroundColor: ch.channel_color }}
                  />
                  <span className="text-sm font-mono w-6">{ch.channel_no}</span>
                  <span className="text-sm flex-1 truncate">{ch.channel_nm}</span>
                  <span className="text-xs text-tv-muted">{ch.category}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
