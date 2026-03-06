"use client";

import { useState, useEffect, useCallback, useRef } from "react";

export type Zone = "sidebar" | "video" | "shopping";

export interface FocusState {
  zone: Zone;
  sidebarIndex: number;
  videoIndex: number;
  shoppingIndex: number;
}

interface UseRemoteFocusOptions {
  menuCount: number;
  channelCount: number;
  productCount: number;
  isSidebarVisible: boolean;
  onEnterProduct?: (index: number) => void;
  onEnterMenu?: (index: number) => void;
  isTrapped?: boolean;
}

export function useRemoteFocus({
  menuCount,
  channelCount,
  productCount,
  isSidebarVisible,
  onEnterProduct,
  onEnterMenu,
  isTrapped = false,
}: UseRemoteFocusOptions) {
  const [focus, setFocus] = useState<FocusState>({
    zone: "video",
    sidebarIndex: 0,
    videoIndex: 0,
    shoppingIndex: 0,
  });

  const focusRef = useRef(focus);
  focusRef.current = focus;

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (isTrapped) return;
      const f = focusRef.current;

      switch (e.key) {
        case "ArrowUp": {
          e.preventDefault();
          if (f.zone === "sidebar") {
            setFocus((prev) => ({ ...prev, sidebarIndex: Math.max(0, prev.sidebarIndex - 1) }));
          } else if (f.zone === "shopping") {
            setFocus((prev) => ({ ...prev, zone: "video" }));
          }
          break;
        }
        case "ArrowDown": {
          e.preventDefault();
          if (f.zone === "sidebar") {
            setFocus((prev) => ({ ...prev, sidebarIndex: Math.min(menuCount - 1, prev.sidebarIndex + 1) }));
          } else if (f.zone === "video") {
            setFocus((prev) => ({ ...prev, zone: "shopping" }));
          }
          break;
        }
        case "ArrowLeft": {
          e.preventDefault();
          if (f.zone === "video") {
            if (f.videoIndex > 0) {
              setFocus((prev) => ({ ...prev, videoIndex: prev.videoIndex - 1 }));
            } else if (isSidebarVisible) {
              setFocus((prev) => ({ ...prev, zone: "sidebar" }));
            }
          } else if (f.zone === "shopping") {
            setFocus((prev) => ({ ...prev, shoppingIndex: Math.max(0, prev.shoppingIndex - 1) }));
          }
          break;
        }
        case "ArrowRight": {
          e.preventDefault();
          if (f.zone === "sidebar") {
            setFocus((prev) => ({ ...prev, zone: "video" }));
          } else if (f.zone === "video") {
            if (f.videoIndex < channelCount - 1) {
              setFocus((prev) => ({ ...prev, videoIndex: prev.videoIndex + 1 }));
            }
          } else if (f.zone === "shopping") {
            setFocus((prev) => ({ ...prev, shoppingIndex: Math.min(productCount - 1, prev.shoppingIndex + 1) }));
          }
          break;
        }
        case "Enter": {
          e.preventDefault();
          if (f.zone === "shopping") {
            onEnterProduct?.(f.shoppingIndex);
          } else if (f.zone === "sidebar") {
            onEnterMenu?.(f.sidebarIndex);
            setFocus((prev) => ({ ...prev, zone: "video" }));
          }
          break;
        }
      }
    },
    [isTrapped, menuCount, channelCount, productCount, isSidebarVisible, onEnterProduct, onEnterMenu]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return { focus, setFocus };
}
