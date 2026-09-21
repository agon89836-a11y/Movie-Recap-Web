#!/usr/bin/env python
# -*- coding: UTF-8 -*-

'''
@Project: NarratoAI
@File   : voice_clone
@Author : PS AI Recap
@Date   : 2026/09/19
'''

"""
Voice Clone Service — unified interface for local voice-clone engines.

Supported engines (must be installed/running separately):
  - IndexTTS-1.5 (Windows local)
  - IndexTTS-1.5 (macOS MLX)
  - IndexTTS-2 (MLX)
  - OmniVoice (Multilingual)
  - VoxCPM-0.5B
  - VoxCPM-2B

Each engine is expected to expose an HTTP endpoint at the URL configured in
config.toml. This service probes the endpoint and sends TTS requests.

If no engine is available, is_available() returns False and the UI/backend
gracefully falls back to standard TTS (Edge-TTS / MMS-TTS).
"""

import os
import json
from typing import Optional, Dict, Any, Tuple
from loguru import logger

try:
    import requests
    _REQUESTS_AVAILABLE = True
except Exception:
    _REQUESTS_AVAILABLE = False


# ============================================================================
# ENGINE REGISTRY
# ============================================================================
# Each entry: engine_id → { name, config_section, api_key, default_url, health_path }
ENGINE_REGISTRY = {
    "indextts": {
        "name": "IndexTTS-1.5 (Windows Local)",
        "config_section": "indextts",
        "default_url": "http://127.0.0.1:8081",
        "tts_path": "/tts",
    },
    "indextts_macos": {
        "name": "IndexTTS-1.5 (macOS MLX)",
        "config_section": "indextts_macos",
        "default_url": "http://127.0.0.1:7866",
        "tts_path": "",
    },
    "indextts2": {
        "name": "IndexTTS-2 (MLX)",
        "config_section": "indextts2",
        "default_url": "http://127.0.0.1:7860",
        "tts_path": "",
    },
    "omnivoice": {
        "name": "OmniVoice (Multilingual)",
        "config_section": "omnivoice",
        "default_url": "http://127.0.0.1:7866",
        "tts_path": "/tts",
    },
    "voxcpm_05b": {
        "name": "VoxCPM-0.5B",
        "config_section": "voxcpm_05b",
        "default_url": "http://127.0.0.1:7864",
        "tts_path": "",
    },
    "voxcpm_2b": {
        "name": "VoxCPM-2B",
        "config_section": "voxcpm_2b",
        "default_url": "http://127.0.0.1:7863",
        "tts_path": "",
    },
}


def _get_config():
    """Lazy-import app config to avoid circular imports."""
    try:
        from app.config import config
        return config
    except Exception:
        return None


def _get_engine_config(engine_id: str) -> Dict[str, Any]:
    """Return config for a given engine (api_url, reference_audio, etc.)."""
    cfg = _get_config()
    if not cfg:
        return {}

    info = ENGINE_REGISTRY.get(engine_id)
    if not info:
        return {}

    section = info["config_section"]
    try:
        section_data = getattr(cfg, section, None)
        if section_data is None:
            # Fallback: try dict-style access
            section_data = cfg.app.get(section, {}) if hasattr(cfg, "app") else {}
        if isinstance(section_data, dict):
            return section_data
    except Exception as e:
        logger.debug(f"Voice Clone: failed to read config section '{section}': {e}")
    return {}


def _build_engine_url(engine_id: str) -> str:
    """Return full base URL for the engine's TTS endpoint."""
    info = ENGINE_REGISTRY.get(engine_id, {})
    default_url = info.get("default_url", "")
    tts_path = info.get("tts_path", "")

    engine_cfg = _get_engine_config(engine_id)
    api_url = engine_cfg.get("api_url", "") or default_url

    if tts_path and not api_url.rstrip("/").endswith(tts_path):
        api_url = api_url.rstrip("/") + tts_path

    return api_url


def _probe_engine(engine_id: str, timeout: float = 1.5) -> bool:
    """Check whether the engine's HTTP endpoint responds."""
    if not _REQUESTS_AVAILABLE:
        return False

    info = ENGINE_REGISTRY.get(engine_id, {})
    if not info:
        return False

    engine_cfg = _get_engine_config(engine_id)
    base_url = engine_cfg.get("api_url", "") or info.get("default_url", "")
    if not base_url:
        return False

    # Probe base URL (strip path for health check)
    base = base_url.split("?")[0].rstrip("/")
    # Try the base URL first, then root
    probe_urls = [base]
    try:
        from urllib.parse import urlparse
        parsed = urlparse(base)
        root = f"{parsed.scheme}://{parsed.netloc}"
        if root != base:
            probe_urls.append(root)
    except Exception:
        pass

    for url in probe_urls:
        try:
            resp = requests.get(url, timeout=timeout)
            # Any HTTP response means service is up (even 404)
            if resp.status_code < 500:
                return True
        except Exception:
            continue

    return False


