"use client";

interface RecommendedChannel {
  id: string;
  title: string;
  desc: string;
  badge: string;
  bg: string;
}

interface VideoPlayerProps {
  channels: RecommendedChannel[];
  currentIndex: number;
  isFocused: boolean;
}

export default function VideoPlayer({ channels, currentIndex, isFocused }: VideoPlayerProps) {
  if (channels.length === 0) return null;

  const channel = channels[currentIndex] ?? channels[0];
  const showLeftArrow = currentIndex > 0;
  const showRightArrow = currentIndex < channels.length - 1;

  return (
    <div
      className="relative w-full h-full rounded-2xl overflow-hidden"
      style={{
        transition: "box-shadow 0.3s ease",
        boxShadow: isFocused
          ? "0 0 0 2px rgba(0,230,118,0.5), 0 0 60px rgba(0,230,118,0.10), 0 8px 40px rgba(0,0,0,0.6)"
          : "0 8px 40px rgba(0,0,0,0.6)",
      }}
    >
      {/* 동적 배경 그라디언트 */}
      <div
        className="absolute inset-0"
        style={{
          background: `linear-gradient(145deg, ${channel.bg} 0%, #050510 100%)`,
          transition: "background 0.7s ease",
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-r from-black/65 via-transparent to-black/25" />
      <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/85" />
      {/* 스캔라인 텍스처 */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,1) 2px, rgba(255,255,255,1) 3px)",
        }}
      />

      {/* 콘텐츠 */}
      <div className="relative z-10 h-full flex flex-col justify-between p-8 pt-6">
        {/* 상단: 라이브 배지 */}
        <div className="flex items-center gap-3">
          {channel.badge && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold text-white bg-red-600">
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
              {channel.badge}
            </span>
          )}
          <span className="text-white/50 text-sm font-light tracking-wide">{channel.title}</span>
        </div>

        {/* 중앙: 채널명 */}
        <div className="flex items-center justify-center">
          <div className="text-center">
            <div className="text-8xl mb-6 drop-shadow-2xl select-none">📺</div>
            <h2
              className="text-white font-bold tracking-tight drop-shadow-xl"
              style={{ fontSize: "clamp(1.8rem, 3vw, 3rem)" }}
            >
              {channel.title}
            </h2>
            <p className="text-white/45 text-lg mt-3 font-light tracking-wide">{channel.desc}</p>
          </div>
        </div>

        {/* 하단: 페이지네이션 */}
        <div className="flex flex-col items-center gap-3">
          <div className="flex items-center gap-2">
            {channels.map((_, i) => (
              <span
                key={i}
                className="block h-[3px] rounded-full"
                style={{
                  width: i === currentIndex ? "2rem" : "0.5rem",
                  background:
                    i === currentIndex ? "rgba(0,230,118,0.9)" : "rgba(255,255,255,0.25)",
                  transition: "width 0.35s ease, background 0.35s ease",
                }}
              />
            ))}
          </div>
          <p
            className="text-white/25 text-xs tracking-wider"
            style={{ opacity: isFocused ? 1 : 0, transition: "opacity 0.3s ease" }}
          >
            ← → 채널 전환 &nbsp;·&nbsp; ↓ 쇼핑 목록
          </p>
        </div>
      </div>

      {/* 좌측 화살표 */}
      {showLeftArrow && (
        <div className="absolute left-5 top-1/2 -translate-y-1/2 z-20">
          <div
            className="w-14 h-14 rounded-full flex items-center justify-center text-white text-3xl font-thin"
            style={{
              background: "rgba(0,0,0,0.45)",
              border: isFocused
                ? "1.5px solid rgba(0,230,118,0.5)"
                : "1.5px solid rgba(255,255,255,0.15)",
              backdropFilter: "blur(8px)",
              boxShadow: isFocused ? "0 0 14px rgba(0,230,118,0.2)" : "none",
              transition: "border-color 0.3s ease, box-shadow 0.3s ease",
            }}
          >
            ‹
          </div>
        </div>
      )}

      {/* 우측 화살표 */}
      {showRightArrow && (
        <div className="absolute right-5 top-1/2 -translate-y-1/2 z-20">
          <div
            className="w-14 h-14 rounded-full flex items-center justify-center text-white text-3xl font-thin"
            style={{
              background: "rgba(0,0,0,0.45)",
              border: isFocused
                ? "1.5px solid rgba(0,230,118,0.5)"
                : "1.5px solid rgba(255,255,255,0.15)",
              backdropFilter: "blur(8px)",
              boxShadow: isFocused ? "0 0 14px rgba(0,230,118,0.2)" : "none",
              transition: "border-color 0.3s ease, box-shadow 0.3s ease",
            }}
          >
            ›
          </div>
        </div>
      )}
    </div>
  );
}
