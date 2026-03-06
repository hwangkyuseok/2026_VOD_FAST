const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const NLP_API_URL = process.env.NEXT_PUBLIC_NLP_API_URL || "http://localhost:8001";

export interface Channel {
  channel_no: number;
  channel_nm: string;
  category: string;
  stream_url?: string;
  logo_url?: string;
  channel_color: string;
  is_active: string;
  sort_order: number;
}

export interface VodMeta {
  asset_id: string;
  title?: string;
  genre?: string;
  description?: string;
  thumbnail_url?: string;
  duration_sec?: number;
  rating?: number;
  view_count?: number;
  is_free_yn: string;
  fast_ad_eligible_yn: string;
}

export interface WeeklyVod {
  rank_no: number;
  asset_id: string;
  week_start_ymd: string;
  selection_score?: number;
  selection_reason?: string;
  ad_pipeline_status: string;
  title?: string;
  genre?: string;
  thumbnail_url?: string;
  duration_sec?: number;
}

export interface RecommendResult {
  asset_id: string;
  score: number;
  reason: string;
  title?: string;
  genre?: string;
  thumbnail_url?: string;
  is_kids: boolean;
}

export interface InsertionPoint {
  timestamp_sec: number;
  confidence: number;
  insert_reason?: string;
  display_duration_sec: number;
  display_position: string;
  ad_type?: string;
  file_path?: string;
}

export interface Product {
  prod_cd: string;
  prod_nm?: string;
  category?: string;
  price?: number;
  thumbnail_url?: string;
  match_score?: number;
}

export interface CommerceRecommendedChannel {
  id: string;
  title: string;
  desc: string;
  badge: string;
  bg: string;
}

export interface CommerceProduct {
  id: string;
  name: string;
  price: number;
  thumbnail_url?: string;
  is_rental?: boolean;
  category?: string;
}

export interface CommerceData {
  menus: string[];
  recommendedChannels: CommerceRecommendedChannel[];
  products: CommerceProduct[];
}

async function fetchApi<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) throw new Error(`API 오류: ${res.status} ${url}`);
  return res.json();
}

export const api = {
  channels: {
    list: () => fetchApi<Channel[]>(`${API_URL}/api/v1/channels`),
    get: (no: number) => fetchApi<Channel>(`${API_URL}/api/v1/channels/${no}`),
  },
  vod: {
    weekly: (week?: string) =>
      fetchApi<WeeklyVod[]>(`${API_URL}/api/v1/vod/weekly${week ? `?week=${week}` : ""}`),
    free: (genre?: string, limit = 20) =>
      fetchApi<VodMeta[]>(`${API_URL}/api/v1/vod/free?limit=${limit}${genre ? `&genre=${genre}` : ""}`),
    get: (id: string) => fetchApi<VodMeta>(`${API_URL}/api/v1/vod/${id}`),
  },
  ad: {
    insertionPoints: (assetId: string) =>
      fetchApi<InsertionPoint[]>(`${API_URL}/api/v1/ad/insertion-points/${assetId}`),
  },
  shopping: {
    match: (keywords: string, limit = 5) =>
      fetchApi<Product[]>(`${API_URL}/api/v1/shopping/match?keywords=${encodeURIComponent(keywords)}&limit=${limit}`),
  },
  nlp: {
    recommend: (userId: string, topN = 10) =>
      fetchApi<RecommendResult[]>(`${NLP_API_URL}/admin/recommend`, {
        method: "POST",
        body: JSON.stringify({ user_id: userId, top_n: topN }),
      }),
    updateProfile: (userId: string) =>
      fetchApi(`${NLP_API_URL}/admin/update_user_profile?user_id=${encodeURIComponent(userId)}`, {
        method: "POST",
      }),
  },
  commerce: {
    data: (limit = 20) =>
      fetchApi<CommerceData>(`${API_URL}/api/v1/commerce/data?limit=${limit}`),
  },
  sessions: {
    start: (data: { user_id: string; session_type: string; channel_no?: number; asset_id?: string }) =>
      fetchApi(`${API_URL}/api/v1/sessions/start`, { method: "POST", body: JSON.stringify(data) }),
    end: (sessionId: string, data: { watch_sec?: number; ad_impression_count?: number }) =>
      fetchApi(`${API_URL}/api/v1/sessions/${sessionId}/end`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  },
};