def list_available_engines() -> list:
    """Return list of engine IDs whose HTTP endpoint is reachable."""
    available = []
    for engine_id in ENGINE_REGISTRY.keys():
        if _probe_engine(engine_id):
            available.append(engine_id)
    return available


def is_available(engine_id: Optional[str] = None) -> bool:
    """Return True if the specified engine (or any engine) is reachable."""
    if not _REQUESTS_AVAILABLE:
        return False

    if engine_id:
        return _probe_engine(engine_id)

    return bool(list_available_engines())


def _resolve_reference_audio(engine_id: str, ref_override: str = "") -> str:
    """Resolve the reference audio file path for an engine."""
    engine_cfg = _get_engine_config(engine_id)

    # Priority: explicit override → engine config → resource folder
    candidate = ref_override or engine_cfg.get("reference_audio", "")
    if candidate:
        if os.path.isabs(candidate) and os.path.exists(candidate):
            return candidate
        # Try resource folder
        try:
            from app.utils import utils
            ref_dir = utils.resource_dir("tts_reference_audio")
            full = os.path.join(ref_dir, candidate)
            if os.path.exists(full):
                return full
        except Exception:
            pass

    return ""


def synthesize(
    engine_id: str,
    text: str,
    reference_audio: str = "",
    output_path: str = "",
    **kwargs,
) -> Tuple[str, str]:
    """Run voice clone synthesis.

    Returns: (audio_path, error_message)
      - On success: (path_to_audio, "")
      - On failure: ("", reason)
    """
    if not _REQUESTS_AVAILABLE:
        return "", "requests library not available"

    if not text or not text.strip():
        return "", "empty text"

    info = ENGINE_REGISTRY.get(engine_id)
    if not info:
        return "", f"unknown engine: {engine_id}"

    if not _probe_engine(engine_id):
        return "", (
            f"{info['name']} is not running. "
            f"Please start the service first, then try again."
        )

    engine_cfg = _get_engine_config(engine_id)
    api_url = _build_engine_url(engine_id)
    if not api_url:
        return "", "engine URL not configured"

    ref_audio = _resolve_reference_audio(engine_id, ref_override=reference_audio)
    if not ref_audio:
        return "", "reference audio not found"

    if not output_path:
        try:
            from app.utils import utils
            import uuid
            temp_dir = utils.storage_dir("temp", create=True)
            output_path = os.path.join(temp_dir, f"voiceclone-{uuid.uuid4()}.wav")
        except Exception:
            return "", "cannot create output path"

    # --- Build request payload ---
    payload = {
        "text": text.strip(),
        "reference_audio": ref_audio,
        "ref_audio": ref_audio,
        "prompt_audio": ref_audio,
    }

    # Add engine-specific params from kwargs + config
    for key in (
        "speed", "temperature", "top_p", "top_k",
        "similarity", "expressiveness", "denoise",
        "emotion", "emo_alpha", "infer_mode", "do_sample",
        "num_beams", "repetition_penalty",
    ):
        if key in kwargs and kwargs[key] is not None:
            payload[key] = kwargs[key]
        elif key in engine_cfg:
            payload[key] = engine_cfg[key]

    # --- POST request ---
    try:
        resp = requests.post(api_url, json=payload, timeout=120)
    except Exception as e:
        return "", f"request failed: {e}"

    if resp.status_code != 200:
        return "", f"engine returned HTTP {resp.status_code}: {resp.text[:200]}"

    # --- Save response (expect audio bytes) ---
    try:
        content_type = resp.headers.get("Content-Type", "")
        if "audio" in content_type or "octet-stream" in content_type:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            logger.success(f"Voice Clone: saved → {output_path} ({info['name']})")
            return output_path, ""

        # Some engines return JSON with a file path or base64
        try:
            data = resp.json()
            for key in ("audio_path", "output_path", "path", "file"):
                if key in data and data[key] and os.path.exists(data[key]):
                    logger.success(f"Voice Clone: engine returned path → {data[key]}")
                    return data[key], ""
        except Exception:
            pass

        return "", f"unexpected response format: {content_type}"

    except Exception as e:
        return "", f"failed to save audio: {e}"


def get_engine_display_name(engine_id: str) -> str:
    """Human-readable name for an engine."""
    return ENGINE_REGISTRY.get(engine_id, {}).get("name", engine_id)


def get_install_hint(engine_id: str) -> str:
    """Return a short install hint for the engine."""
    hints = {
        "indextts": "https://github.com/index-tts/index-tts (Windows local)",
        "indextts_macos": "https://github.com/index-tts/index-tts (macOS MLX)",
        "indextts2": "https://github.com/index-tts/index-tts (IndexTTS-2)",
        "omnivoice": "https://github.com/OmniVoice/OmniVoice",
        "voxcpm_05b": "https://github.com/OpenBMB/VoxCPM",
        "voxcpm_2b": "https://github.com/OpenBMB/VoxCPM",
    }
    return hints.get(engine_id, "")