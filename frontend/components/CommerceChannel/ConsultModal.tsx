"use client";

import { useEffect, useCallback, useState, useRef } from "react";
import type { CommerceProduct } from "./ShoppingRow";

interface ConsultModalProps {
  product: CommerceProduct;
  onClose: () => void;
}

const BOTTOM_BUTTONS = ["kakao", "sms", "close"] as const;
type BottomBtn = (typeof BOTTOM_BUTTONS)[number];
type FocusArea = "input" | "save" | BottomBtn;
const FOCUS_ORDER: FocusArea[] = ["input", "save", "kakao", "sms", "close"];

const BUTTON_LABELS: Record<BottomBtn, string> = {
  kakao: "카카오톡 전송",
  sms: "문자전송",
  close: "닫기",
};

export default function ConsultModal({ product, onClose }: ConsultModalProps) {
  const [phone, setPhone] = useState("010");
  const [saveNumber, setSaveNumber] = useState(false);
  const [focusArea, setFocusArea] = useState<FocusArea>("input");
  const [sent, setSent] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (focusArea === "input") inputRef.current?.focus();
    else inputRef.current?.blur();
  }, [focusArea]);

  const moveFocus = useCallback(
    (dir: "prev" | "next") => {
      const idx = FOCUS_ORDER.indexOf(focusArea);
      if (dir === "next" && idx < FOCUS_ORDER.length - 1) setFocusArea(FOCUS_ORDER[idx + 1]);
      else if (dir === "prev" && idx > 0) setFocusArea(FOCUS_ORDER[idx - 1]);
    },
    [focusArea]
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (focusArea === "input") {
        if (e.key >= "0" && e.key <= "9") {
          setPhone((p) => (p.length < 11 ? p + e.key : p));
          return;
        }
        if (e.key === "Backspace") {
          setPhone((p) => p.slice(0, -1));
          return;
        }
      }
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          moveFocus("next");
          break;
        case "ArrowUp":
          e.preventDefault();
          moveFocus("prev");
          break;
        case "ArrowLeft":
          e.preventDefault();
          if (BOTTOM_BUTTONS.includes(focusArea as BottomBtn)) {
            const idx = BOTTOM_BUTTONS.indexOf(focusArea as BottomBtn);
            if (idx > 0) setFocusArea(BOTTOM_BUTTONS[idx - 1] as FocusArea);
          }
          break;
        case "ArrowRight":
          e.preventDefault();
          if (BOTTOM_BUTTONS.includes(focusArea as BottomBtn)) {
            const idx = BOTTOM_BUTTONS.indexOf(focusArea as BottomBtn);
            if (idx < BOTTOM_BUTTONS.length - 1) setFocusArea(BOTTOM_BUTTONS[idx + 1] as FocusArea);
          }
          break;
        case "Enter":
          e.preventDefault();
          if (focusArea === "save") setSaveNumber((p) => !p);
          else if (focusArea === "kakao" || focusArea === "sms") {
            setSent(true);
            setTimeout(onClose, 1500);
          } else if (focusArea === "close") onClose();
          else if (focusArea === "input") moveFocus("next");
          break;
        case "Escape":
          e.preventDefault();
          onClose();
          break;
      }
    },
    [focusArea, moveFocus, onClose]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
      <div
        className="relative rounded-2xl p-6 w-full max-w-sm"
        style={{
          background: "#111128",
          border: "1px solid rgba(255,255,255,0.15)",
          boxShadow: "0 0 40px rgba(0,0,0,0.8)",
        }}
      >
        <p className="text-center text-white text-sm font-medium mb-2 leading-relaxed">
          입력하신 휴대폰 번호로
          <br />
          주문정보를 전달드립니다
        </p>
        <p className="text-center text-tv-muted text-xs mb-4 truncate px-2">{product.name}</p>

        {/* 전화번호 입력 */}
        <div
          className={[
            "rounded-lg px-4 py-3 mb-3 transition-all duration-150",
            focusArea === "input" ? "tv-focused bg-white/15" : "bg-white/10",
          ].join(" ")}
        >
          <input
            ref={inputRef}
            type="text"
            value={phone}
            readOnly
            className="w-full bg-transparent text-white text-lg font-mono outline-none"
            placeholder="010"
          />
        </div>

        {/* 번호 저장 체크박스 */}
        <div
          className={[
            "flex items-center gap-2 px-2 py-2 rounded-lg mb-4 cursor-pointer transition-all duration-150",
            focusArea === "save" ? "tv-focused bg-white/10" : "",
          ].join(" ")}
        >
          <div
            className={[
              "w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors",
              saveNumber ? "border-tv-focus bg-tv-focus" : "border-white/40",
            ].join(" ")}
          >
            {saveNumber && <span className="text-black text-xs font-bold">✓</span>}
          </div>
          <span className="text-white/80 text-sm">번호 저장</span>
        </div>

        {/* 액션 버튼 */}
        <div className="flex gap-2">
          {BOTTOM_BUTTONS.map((btn) => (
            <button
              key={btn}
              className={[
                "flex-1 py-3 rounded-xl text-sm font-semibold transition-all duration-150",
                focusArea === btn
                  ? btn === "close"
                    ? "bg-white/20 text-white tv-focused"
                    : "bg-tv-focus text-black tv-focused"
                  : btn === "close"
                  ? "bg-white/10 text-white/60"
                  : "bg-white/10 text-white/70",
              ].join(" ")}
            >
              {sent && (btn === "kakao" || btn === "sms") ? "✓ 전송완료" : BUTTON_LABELS[btn]}
            </button>
          ))}
        </div>

        <p className="text-center text-tv-muted text-xs mt-3">
          ↑ ↓ 이동 &nbsp;|&nbsp; Enter 선택 &nbsp;|&nbsp; ESC 닫기
        </p>
      </div>
    </div>
  );
}
