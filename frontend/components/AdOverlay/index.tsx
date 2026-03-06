"use client";

import { useEffect, useState, useRef } from "react";
import { api, type InsertionPoint } from "@/lib/api";

interface Props {
  assetId: string;
  currentTime: number;
  onAdImpression?: () => void;
}

export default function AdOverlay({ assetId, currentTime, onAdImpression }: Props) {
  const [insertionPoints, setInsertionPoints] = useState<InsertionPoint[]>([]);
  const [activeAd, setActiveAd] = useState<InsertionPoint | null>(null);
  const [adVisible, setAdVisible] = useState(false);
  const triggeredRef = useRef<Set<number>>(new Set());
  const adTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!assetId) return;
    api.ad.insertionPoints(assetId).then(setInsertionPoints).catch(() => {});
  }, [assetId]);

  // 타임스탬프 도달 시 광고 표시
  useEffect(() => {
    for (const point of insertionPoints) {
      const ts = Math.round(point.timestamp_sec);
      const ct = Math.round(currentTime);
      if (ct === ts && !triggeredRef.current.has(ts)) {
        triggeredRef.current.add(ts);
        setActiveAd(point);
        setAdVisible(true);
        onAdImpression?.();

        if (adTimerRef.current) clearTimeout(adTimerRef.current);
        adTimerRef.current = setTimeout(() => {
          setAdVisible(false);
          setActiveAd(null);
        }, point.display_duration_sec * 1000);
        break;
      }
    }
  }, [currentTime, insertionPoints, onAdImpression]);

  if (!adVisible || !activeAd) return null;

  return (
    <div className="ad-overlay z-40">
      <div className="bg-black/80 backdrop-blur-sm rounded-xl p-3 flex items-center gap-3 border border-white/10 animate-ad-slide-up">
        {/* 광고 이미지 */}
        <div className="w-16 h-16 bg-tv-surface rounded-lg overflow-hidden flex-shrink-0">
          {activeAd.ad_type === "IMAGE" && activeAd.file_path ? (
            <img
              src={`/api/ad-asset?path=${encodeURIComponent(activeAd.file_path)}`}
              alt="광고"
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full bg-tv-primary/30 flex items-center justify-center text-xs text-white/60">
              AD
            </div>
          )}
        </div>
        {/* 광고 텍스트 */}
        <div className="flex-1 min-w-0">
          <div className="text-xs text-tv-muted mb-0.5">FAST 광고</div>
          <div className="text-sm text-white font-medium">
            {activeAd.ad_type === "VIDEO_SILENT" ? "무음 숏폼 광고" : "상품 광고"}
          </div>
          <div className="text-xs text-tv-muted mt-0.5">
            {Math.round(activeAd.display_duration_sec)}초 후 종료
          </div>
        </div>
        {/* 닫기 버튼 */}
        <button
          onClick={() => { setAdVisible(false); setActiveAd(null); }}
          className="text-white/40 hover:text-white transition-colors text-lg leading-none"
        >
          ×
        </button>
      </div>
    </div>
  );
}
