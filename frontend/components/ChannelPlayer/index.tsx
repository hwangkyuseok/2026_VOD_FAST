"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { Channel } from "@/lib/api";
import AdOverlay from "@/components/AdOverlay";
import ShoppingOverlay from "@/components/ShoppingOverlay";

interface Props {
  channel: Channel;
  onChannelChange: (delta: number) => void;
  userId: string;
}

export default function ChannelPlayer({ channel, onChannelChange, userId }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isZapping, setIsZapping] = useState(false);
  const [showChannelBadge, setShowChannelBadge] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const badgeTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 채널 전환 시 Zapping 효과
  useEffect(() => {
    setIsZapping(true);
    setShowChannelBadge(true);

    const timer = setTimeout(() => {
      setIsZapping(false);
      if (videoRef.current && channel.stream_url) {
        videoRef.current.load();
        videoRef.current.play().catch(() => {});
      }
    }, 500);

    // 채널 번호 배지 3초 후 숨김
    if (badgeTimerRef.current) clearTimeout(badgeTimerRef.current);
    badgeTimerRef.current = setTimeout(() => setShowChannelBadge(false), 3000);

    return () => clearTimeout(timer);
  }, [channel.channel_no]);

  // 키보드 채널 제어
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowUp") onChannelChange(1);
      if (e.key === "ArrowDown") onChannelChange(-1);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onChannelChange]);

  const handleTimeUpdate = useCallback(() => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  }, []);

  return (
    <div
      className="relative w-full h-full bg-black overflow-hidden scanline tv-glow"
      style={{ borderRadius: "4px" }}
    >
      {/* Zapping 블러 효과 */}
      {isZapping && (
        <div className="absolute inset-0 bg-black z-50 animate-zap-blur flex items-center justify-center">
          <div className="text-white text-4xl font-bold">{channel.channel_no}</div>
        </div>
      )}

      {/* 채널 배경색 (스트림 없을 때) */}
      {!channel.stream_url && (
        <div
          className="absolute inset-0 flex flex-col items-center justify-center"
          style={{ backgroundColor: channel.channel_color || "#1a1a2e" }}
        >
          <div className="text-white/60 text-lg font-semibold">{channel.channel_nm}</div>
          <div className="text-white/40 text-sm mt-2">{channel.category}</div>
          <div className="text-white/30 text-xs mt-4">스트림 준비 중...</div>
        </div>
      )}

      {/* 비디오 플레이어 */}
      {channel.stream_url && (
        <video
          ref={videoRef}
          className="w-full h-full object-cover"
          autoPlay
          muted
          loop
          playsInline
          onTimeUpdate={handleTimeUpdate}
        >
          <source src={channel.stream_url} type="application/x-mpegURL" />
          <source src={channel.stream_url} />
        </video>
      )}

      {/* 채널 번호 배지 */}
      {showChannelBadge && (
        <div className="channel-badge animate-channel-switch">
          <span className="text-tv-muted text-xs">CH</span>
          <span className="ml-1 text-xl">{channel.channel_no}</span>
          <div className="text-tv-muted text-xs mt-0.5">{channel.channel_nm}</div>
        </div>
      )}

      {/* 광고 오버레이 (트랙1 VOD 전용, 채널에서는 비활성) */}

      {/* 쇼핑 오버레이 */}
      <ShoppingOverlay
        channelCategory={channel.category}
        currentTime={currentTime}
        userId={userId}
      />

      {/* 채널 Up/Down 버튼 */}
      <div className="absolute left-2 top-1/2 -translate-y-1/2 flex flex-col gap-2 opacity-0 hover:opacity-100 transition-opacity">
        <button
          onClick={() => onChannelChange(1)}
          className="bg-black/60 text-white p-2 rounded-lg hover:bg-black/80 transition-colors text-sm"
        >
          ▲
        </button>
        <button
          onClick={() => onChannelChange(-1)}
          className="bg-black/60 text-white p-2 rounded-lg hover:bg-black/80 transition-colors text-sm"
        >
          ▼
        </button>
      </div>
    </div>
  );
}
