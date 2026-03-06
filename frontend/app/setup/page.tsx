"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const PROFILE_OPTIONS = [
  { id: "family", label: "가족", icon: "👨‍👩‍👧‍👦", desc: "전 연령 콘텐츠 추천" },
  { id: "adult", label: "성인", icon: "🧑", desc: "성인 콘텐츠 중심" },
  { id: "kids", label: "어린이", icon: "🧒", desc: "키즈·애니메이션 중심" },
  { id: "senior", label: "시니어", icon: "👴", desc: "뉴스·다큐·트로트 중심" },
];

export default function SetupPage() {
  const router = useRouter();
  const [userId, setUserId] = useState("");
  const [selectedProfile, setSelectedProfile] = useState<string | null>(null);
  const [step, setStep] = useState<1 | 2>(1);

  const handleNext = () => {
    if (step === 1 && userId.trim()) {
      setStep(2);
    } else if (step === 2 && selectedProfile) {
      // localStorage에 유저 정보 저장
      localStorage.setItem("tv_user_id", userId.trim());
      localStorage.setItem("tv_profile", selectedProfile);
      // router.push("/channel");
      router.push("/vod");
    }
  };

  return (
    <div className="fixed inset-0 bg-tv-bg flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-lg space-y-8">
        {/* 헤더 */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-tv-primary">HV TV</h1>
          <p className="text-tv-muted mt-2">
            {step === 1 ? "사용자 ID를 입력하세요" : "시청 프로필을 선택하세요"}
          </p>
        </div>

        {/* 단계 표시 */}
        <div className="flex gap-2 justify-center">
          {[1, 2].map((s) => (
            <div
              key={s}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                s <= step ? "bg-tv-primary w-16" : "bg-tv-surface w-8"
              }`}
            />
          ))}
        </div>

        {/* Step 1: 유저 ID */}
        {step === 1 && (
          <div className="space-y-4">
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleNext()}
              placeholder="사용자 ID 입력"
              className="w-full bg-tv-surface border border-tv-primary/30 rounded-xl px-4 py-3 text-tv-text text-lg focus:outline-none focus:border-tv-primary transition-colors"
              autoFocus
            />
            <p className="text-tv-muted text-sm text-center">
              기존 가입 고객 ID 또는 원하는 닉네임을 입력하세요
            </p>
          </div>
        )}

        {/* Step 2: 프로필 선택 */}
        {step === 2 && (
          <div className="grid grid-cols-2 gap-4">
            {PROFILE_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                onClick={() => setSelectedProfile(opt.id)}
                className={`p-4 rounded-xl border-2 transition-all duration-200 text-left space-y-2 ${
                  selectedProfile === opt.id
                    ? "border-tv-primary bg-tv-primary/20"
                    : "border-tv-surface hover:border-tv-primary/50 bg-tv-surface"
                }`}
              >
                <div className="text-3xl">{opt.icon}</div>
                <div className="font-bold text-tv-text">{opt.label}</div>
                <div className="text-tv-muted text-sm">{opt.desc}</div>
              </button>
            ))}
          </div>
        )}

        {/* 버튼 */}
        <button
          onClick={handleNext}
          disabled={(step === 1 && !userId.trim()) || (step === 2 && !selectedProfile)}
          className="w-full py-3 rounded-xl bg-tv-primary text-white font-bold text-lg disabled:opacity-40 disabled:cursor-not-allowed hover:bg-tv-primary/80 transition-colors"
        >
          {step === 1 ? "다음" : "시청 시작"}
        </button>

        {step === 2 && (
          <button
            onClick={() => setStep(1)}
            className="w-full py-2 text-tv-muted hover:text-tv-text transition-colors text-sm"
          >
            뒤로
          </button>
        )}
      </div>
    </div>
  );
}
