import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        "tv-bg": "#0a0a1a",
        "tv-surface": "#1a1a2e",
        "tv-panel": "#111128",
        "tv-card": "#1a1a35",
        "tv-primary": "#6c5ce7",
        "tv-accent": "#00b894",
        "tv-focus": "#00e676",
        "tv-text": "#e2e8f0",
        "tv-muted": "#64748b",
        "tv-kids": "#27ae60",
        "tv-news": "#c0392b",
        "tv-movie": "#2c3e50",
      },
      fontFamily: {
        sans: ["Noto Sans KR", "system-ui", "sans-serif"],
      },
      animation: {
        "channel-switch": "channelSwitch 0.3s ease-out",
        "ad-slide-up": "adSlideUp 0.4s ease-out",
        "shop-pulse": "shopPulse 2s infinite",
        "zap-blur": "zapBlur 0.5s ease-out",
      },
      keyframes: {
        channelSwitch: {
          "0%": { opacity: "0", transform: "scale(0.98)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        adSlideUp: {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shopPulse: {
          "0%, 100%": { opacity: "0.8" },
          "50%": { opacity: "1" },
        },
        zapBlur: {
          "0%": { filter: "blur(4px)", opacity: "0" },
          "100%": { filter: "blur(0)", opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
