"use client";

import { useEffect, useCallback, useState } from "react";
import type { CommerceProduct } from "./ShoppingRow";

interface PurchaseModalProps {
  product: CommerceProduct;
  onClose: () => void;
}

const MODAL_BUTTONS = ["주문하기", "닫기"];

function formatPrice(price: number): string {
  return price.toLocaleString("ko-KR") + "원";
}

export default function PurchaseModal({ product, onClose }: PurchaseModalProps) {
  const [focusedBtn, setFocusedBtn] = useState(0);
  const [ordered, setOrdered] = useState(false);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      switch (e.key) {
        case "ArrowLeft":
          e.preventDefault();
          setFocusedBtn((p) => Math.max(0, p - 1));
          break;
        case "ArrowRight":
          e.preventDefault();
          setFocusedBtn((p) => Math.min(MODAL_BUTTONS.length - 1, p + 1));
          break;
        case "Enter":
          e.preventDefault();
          if (focusedBtn === 0) {
            setOrdered(true);
            setTimeout(onClose, 1500);
          } else {
            onClose();
          }
          break;
        case "Escape":
          e.preventDefault();
          onClose();
          break;
      }
    },
    [focusedBtn, onClose]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75">
      <div
        className="relative rounded-2xl overflow-hidden p-6 w-full max-w-xl"
        style={{ background: "#0f0f22", border: "1px solid rgba(255,255,255,0.1)" }}
      >
        <h2 className="text-white text-xl font-bold text-center mb-5">
          상품을 확인하고 주문을 진행해주세요
        </h2>

        {/* 상품 정보 */}
        <div
          className="rounded-xl p-4 flex items-center gap-4 mb-5"
          style={{ background: "rgba(255,255,255,0.06)" }}
        >
          <div
            className="w-20 h-20 rounded-lg flex items-center justify-center text-4xl shrink-0"
            style={{ background: "rgba(255,255,255,0.08)" }}
          >
            {product.thumbnail_url ? (
              <img src={product.thumbnail_url} alt={product.name} className="w-full h-full object-cover rounded-lg" />
            ) : (
              "🛍️"
            )}
          </div>
          <div>
            <p className="text-white text-sm font-medium leading-snug">{product.name}</p>
            <p className="text-tv-focus text-lg font-bold mt-1">{formatPrice(product.price)}</p>
          </div>
        </div>

        {/* 버튼 */}
        <div className="flex gap-3 justify-center">
          {MODAL_BUTTONS.map((label, idx) => (
            <button
              key={label}
              className={[
                "px-8 py-3 rounded-full text-sm font-semibold transition-all duration-150",
                focusedBtn === idx
                  ? idx === 0
                    ? "bg-tv-focus text-black tv-focused"
                    : "bg-white/20 text-white tv-focused"
                  : idx === 0
                  ? "bg-tv-focus/30 text-tv-focus"
                  : "bg-white/10 text-white/60",
              ].join(" ")}
            >
              {ordered && idx === 0 ? "✓ 주문완료!" : label}
            </button>
          ))}
        </div>

        <p className="text-center text-tv-muted text-xs mt-3">
          ← → 버튼 이동 &nbsp;|&nbsp; Enter 선택 &nbsp;|&nbsp; ESC 닫기
        </p>
      </div>
    </div>
  );
}
