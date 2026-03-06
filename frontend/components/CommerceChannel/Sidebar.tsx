"use client";

import { useEffect, useState } from "react";

interface SidebarProps {
  menus: string[];
  activeIndex: number;
  isSectionFocused: boolean;
}

const MENU_ICONS: Record<string, string> = {
  "실시간 추천 채널": "▶",
  VOD: "⬛",
  키즈: "★",
  영화: "▣",
  스포츠: "◆",
  쇼핑: "◉",
  약정: "▤",
};

export default function Sidebar({ menus, activeIndex, isSectionFocused }: SidebarProps) {
  const [timeStr, setTimeStr] = useState("");

  useEffect(() => {
    const update = () =>
      setTimeStr(new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" }));
    update();
    const id = setInterval(update, 30000);
    return () => clearInterval(id);
  }, []);

  return (
    <aside
      className="w-56 h-full flex flex-col shrink-0 border-r border-white/[0.05]"
      style={{ background: "linear-gradient(180deg, #0d0d22 0%, #080814 100%)" }}
    >
      {/* 로고 */}
      <div className="px-5 pt-5 pb-4 border-b border-white/[0.05] shrink-0">
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: "linear-gradient(135deg, #00e676 0%, #00b0ff 100%)" }}
          >
            <span className="text-black text-[10px] font-black leading-none">0</span>
          </div>
          <div className="min-w-0">
            <p className="text-white text-[13px] font-bold tracking-wider leading-tight">
              쇼핑TV
            </p>
            <p className="text-tv-muted text-[9px] tracking-[0.2em] mt-0.5">CH 0 · COMMERCE</p>
          </div>
        </div>
      </div>

      {/* 메뉴 */}
      <nav className="flex-1 flex flex-col px-2.5 py-4 gap-0.5">
        {menus.map((menu, idx) => {
          const isFocused = isSectionFocused && activeIndex === idx;
          const isActive = activeIndex === idx;
          return (
            <div
              key={menu}
              className="relative flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-default select-none"
              style={{
                transition: "background 0.2s ease, box-shadow 0.2s ease",
                background: isFocused
                  ? "rgba(0, 230, 118, 0.10)"
                  : isActive
                  ? "rgba(255,255,255,0.06)"
                  : "transparent",
                outline: isFocused ? "1.5px solid rgba(0, 230, 118, 0.55)" : "none",
                outlineOffset: "1px",
                boxShadow: isFocused ? "0 0 18px rgba(0, 230, 118, 0.15)" : "none",
              }}
            >
              {isActive && !isFocused && (
                <span
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] rounded-r-full"
                  style={{
                    height: "60%",
                    background: "linear-gradient(180deg, #00e676, #00b0ff)",
                  }}
                />
              )}
              <span
                className="text-[11px] w-4 text-center shrink-0 font-bold"
                style={{
                  color: isFocused ? "#00e676" : isActive ? "#ffffff" : "#7070a0",
                  transition: "color 0.2s ease",
                }}
              >
                {MENU_ICONS[menu] ?? "▶"}
              </span>
              <span
                className="truncate text-[13px] font-medium leading-none"
                style={{
                  color: isFocused ? "#00e676" : isActive ? "#ffffff" : "#7070a0",
                  transition: "color 0.2s ease",
                }}
              >
                {menu}
              </span>
            </div>
          );
        })}
      </nav>

      {/* 하단 시계 */}
      <div className="px-5 py-4 border-t border-white/[0.05] shrink-0">
        <p className="text-white/60 text-sm font-light tabular-nums">{timeStr}</p>
        <p
          className="text-tv-muted text-[10px] mt-1 leading-none"
          style={{ opacity: isSectionFocused ? 1 : 0, transition: "opacity 0.3s ease" }}
        >
          ↑ ↓ 메뉴 이동 &nbsp;·&nbsp; → 영상
        </p>
      </div>
    </aside>
  );
}
