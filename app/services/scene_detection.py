#!/usr/bin/env python
# -*- coding: UTF-8 -*-

'''
@Project: NarratoAI
@File   : scene_detection
@Author : PS AI Recap
@Date   : 2026/09/19
'''

"""
Scene Detection Service — uses PySceneDetect to find scene boundaries.

Provides:
  - detect_scenes()       : raw scene boundary detection
  - get_highlight_scenes(): filter/score scenes by mode + duration

Used by generate_video.py when antivirus auto_sync or ai_auto_cut is enabled.
"""

import os
import math
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

try:
    from scenedetect import detect, ContentDetector, AdaptiveDetector, ThresholdDetector
    from scenedetect.scene_manager import SceneManager
    _SCENEDETECT_AVAILABLE = True
except Exception as _e:
    _SCENEDETECT_AVAILABLE = False
    logger.warning(f"PySceneDetect not available: {_e}")


def is_available() -> bool:
    """Return True if PySceneDetect is installed and importable."""
    return _SCENEDETECT_AVAILABLE


def detect_scenes(
    video_path: str,
    threshold: float = 27.0,
    min_scene_len: float = 0.5,
    detector_type: str = "content",
) -> List[Tuple[float, float]]:
    """Detect scene boundaries in a video.

    Args:
        video_path: path to the input video
        threshold: detection sensitivity (lower = more sensitive)
        min_scene_len: minimum scene length in seconds
        detector_type: "content" | "adaptive" | "threshold"

    Returns:
        List of (start_sec, end_sec) tuples.
    """
    if not _SCENEDETECT_AVAILABLE:
        logger.warning("Scene detection skipped — PySceneDetect not installed.")
        return []

    if not video_path or not os.path.exists(video_path):
        logger.warning(f"Scene detection skipped — file not found: {video_path}")
        return []

    try:
        if detector_type == "adaptive":
            detector = AdaptiveDetector(min_scene_len=min_scene_len)
        elif detector_type == "threshold":
            detector = ThresholdDetector()
        else:
            detector = ContentDetector(
                threshold=threshold,
                min_scene_len=max(1, int(round(min_scene_len * 30))),
            )

        scene_list = detect(video_path, detector, show_progress=False)

        results: List[Tuple[float, float]] = []
        for start_tc, end_tc in scene_list:
            start_sec = start_tc.get_seconds()
            end_sec = end_tc.get_seconds()
            if end_sec > start_sec:
                results.append((round(start_sec, 3), round(end_sec, 3)))

        logger.info(f"Scene Detection: {len(results)} scenes found in {os.path.basename(video_path)}")
        return results

    except Exception as e:
        logger.error(f"Scene detection failed: {e}")
        return []


def _score_scene(
    start: float,
    end: float,
    mode: str,
    video_duration: float,
) -> float:
    """Compute a highlight score for a scene.

    Higher score = better highlight candidate.
    """
    dur = max(0.001, end - start)
    score = 0.0

    if mode == "Auto Highlight":
        # Balance: prefer 3-12s scenes, bonus for mid-video
        if 2.0 <= dur <= 15.0:
            score += 5.0
        mid = (start + end) / 2.0
        if 0.15 * video_duration <= mid <= 0.85 * video_duration:
            score += 3.0
        score += min(dur / 5.0, 2.0)

    elif mode == "Action Scenes":
        # Prefer shorter, punchier clips
        if 1.0 <= dur <= 6.0:
            score += 6.0
        elif dur <= 10.0:
            score += 3.0

    elif mode == "Emotional Scenes":
        # Prefer longer, contemplative clips
        if 5.0 <= dur <= 20.0:
            score += 6.0
        elif dur >= 3.0:
            score += 3.0
        mid = (start + end) / 2.0
        if 0.25 * video_duration <= mid <= 0.75 * video_duration:
            score += 2.0

    elif mode == "Dialogue Scenes":
        # Prefer medium scenes with stable pacing
        if 3.0 <= dur <= 12.0:
            score += 5.0

    else:  # "All Scenes"
        score += 1.0

    return score


def get_highlight_scenes(
    video_path: str,
    mode: str = "Auto Highlight",
    sensitivity: int = 5,
    min_duration: float = 3.0,
    max_duration: float = 15.0,
    max_highlights: int = 5,
) -> List[Dict[str, Any]]:
    """Detect and return top-N highlight scenes.

    Args:
        video_path: input video path
        mode: one of "Auto Highlight", "Action Scenes", "Emotional Scenes",
              "Dialogue Scenes", "All Scenes"
        sensitivity: 1-10 (higher = more scenes detected)
        min_duration: minimum clip length in seconds
        max_duration: maximum clip length in seconds
        max_highlights: max number of highlights to return

    Returns:
        List of dicts: {start, end, duration, score}
    """
    # Map sensitivity 1-10 → content threshold (higher sensitivity = lower threshold)
    sensitivity = max(1, min(10, int(sensitivity or 5)))
    threshold = 40.0 - (sensitivity - 1) * 3.5
    threshold = max(10.0, min(40.0, threshold))

    # Get raw scenes
    raw_scenes = detect_scenes(video_path, threshold=threshold)

    # Fallback: if no scenes found, treat whole video as one scene
    if not raw_scenes:
        try:
            from app.services.generate_video import _probe_video
            meta = _probe_video(video_path)
            total = float(meta["duration"])
            raw_scenes = [(0.0, total)]
            logger.info("Scene Detection: no boundaries found, using whole video as one scene.")
        except Exception as e:
            logger.warning(f"Scene Detection fallback failed: {e}")
            return []

    # Estimate total duration
    try:
        from app.services.generate_video import _probe_video
        meta = _probe_video(video_path)
        video_duration = float(meta["duration"])
    except Exception:
        video_duration = raw_scenes[-1][1] if raw_scenes else 1.0

    min_duration = max(0.5, float(min_duration or 3.0))
    max_duration = max(min_duration, float(max_duration or 15.0))

    # Filter by duration
    candidates = []
    for start, end in raw_scenes:
        dur = end - start
        if dur < min_duration:
            continue
        if dur > max_duration:
            # Split long scene into max_duration chunks
            num_chunks = int(math.ceil(dur / max_duration))
            chunk_len = dur / num_chunks
            for i in range(num_chunks):
                cs = start + i * chunk_len
                ce = min(end, cs + chunk_len)
                if ce - cs >= min_duration:
                    candidates.append((cs, ce))
        else:
            candidates.append((start, end))

    # Score and sort
    scored = []
    for start, end in candidates:
        s = _score_scene(start, end, mode, video_duration)
        scored.append({
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(end - start, 3),
            "score": round(s, 3),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[: max(1, int(max_highlights or 5))]
    top.sort(key=lambda x: x["start"])

    logger.info(
        f"Scene Detection: {len(raw_scenes)} raw → {len(candidates)} filtered → "
        f"{len(top)} highlights (mode={mode}, sens={sensitivity})"
    )
    return top


def save_scenes_to_json(
    scenes: List[Dict[str, Any]],
    output_path: str,
) -> bool:
    """Save detected scenes to a JSON file."""
    try:
        import json
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(scenes, f, ensure_ascii=False, indent=2)
        logger.info(f"Scene Detection: saved {len(scenes)} scenes to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save scenes JSON: {e}")
        return False


def load_scenes_from_json(input_path: str) -> List[Dict[str, Any]]:
    """Load detected scenes from a JSON file."""
    try:
        import json
        if not os.path.exists(input_path):
            return []
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f) or []
    except Exception as e:
        logger.warning(f"Failed to load scenes JSON: {e}")
        return []