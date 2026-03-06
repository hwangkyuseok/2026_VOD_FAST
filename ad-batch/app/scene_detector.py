"""PySceneDetect 기반 씬 분할 — 오디오 배제, 비디오 프레임 기반만 처리.

2026_ADWARE services/preprocessor/scene_detector.py 재사용.
"""
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

import structlog

log = structlog.get_logger()


@dataclass
class SceneSegment:
    scene_index: int
    start_time: float
    end_time: float
    start_frame: int
    end_frame: int
    keyframe_path: str | None = None


def detect_scenes(
    video_path: str,
    output_dir: str,
    threshold: float = 30.0,
) -> List[SceneSegment]:
    """PySceneDetect ContentDetector로 씬 분할 (오디오 완전 배제).

    Args:
        video_path: 원본 영상 경로
        output_dir: 처리 결과 디렉토리
        threshold: 씬 전환 감지 임계값 (기본 30.0)

    Returns:
        SceneSegment 목록
    """
    from scenedetect import SceneManager, open_video
    from scenedetect.detectors import ContentDetector

    # open_video: 오디오 스트림은 읽지 않음 (ContentDetector = 비디오 프레임만)
    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    scene_manager.detect_scenes(video)

    raw_scenes = scene_manager.get_scene_list()
    if not raw_scenes:
        log.warning("scene_detect.no_scenes", video=video_path)
        duration = video.duration.get_seconds()
        raw_scenes = [(video.base_timecode, video.base_timecode + duration)]

    segments: List[SceneSegment] = []
    scenes_dir = Path(output_dir) / "scenes"

    for idx, (start_tc, end_tc) in enumerate(raw_scenes):
        scene_dir = scenes_dir / str(idx)
        scene_dir.mkdir(parents=True, exist_ok=True)

        keyframe_path = _extract_scene_keyframe(video_path, start_tc.get_seconds(), scene_dir)

        seg = SceneSegment(
            scene_index=idx,
            start_time=start_tc.get_seconds(),
            end_time=end_tc.get_seconds(),
            start_frame=start_tc.get_frames(),
            end_frame=end_tc.get_frames(),
            keyframe_path=str(keyframe_path) if keyframe_path else None,
        )
        segments.append(seg)

    meta_path = Path(output_dir) / "scenes_meta.json"
    with open(meta_path, "w", encoding="utf-8") as fp:
        json.dump([asdict(s) for s in segments], fp, ensure_ascii=False, indent=2)

    log.info("scene_detect.done", num_scenes=len(segments), meta=str(meta_path))
    return segments


def _extract_scene_keyframe(video_path: str, start_sec: float, scene_dir: Path) -> Path | None:
    """씬 시작 시점의 대표 키프레임을 PNG로 추출 (ffmpeg)."""
    import ffmpeg

    keyframe_path = scene_dir / "keyframe.png"
    try:
        (
            ffmpeg.input(video_path, ss=start_sec)
            .output(str(keyframe_path), vframes=1)
            .overwrite_output()
            .run(quiet=True)
        )
        return keyframe_path
    except Exception as exc:
        log.warning("keyframe.extract_failed", start_sec=start_sec, error=str(exc))
        return None
