"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useRemoteFocus } from "@/hooks/useRemoteFocus";
import Sidebar from "./Sidebar";
import VideoPlayer from "./VideoPlayer";
import ShoppingRow, { type CommerceProduct } from "./ShoppingRow";
import PurchaseModal from "./PurchaseModal";
import ConsultModal from "./ConsultModal";

interface RecommendedChannel {
  id: string;
  title: string;
  desc: string;
  badge: string;
  bg: string;
}

interface CommerceData {
  menus: string[];
  recommendedChannels: RecommendedChannel[];
  products: CommerceProduct[];
}

interface Props {
  onChannelChange: (delta: number) => void;
}

export default function CommerceChannel({ onChannelChange }: Props) {
  const router = useRouter();
  const [data, setData] = useState<CommerceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSidebarVisible, setIsSidebarVisible] = useState(true);
  const [modalProduct, setModalProduct] = useState<CommerceProduct | null>(null);

  // VOD 메뉴는 FIXED_MENUS index 1
  const VOD_MENU_INDEX = 1;

  useEffect(() => {
    api.commerce.data()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const isModalOpen = modalProduct !== null;
  const closeModal = useCallback(() => setModalProduct(null), []);

  const handleEnterProduct = useCallback(
    (index: number) => {
      if (!data) return;
      const product = data.products[index];
      if (product) setModalProduct(product);
    },
    [data]
  );

  // 사이드바 메뉴 Enter 처리: VOD → /vod, 나머지 → video 존
  const handleEnterMenu = useCallback(
    (index: number) => {
      if (index === VOD_MENU_INDEX) {
        router.push("/vod");
      }
      // 그 외 메뉴는 focus가 자동으로 video 존으로 이동 (useRemoteFocus 기본 동작)
    },
    [router]
  );

  const { focus } = useRemoteFocus({
    menuCount: data?.menus.length ?? 0,
    channelCount: data?.recommendedChannels.length ?? 0,
    productCount: data?.products.length ?? 0,
    isSidebarVisible,
    onEnterProduct: handleEnterProduct,
    onEnterMenu: handleEnterMenu,
    isTrapped: isModalOpen,
  });

  // 'B' 키: 사이드바 토글 (리모컨 뒤로/메뉴 버튼 시뮬레이션)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isModalOpen) return;
      // ArrowUp on video zone when video=0 → channel up (escape to CH1)
      if (e.key === "b" || e.key === "B") {
        setIsSidebarVisible((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isModalOpen]);

  if (loading) {
    return (
      <div className="flex items-center justify-center w-full h-full bg-tv-bg">
        <div className="text-center">
          <div className="text-5xl mb-4 select-none" style={{ animation: "pulse 2s infinite" }}>
            🛍️
          </div>
          <p className="text-tv-muted text-sm tracking-widest">쇼핑 채널 로딩 중...</p>
        </div>
      </div>
    );
  }

  if (!data || data.products.length === 0) {
    return (
      <div className="flex items-center justify-center w-full h-full bg-tv-bg">
        <div
          className="text-center px-10 py-8 rounded-2xl"
          style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <div className="text-4xl mb-4 select-none">📺</div>
          <p className="text-tv-muted text-sm">쇼핑 데이터를 불러올 수 없습니다.</p>
          <p className="text-tv-muted text-xs mt-2">채널▲ 버튼으로 다른 채널로 이동하세요.</p>
        </div>
      </div>
    );
  }

  const selectedMenu = data.menus[focus.sidebarIndex] ?? data.menus[0] ?? "";

  return (
    <div className="flex w-full h-full overflow-hidden bg-tv-bg">
      {/* 사이드바 */}
      <div
        className="shrink-0 overflow-hidden h-full"
        style={{
          width: isSidebarVisible ? "14rem" : "0",
          transition: "width 0.35s cubic-bezier(0.4, 0, 0.2, 1)",
        }}
      >
        <Sidebar
          menus={data.menus}
          activeIndex={focus.sidebarIndex}
          isSectionFocused={focus.zone === "sidebar"}
        />
      </div>

      {/* 우측 영역: VideoPlayer + ShoppingRow */}
      <div className="flex-1 flex flex-col min-w-0 p-4 gap-3 h-full overflow-hidden">
        <div className="flex-1 min-h-0">
          <VideoPlayer
            channels={data.recommendedChannels}
            currentIndex={focus.videoIndex}
            isFocused={focus.zone === "video"}
          />
        </div>
        <div className="shrink-0" style={{ height: "208px" }}>
          <ShoppingRow
            products={data.products}
            focusedIndex={focus.shoppingIndex}
            isFocused={focus.zone === "shopping"}
            onEnterProduct={handleEnterProduct}
          />
        </div>
      </div>

      {/* 포커스 존 표시 배지 */}
      <div
        className="fixed top-3 right-4 z-30 flex items-center gap-2 px-3 py-1.5 rounded-full text-[11px]"
        style={{
          background: "rgba(0,0,0,0.55)",
          border: "1px solid rgba(255,255,255,0.1)",
          backdropFilter: "blur(8px)",
          color: "#7070a0",
        }}
      >
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{
            background:
              focus.zone === "video"
                ? "#00e676"
                : focus.zone === "shopping"
                ? "#fb923c"
                : "#00b0ff",
            boxShadow: `0 0 6px ${
              focus.zone === "video"
                ? "rgba(0,230,118,0.8)"
                : focus.zone === "shopping"
                ? "rgba(251,146,60,0.8)"
                : "rgba(0,176,255,0.8)"
            }`,
          }}
        />
        <span>
          {selectedMenu}
          {!isSidebarVisible && " · 전체화면"}
        </span>
      </div>

      {/* 모달 */}
      {modalProduct &&
        (modalProduct.price >= 200_000 ? (
          <ConsultModal product={modalProduct} onClose={closeModal} />
        ) : (
          <PurchaseModal product={modalProduct} onClose={closeModal} />
        ))}
    </div>
  );
}
