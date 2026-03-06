"""생성형 AI 기반 FAST 광고 에셋 생성 — 이미지 및 무음 비디오."""
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

log = structlog.get_logger()

AD_ASSET_DIR = os.environ.get("AD_ASSET_DIR", "/app/data/ad_assets")


def keywords_to_prompt(keywords: List[str], ad_type: str = "IMAGE") -> str:
    """비전 키워드를 생성형 AI 프롬프트로 변환."""
    kw_str = ", ".join(keywords[:5]) if keywords else "lifestyle product"
    if ad_type == "IMAGE":
        return (
            f"High-quality product advertisement photo featuring {kw_str}. "
            "Clean background, professional lighting, Korean e-commerce style, "
            "vibrant colors, no text overlay."
        )
    else:  # VIDEO_SILENT
        return (
            f"Silent short-form video advertisement showing {kw_str}. "
            "3-5 seconds, smooth transitions, product showcase style, "
            "no audio, no text, Korean shopping channel aesthetic."
        )


def generate_image_ad(
    keywords: List[str],
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """이미지 광고 에셋 생성 (OpenAI DALL-E 또는 mock).

    Returns:
        {"file_path", "width_px", "height_px", "provider", "model", "prompt"}
    """
    api_key = os.environ.get("IMAGE_GEN_API_KEY", "")
    api_url = os.environ.get("IMAGE_GEN_API_URL", "")
    prompt = keywords_to_prompt(keywords, "IMAGE")

    if not output_path:
        Path(AD_ASSET_DIR).mkdir(parents=True, exist_ok=True)
        output_path = str(Path(AD_ASSET_DIR) / f"img_{uuid.uuid4().hex}.png")

    if api_key and api_url:
        result = _call_image_api(api_key, api_url, prompt, output_path)
    else:
        log.warning("ad_generator.image: API 키 미설정 — 플레이스홀더 사용")
        result = _create_placeholder_image(output_path, keywords)

    result["prompt"] = prompt
    return result


def generate_video_ad(
    keywords: List[str],
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """무음 숏폼 비디오 광고 에셋 생성.

    Returns:
        {"file_path", "duration_sec", "width_px", "height_px", "provider", "model", "prompt"}
    """
    api_key = os.environ.get("VIDEO_GEN_API_KEY", "")
    api_url = os.environ.get("VIDEO_GEN_API_URL", "")
    prompt = keywords_to_prompt(keywords, "VIDEO_SILENT")

    if not output_path:
        Path(AD_ASSET_DIR).mkdir(parents=True, exist_ok=True)
        output_path = str(Path(AD_ASSET_DIR) / f"vid_{uuid.uuid4().hex}.mp4")

    if api_key and api_url:
        result = _call_video_api(api_key, api_url, prompt, output_path)
    else:
        log.warning("ad_generator.video: API 키 미설정 — 플레이스홀더 사용")
        result = _create_placeholder_video(output_path)

    result["prompt"] = prompt
    return result


def _call_image_api(api_key: str, api_url: str, prompt: str, output_path: str) -> Dict[str, Any]:
    """OpenAI DALL-E 3 API 호출."""
    try:
        import httpx
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "url",
        }
        response = httpx.post(api_url, json=payload, headers=headers, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        image_url = data["data"][0]["url"]

        # 이미지 다운로드
        img_response = httpx.get(image_url, timeout=60.0)
        img_response.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(img_response.content)

        file_size = Path(output_path).stat().st_size
        log.info("image_ad.generated", path=output_path, size=file_size)
        return {
            "file_path": output_path,
            "width_px": 1024,
            "height_px": 1024,
            "provider": "OPENAI",
            "model": "dall-e-3",
            "file_size_bytes": file_size,
        }
    except Exception as e:
        log.error("image_api.failed", error=str(e))
        return _create_placeholder_image(output_path, [])


def _call_video_api(api_key: str, api_url: str, prompt: str, output_path: str) -> Dict[str, Any]:
    """영상 생성 API 호출 (RunwayML / Kling 등)."""
    try:
        import httpx
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"prompt": prompt, "duration": 4, "ratio": "16:9"}
        response = httpx.post(api_url, json=payload, headers=headers, timeout=120.0)
        response.raise_for_status()
        data = response.json()
        video_url = data.get("output") or data.get("url") or data.get("video_url")

        if video_url:
            vid_response = httpx.get(video_url, timeout=120.0)
            vid_response.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(vid_response.content)

        file_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0
        return {
            "file_path": output_path,
            "duration_sec": 4.0,
            "width_px": 1280,
            "height_px": 720,
            "provider": "VIDEO_API",
            "model": "generic",
            "file_size_bytes": file_size,
        }
    except Exception as e:
        log.error("video_api.failed", error=str(e))
        return _create_placeholder_video(output_path)


def _create_placeholder_image(output_path: str, keywords: List[str]) -> Dict[str, Any]:
    """API 없을 때 플레이스홀더 이미지 생성 (PIL)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (1024, 1024), color=(30, 30, 60))
        draw = ImageDraw.Draw(img)
        kw_text = ", ".join(keywords[:3]) if keywords else "광고 에셋"
        draw.text((512, 480), f"[FAST AD]\n{kw_text}", fill=(255, 255, 255), anchor="mm")
        img.save(output_path)
        file_size = Path(output_path).stat().st_size
    except Exception:
        Path(output_path).write_bytes(b"")
        file_size = 0

    return {
        "file_path": output_path,
        "width_px": 1024,
        "height_px": 1024,
        "provider": "PLACEHOLDER",
        "model": "PIL",
        "file_size_bytes": file_size,
    }


def _create_placeholder_video(output_path: str) -> Dict[str, Any]:
    """API 없을 때 4초 무음 플레이스홀더 비디오 생성 (ffmpeg)."""
    try:
        import ffmpeg
        (
            ffmpeg.input("color=c=black:size=1280x720:rate=30", f="lavfi", t=4)
            .output(output_path, vcodec="libx264", an=None)
            .overwrite_output()
            .run(quiet=True)
        )
        file_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0
    except Exception as e:
        log.warning("placeholder_video.failed", error=str(e))
        Path(output_path).write_bytes(b"")
        file_size = 0

    return {
        "file_path": output_path,
        "duration_sec": 4.0,
        "width_px": 1280,
        "height_px": 720,
        "provider": "PLACEHOLDER",
        "model": "ffmpeg",
        "file_size_bytes": file_size,
    }
