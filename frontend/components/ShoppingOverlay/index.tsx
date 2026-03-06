"use client";

import { useEffect, useState, useRef } from "react";
import { api, type Product } from "@/lib/api";

const CATEGORY_KEYWORDS: Record<string, string> = {
  SHOPPING: "생활용품,주방,패션",
  LIFESTYLE: "인테리어,요리,뷰티",
  SPORTS: "스포츠,운동,헬스",
  MUSIC: "음악,악기",
  KIDS: "장난감,아동복,학습",
  FOOD: "식품,건강식품",
  DRAMA: "패션,뷰티,라이프스타일",
  MOVIE: "영화,엔터테인먼트",
  default: "생활용품,가전",
};

interface Props {
  channelCategory: string;
  currentTime: number;
  userId: string;
}

export default function ShoppingOverlay({ channelCategory, currentTime, userId }: Props) {
  const [products, setProducts] = useState<Product[]>([]);
  const [visible, setVisible] = useState(false);
  const [clickedIdx, setClickedIdx] = useState<number | null>(null);
  const fetchedRef = useRef(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // 30초마다 쇼핑 매칭 갱신
  useEffect(() => {
    if (Math.floor(currentTime) % 30 !== 0 || currentTime < 1) return;
    if (fetchedRef.current) {
      fetchedRef.current = false;
      return;
    }
    fetchedRef.current = true;

    const keywords = CATEGORY_KEYWORDS[channelCategory] || CATEGORY_KEYWORDS.default;
    api.shopping.match(keywords, 3).then((prods) => {
      if (prods.length > 0) {
        setProducts(prods);
        setVisible(true);
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => setVisible(false), 8000);
      }
    }).catch(() => {});
  }, [currentTime, channelCategory]);

  if (!visible || products.length === 0) return null;

  return (
    <div className="shopping-overlay z-30">
      {/* 쇼핑 라벨 */}
      <div className="text-xs text-tv-muted text-right mb-1 animate-shop-pulse">
        🛒 실시간 쇼핑
      </div>
      {products.map((prod, idx) => (
        <button
          key={prod.prod_cd}
          onClick={() => setClickedIdx(idx)}
          className={`bg-black/70 backdrop-blur-sm rounded-xl p-2.5 flex items-center gap-2.5 border transition-all duration-200 w-44 animate-ad-slide-up text-left ${
            clickedIdx === idx
              ? "border-tv-accent bg-tv-accent/20"
              : "border-white/10 hover:border-tv-accent/50"
          }`}
          style={{ animationDelay: `${idx * 100}ms` }}
        >
          {/* 상품 이미지 */}
          <div className="w-10 h-10 rounded-lg bg-tv-surface overflow-hidden flex-shrink-0">
            {prod.thumbnail_url ? (
              <img src={prod.thumbnail_url} alt={prod.prod_nm} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-lg">🛍️</div>
            )}
          </div>
          {/* 상품 정보 */}
          <div className="flex-1 min-w-0">
            <div className="text-xs text-white truncate">{prod.prod_nm || "상품"}</div>
            {prod.price && (
              <div className="text-tv-accent text-xs font-bold mt-0.5">
                {prod.price.toLocaleString("ko-KR")}원
              </div>
            )}
          </div>
        </button>
      ))}
      {/* 닫기 */}
      <button
        onClick={() => setVisible(false)}
        className="text-white/30 hover:text-white/60 text-xs transition-colors text-right w-full mt-1"
      >
        닫기 ×
      </button>
    </div>
  );
}
