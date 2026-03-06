"""YOLO + CLIP 기반 비전 분석 — 씬 키프레임에서 객체·컨텍스트 태그 추출.

2026_ADWARE services/analyzer/vision.py 패턴 반영:
- YOLO: 객체 감지 (기존 유지)
- CLIP: 의미적 컨텍스트 태그 추출 추가 (openai/clip-vit-base-patch32)
  → CLIP이 없거나 로드 실패 시 YOLO만으로 graceful fallback
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

log = structlog.get_logger()

# CLIP 컨텍스트 태그 (광고 타겟팅용 — 2026_ADWARE와 동일)
CONTEXT_TAGS: List[str] = [
    "outdoor", "indoor", "sports", "food", "technology", "fashion",
    "travel", "nature", "people", "vehicle", "music", "entertainment",
    "news", "education", "cooking", "gaming", "fitness", "beauty",
    "business", "animal",
]

_yolo_model = None
_clip_model = None
_clip_processor = None


def _load_yolo():
    global _yolo_model
    if _yolo_model is None:
        from ultralytics import YOLO
        model_path = os.environ.get("YOLO_MODEL_PATH", "yolov8n.pt")
        log.info("yolo.loading", model=model_path)
        _yolo_model = YOLO(model_path)
        log.info("yolo.loaded")
    return _yolo_model


def _load_clip() -> Optional[tuple]:
    """CLIP 모델 로드. CLIP_ENABLED=false 또는 로드 실패 시 None 반환."""
    global _clip_model, _clip_processor
    if os.environ.get("CLIP_ENABLED", "true").lower() == "false":
        return None
    if _clip_model is None:
        try:
            from transformers import CLIPModel, CLIPProcessor
            model_name = os.environ.get("CLIP_MODEL", "openai/clip-vit-base-patch32")
            log.info("clip.loading", model=model_name)
            _clip_processor = CLIPProcessor.from_pretrained(model_name)
            _clip_model = CLIPModel.from_pretrained(model_name)
            _clip_model.eval()
            log.info("clip.loaded")
        except Exception as e:
            log.warning("clip.load_failed", error=str(e))
            return None
    if _clip_model is None:
        return None
    return _clip_model, _clip_processor


def analyze_keyframe(keyframe_path: str) -> Dict[str, Any]:
    """키프레임 이미지에서 YOLO 객체 감지 + CLIP 컨텍스트 태그 추출.

    Args:
        keyframe_path: 씬 대표 키프레임 이미지 경로

    Returns:
        {
          "objects": [...],           # YOLO 감지 객체 레이블
          "clip_tags": [...],         # CLIP 의미적 컨텍스트 태그 (옵션)
          "dominant_colors": [...],   # 주요 색상 HEX
          "vision_tags": [...]        # objects + clip_tags 통합 태그 (광고 프롬프트용)
        }
    """
    if not Path(keyframe_path).exists():
        log.warning("vision.no_keyframe", path=keyframe_path)
        return {"objects": [], "clip_tags": [], "dominant_colors": [], "vision_tags": []}

    objects = _detect_objects(keyframe_path)
    clip_tags = _analyze_clip(keyframe_path)
    dominant_colors = _extract_dominant_colors(keyframe_path)

    # vision_tags: YOLO 객체 + CLIP 태그 통합 (중복 제거, 최대 10개)
    combined = list(dict.fromkeys(objects + clip_tags))[:10]

    return {
        "objects": objects,
        "clip_tags": clip_tags,
        "dominant_colors": dominant_colors,
        "vision_tags": combined,
    }


def _detect_objects(image_path: str) -> List[str]:
    """YOLO 객체 감지."""
    try:
        confidence = float(os.environ.get("VISION_CONFIDENCE_THRESHOLD", "0.5"))
        model = _load_yolo()
        results = model(image_path, verbose=False, conf=confidence)
        labels: List[str] = []
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                label = result.names[class_id]
                if label not in labels:
                    labels.append(label)
        return labels
    except Exception as e:
        log.warning("yolo.detect_failed", error=str(e))
        return []


def _analyze_clip(image_path: str, top_k: int = 5) -> List[str]:
    """CLIP으로 이미지-텍스트 유사도 기반 컨텍스트 태그 추출 (2026_ADWARE 패턴).

    CLIP 미사용(CLIP_ENABLED=false) 또는 로드 실패 시 빈 리스트 반환.
    """
    clip_pair = _load_clip()
    if clip_pair is None:
        return []
    model, processor = clip_pair

    try:
        import torch
        from PIL import Image

        image = Image.open(image_path).convert("RGB")
        inputs = processor(
            text=CONTEXT_TAGS,
            images=image,
            return_tensors="pt",
            padding=True,
        )
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits_per_image[0]
            probs = logits.softmax(dim=0)

        top_indices = probs.argsort(descending=True)[:top_k].tolist()
        return [CONTEXT_TAGS[i] for i in top_indices]
    except Exception as e:
        log.warning("clip.analyze_failed", error=str(e))
        return []


def _extract_dominant_colors(image_path: str, num_colors: int = 3) -> List[str]:
    """이미지 주요 색상 HEX 추출."""
    try:
        from PIL import Image
        image = Image.open(image_path).convert("RGB").resize((100, 100))
        pixels = list(image.getdata())
        buckets: dict = {}
        for r, g, b in pixels:
            key = (r // 64 * 64, g // 64 * 64, b // 64 * 64)
            buckets[key] = buckets.get(key, 0) + 1
        top = sorted(buckets.items(), key=lambda x: x[1], reverse=True)[:num_colors]
        return [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), _ in top]
    except Exception as e:
        log.warning("color.extract_failed", error=str(e))
        return []
