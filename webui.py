import streamlit as st
import os
import sys
import time
from html import escape
from loguru import logger
from app.config import config
from webui.components import (
    basic_settings,
    video_settings,
    audio_settings,
    subtitle_settings,
    script_settings,
    system_settings,
    antivirus_settings,
    advanced_features,
    auth_panel,
    coin_panel,
    payment_panel,
)
from app.utils import utils
from app.utils import ffmpeg_utils
from app.models import const
from app.models.schema import VideoClipParams, VideoAspect

st.set_page_config(
    page_title="PS AI Recap",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'About': "PS AI Recap — Movie Recap Studio",
    },
)

hide_streamlit_style = """
<style>#root > div:nth-child(1) > div > div > div > div > section > div {padding-top: 2rem; padding-bottom: 10px; padding-left: 20px; padding-right: 20px;}</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

def init_log():
    """Initialize logging configuration."""
    from loguru import logger
    logger.remove()
    _lvl = "INFO"

    def format_record(record):
        file_path = record["file"].path
        relative_path = os.path.relpath(file_path, config.root_dir)
        record["file"].path = f"./{relative_path}"
        record['message'] = record['message'].replace(config.root_dir, ".")

        _format = '<green>{time:%Y-%m-%d %H:%M:%S}</> | ' + \
                  '<level>{level}</>' + \
                  '"{file.path}:{line}":<blue> {function}</>' + \
                  '- <level>{message}</>' + "\n"
        return _format

    def log_filter(record):
        ignore_patterns = [
            "Examining the path of torch.classes raised",
            "torch.cuda.is_available()",
            "CUDA initialization"
        ]
        return not any(pattern in record["message"] for pattern in ignore_patterns)

    logger.add(
        sys.stdout,
        level=_lvl,
        format=format_record,
        colorize=True,
        filter=log_filter
    )

def init_global_state():
    """Initialize global state."""
    if 'video_clip_json' not in st.session_state:
        st.session_state['video_clip_json'] = []
    if 'video_plot' not in st.session_state:
        st.session_state['video_plot'] = ''
    if 'ui_language' not in st.session_state:
        st.session_state['ui_language'] = config.ui.get("language", utils.get_system_locale())

def tr(key):
    """Translation function."""
    i18n_dir = os.path.join(os.path.dirname(__file__), "webui", "i18n")
    locales = utils.load_locales(i18n_dir)
    loc = locales.get(st.session_state['ui_language'], {})
    return loc.get("Translation", {}).get(key, key)

VIDEO_GENERATION_STEP_LABELS = [
    "Loading script",
    "Generating TTS voice",
    "Cutting video by script",
    "Merging voice and subtitle",
    "Merging video clips",
    "Synthesizing final video",
]

def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def _format_optional_percent(value):
    try:
        percent = max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return None
    if percent.is_integer():
        return str(int(percent))
    return f"{percent:.1f}"

def _render_generation_status(task: dict | None) -> str:
    task = task or {}
    state = task.get("state")
    current_step = _safe_int(task.get("step_current"), 0)
    step_total = _safe_int(task.get("step_total"), len(VIDEO_GENERATION_STEP_LABELS))
    message = str(task.get("message") or "")
    ffmpeg_percent = _format_optional_percent(task.get("ffmpeg_progress"))

    if current_step <= 0:
        return f"<div style='font-weight:650;color:#e2e8f0;'>{escape(message or 'Generating video, please wait...')}</div>"

    lines = []
    for index, default_label in enumerate(VIDEO_GENERATION_STEP_LABELS, start=1):
        is_current = index == current_step
        is_complete = state == const.TASK_STATE_COMPLETE
        is_done = is_complete or index < current_step
        label = message if is_current and message else default_label

        suffix = f"{index}/{step_total}"
        if (
            is_current
            and index == step_total
            and ffmpeg_percent is not None
            and not is_complete
        ):
            suffix = f"{suffix} | ffmpeg {ffmpeg_percent}%"

        color = "#e2e8f0" if is_current else "#8b9099" if is_done else "#5a6072"
        weight = "650" if is_current else "500"
        lines.append(
            "<div style='"
            "font-size:1.02rem;"
            "line-height:1.85;"
            "margin:0.28rem 0;"
            f"color:{color};"
            f"font-weight:{weight};"
            "'>"
            f"{escape(label)} <span style='white-space:nowrap;'>({escape(suffix)})</span>"
            "</div>"
        )

    return "".join(lines)

def _estimate_video_minutes() -> float:
    """Video file ကနေ အရှည် (မိနစ်) ခန့်မှန်း — 3 Methods + Debug Log"""
    video_path = st.session_state.get("video_origin_path", "")
    logger.info(f"[COIN-DEBUG] video_origin_path: '{video_path}'")

    if not video_path:
        logger.warning("[COIN-DEBUG] video_origin_path EMPTY — default 5 min")
        return 5.0

    if not os.path.exists(video_path):
        logger.warning(f"[COIN-DEBUG] File not found: {video_path}")
        return 5.0

    file_size = os.path.getsize(video_path)
    logger.info(f"[COIN-DEBUG] File exists — size: {file_size} bytes")

    # --- Method 1: _probe_video ---
    try:
        from app.services.generate_video import _probe_video
        meta = _probe_video(video_path)
        logger.info(f"[COIN-DEBUG] _probe_video meta: {meta}")
        duration = float(meta.get("duration", 0))
        if duration > 0:
            minutes = max(0.5, duration / 60.0)
            logger.info(f"[COIN-DEBUG] Method 1 OK — {duration:.1f}s = {minutes:.2f} min")
            return minutes
    except Exception as e:
        logger.warning(f"[COIN-DEBUG] Method 1 failed: {e}")

    # --- Method 2: ffprobe ---
    try:
        import subprocess
        import json as _json
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json", video_path,
        ]
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=15, check=False,
        )
        if result.returncode == 0:
            data = _json.loads(result.stdout.decode("utf-8", errors="ignore"))
            duration = float(data.get("format", {}).get("duration", 0))
            if duration > 0:
                minutes = max(0.5, duration / 60.0)
                logger.info(f"[COIN-DEBUG] Method 2 OK — {duration:.1f}s = {minutes:.2f} min")
                return minutes
    except Exception as e:
        logger.warning(f"[COIN-DEBUG] Method 2 failed: {e}")

    # --- Method 3: ffmpeg-python ---
    try:
        import ffmpeg
        probe = ffmpeg.probe(video_path)
        duration = float(probe.get("format", {}).get("duration", 0))
        if duration > 0:
            minutes = max(0.5, duration / 60.0)
            logger.info(f"[COIN-DEBUG] Method 3 OK — {duration:.1f}s = {minutes:.2f} min")
            return minutes
    except Exception as e:
        logger.warning(f"[COIN-DEBUG] Method 3 failed: {e}")

    logger.warning("[COIN-DEBUG] ALL METHODS FAILED — default 5 min")
    return 5.0


def _check_and_deduct_coins() -> bool:
    """Video မထုတ်ခင် Coin စစ်ပြီး ဖြတ် — Antivirus Mode ဖြစ်လည်း အလုပ်လုပ်"""
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("⚠️ Login မဝင်ရသေး")
        return False

    # --- Estimated minutes ---
    minutes = _estimate_video_minutes()
    logger.info(f"[COIN] Estimated video duration: {minutes:.2f} min")

    # --- Antivirus Mode check (log only) ---
    av_mode = bool(st.session_state.get("antivirus_auto_mode_widget", False))
    logger.info(f"[COIN] Antivirus Auto Mode: {av_mode}")

    # --- Cost calc ---
    cost_data = coin_panel.calculate_video_cost(minutes)
    total_cost = cost_data["total"]
    logger.info(f"[COIN] Cost breakdown: {cost_data}")

    # --- Balance check ---
    balance = coin_panel.cs.get_coin_balance(user_id)
    logger.info(f"[COIN] Balance: {balance} · Cost: {total_cost}")

    if balance < total_cost:
        st.error(
            f"❌ Coin မလုံလောက် — "
            f"လိုတာ **{total_cost}** Coin · "
            f"ရှိတာ **{balance}** Coin"
        )
        return False

    # --- Deduct ---
    result = coin_panel.check_and_deduct_for_video(minutes)

    if not result["success"]:
        st.error(f"❌ {result['error']}")
        logger.error(f"[COIN] Deduct failed: {result['error']}")
        return False

    new_balance = coin_panel.cs.get_coin_balance(user_id)
    st.session_state["coin_balance"] = new_balance

    st.success(
        f"💰 **{result['cost']} Coin** ဖြတ်ပြီးပါပြီ — "
        f"ကျန် **{new_balance} Coin** · Video ထုတ်နေတယ်..."
    )
    logger.info(
        f"[COIN] Deducted {result['cost']} from user {user_id} "
        f"({minutes:.1f} min). New balance: {new_balance}"
    )
    return True


def render_generate_button():
    """Render generate button and processing logic."""
    # ========================================================================
    # 💰 COST PREVIEW — Generate မနှိပ်ခင်
    # ========================================================================
    _minutes = _estimate_video_minutes()
    _enough_coins = coin_panel.render_generate_cost_preview(_minutes)

    if st.button(
        tr("Generate Video"),
        use_container_width=True,
        type="primary",
        disabled=not _enough_coins,
    ):
        from app.services import task as tm
        from app.services import state as sm
        from app.models import const
        import threading
        import time
        import uuid

        config.save_config()

        if not st.session_state.get('video_clip_json_path'):
            st.error(tr("Script file cannot be empty"))
            return
        if not st.session_state.get('video_origin_path'):
            st.error(tr("Video file cannot be empty"))
            return

        # ====================================================================
        # 💰 COIN CHECK & DEDUCT
        # ====================================================================
        if not _check_and_deduct_coins():
            return

        script_params = script_settings.get_script_params()
        video_params = video_settings.get_video_params()
        audio_params = audio_settings.get_audio_params()
        subtitle_params = subtitle_settings.get_subtitle_params()
        advanced_params = advanced_features.get_advanced_params()
        antivirus_params = antivirus_settings.get_antivirus_params()

        all_params = {
            **script_params,
            **video_params,
            **audio_params,
            **subtitle_params,
            "advanced_params": advanced_params,
            "antivirus_params": antivirus_params,
        }

        params = VideoClipParams(**all_params)

        task_id = str(uuid.uuid4())

        @st.dialog(tr("Generating Video"), width="large")
        def generate_video_dialog():
            st.markdown(
                """
                <style>
                    div[data-testid="stDialog"] div[data-testid="stStatusWidget"] {
                        margin-top: 0.25rem;
                    }
                    div[data-testid="stDialog"] div[data-testid="stProgress"] {
                        margin-bottom: 0.75rem;
                    }
                    div[data-testid="stDialog"] video {
                        max-height: 62vh;
                        object-fit: contain;
                        background: #000;
                    }
                </style>
                """,
                unsafe_allow_html=True,
            )

            progress_bar = st.progress(0)
            status_panel = st.status(tr("Generating Video"), expanded=True)
            with status_panel:
                status_placeholder = st.empty()
                status_placeholder.markdown(
                    _render_generation_status(None),
                    unsafe_allow_html=True,
                )

            def run_task():
                try:
                    tm.start_subclip_unified(
                        task_id=task_id,
                        params=params
                    )
                except Exception as e:
                    logger.error(f"Task failed: {e}")
                    current_task = sm.state.get_task(task_id) or {}
                    sm.state.update_task(
                        task_id,
                        state=const.TASK_STATE_FAILED,
                        progress=current_task.get("progress", 0),
                        message=str(e),
                    )

            thread = threading.Thread(target=run_task)
            thread.start()

            last_status_key = None

            while True:
                task = sm.state.get_task(task_id)
                if task:
                    progress = task.get("progress", 0)
                    state = task.get("state")

                    try:
                        progress = int(progress)
                    except (TypeError, ValueError):
                        progress = 0
                    progress = max(0, min(progress, 100))

                    progress_bar.progress(progress / 100)
                    current_message = task.get("message") or f"Processing... {progress}%"
                    status_key = (
                        state,
                        progress,
                        current_message,
                        task.get("step_current"),
                        task.get("step_total"),
                        task.get("ffmpeg_progress"),
                    )
                    if status_key != last_status_key:
                        status_placeholder.markdown(
                            _render_generation_status(task),
                            unsafe_allow_html=True,
                        )
                        last_status_key = status_key

                    if state == const.TASK_STATE_COMPLETE:
                        status_panel.update(
                            label=tr("Video Generation Completed"),
                            state="complete",
                            expanded=False,
                        )
                        progress_bar.progress(1.0)

                        video_files = task.get("videos", [])
                        try:
                            if video_files:
                                aspect = getattr(params, "video_aspect", "")
                                aspect = getattr(aspect, "value", aspect)
                                preview_width = 320 if aspect in {
                                    VideoAspect.portrait.value,
                                    VideoAspect.portrait_2.value,
                                } else 600
                                for url in video_files:
                                    _, preview_col, _ = st.columns([1, 2, 1])
                                    with preview_col:
                                        st.video(url, width=preview_width)
                        except Exception as e:
                            logger.error(f"Failed to play video: {e}")

                        st.success(tr("Video Generation Completed"))
                        break

                    if state == const.TASK_STATE_FAILED:
                        status_panel.update(
                            label=f"{tr('Task failed')}: {task.get('message', 'Unknown error')}",
                            state="error",
                            expanded=True,
                        )
                        st.error(f"{tr('Task failed')}: {task.get('message', 'Unknown error')}")
                        break

                time.sleep(0.5)

        generate_video_dialog()

def get_voice_name_for_tts_engine(tts_engine: str) -> str:
    """Get selected voice name for a given TTS engine."""
    if tts_engine == 'edge_tts':
        return config.ui.get('edge_voice_name', 'zh-CN-XiaoxiaoNeural-Female')
    if tts_engine == 'azure_speech':
        return config.ui.get('azure_voice_name', 'zh-CN-XiaoxiaoMultilingualNeural')
    if tts_engine == 'tencent_tts':
        return f"tencent:{config.ui.get('tencent_voice_type', '101001')}"
    if tts_engine == 'qwen3_tts':
        return f"qwen3:{config.ui.get('qwen_voice_type', 'Cherry')}"
    if tts_engine == config.INDEXTTS2_ENGINE:
        reference_audio = config.indextts2.get('reference_audio', '')
        if reference_audio:
            return f"{config.INDEXTTS2_VOICE_PREFIX}{reference_audio}"
        return config.ui.get('voice_name', '')
    if config.normalize_tts_engine_name(tts_engine) == config.INDEXTTS_ENGINE:
        reference_audio = config.indextts.get('reference_audio', '')
        if reference_audio:
            return f"{config.INDEXTTS_VOICE_PREFIX}{reference_audio}"
        return config.ui.get('voice_name', '')
    if tts_engine == config.OMNIVOICE_ENGINE:
        mode = config.omnivoice.get('mode', 'auto')
        reference_audio = config.omnivoice.get('reference_audio', '')
        if mode == 'voice_clone' and reference_audio:
            return f"{config.OMNIVOICE_VOICE_PREFIX}{reference_audio}"
        return f"{config.OMNIVOICE_VOICE_PREFIX}{mode}"
    if tts_engine == 'doubaotts':
        return config.ui.get('doubaotts_voice_type', 'BV700_streaming')
    if tts_engine == 'soulvoice':
        voice_uri = config.soulvoice.get('voice_uri', '')
        if voice_uri and not voice_uri.startswith(('soulvoice:', 'speech:')):
            return f"soulvoice:{voice_uri}"
        return voice_uri
    return config.ui.get('voice_name', config.ui.get('edge_voice_name', 'zh-CN-XiaoxiaoNeural-Female'))

def get_jianying_export_params(draft_name=None) -> VideoClipParams:
    """Get parameters for exporting to Jianying draft."""
    tts_engine = st.session_state.get('tts_engine', config.ui.get('tts_engine', 'edge_tts'))
    voice_name = get_voice_name_for_tts_engine(tts_engine)
    voice_rate = st.session_state.get('voice_rate', 1.0)
    voice_pitch = st.session_state.get('voice_pitch', 1.0)
    subtitle_paths = st.session_state.get('subtitle_paths', [])
    if isinstance(subtitle_paths, str):
        subtitle_paths = [subtitle_paths]
    subtitle_paths = [
        path for path in subtitle_paths
        if isinstance(path, str) and path.strip()
    ]
    if not subtitle_paths and st.session_state.get('subtitle_path'):
        subtitle_paths = [st.session_state.get('subtitle_path')]

    advanced_params = advanced_features.get_advanced_params()
    antivirus_params = antivirus_settings.get_antivirus_params()

    return VideoClipParams(
        video_clip_json_path=st.session_state['video_clip_json_path'],
        video_origin_path=st.session_state['video_origin_path'],
        video_origin_paths=st.session_state.get('video_origin_paths', []),
        original_subtitle_path=subtitle_paths[0] if subtitle_paths else "",
        original_subtitle_paths=subtitle_paths,
        tts_engine=tts_engine,
        voice_name=voice_name,
        voice_rate=voice_rate,
        voice_pitch=voice_pitch,
        n_threads=config.app.get('n_threads', 4),
        video_aspect=VideoAspect.landscape,
        subtitle_enabled=st.session_state.get('subtitle_enabled', False),
        font_name=st.session_state.get('font_name', 'SourceHanSansCN-Regular.otf'),
        font_size=st.session_state.get('font_size', 24),
        text_fore_color=st.session_state.get('text_fore_color', '#FFFFFF'),
        subtitle_position=st.session_state.get('subtitle_position', 'bottom'),
        custom_position=st.session_state.get('custom_position', 70.0),
        tts_volume=st.session_state.get('tts_volume', 1.0),
        original_volume=st.session_state.get('original_volume', 0.7),
        bgm_volume=st.session_state.get('bgm_volume', 0.3),
        advanced_params=advanced_params,
        antivirus_params=antivirus_params,
        draft_name=(
            draft_name
            if draft_name is not None
            else st.session_state.get('draft_name_input', f"NarratoAI_{int(time.time())}")
        )
    )

def _render_jianying_export_status():
    """Render Jianying export result status."""
    result = st.session_state.get('jianying_export_result')
    error = st.session_state.get('jianying_export_error')

    if result:
        st.success(tr("Jianying draft exported successfully").format(name=result['draft_name']))
        st.info(tr("Draft saved to").format(path=result['draft_path']))
    elif error:
        st.error(f"{tr('Failed to export Jianying draft')}: {error}")

def _render_jianying_export_dialog():
    """Use dialog to confirm Jianying draft name."""
    import uuid
    from loguru import logger

    @st.dialog(tr("Export to Jianying Draft"), width="small")
    def jianying_export_dialog():
        jianying_draft_path = config.ui.get("jianying_draft_path", "")
        dialog_title = escape(tr("Jianying export dialog title"))
        dialog_description = escape(tr("Jianying export dialog description"))
        destination_label = escape(tr("Jianying export destination"))
        destination_path = escape(jianying_draft_path or "-")

        st.markdown(
            f"""
            <style>
                .jianying-export-panel {{
                    display: flex;
                    gap: 12px;
                    align-items: flex-start;
                    padding: 14px;
                    margin: 2px 0 18px;
                    border: 1px solid rgba(139, 92, 246, 0.3);
                    border-radius: 12px;
                    background: linear-gradient(135deg, rgba(139, 92, 246, 0.12), rgba(6, 182, 212, 0.06));
                }}
                .jianying-export-icon {{
                    width: 40px;
                    height: 40px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    flex: 0 0 auto;
                    border-radius: 10px;
                    color: #ffffff;
                    background: linear-gradient(135deg, #8b5cf6, #6366f1);
                    font-size: 22px;
                    line-height: 1;
                    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
                }}
                .jianying-export-title {{
                    color: #e2e8f0;
                    font-size: 17px;
                    font-weight: 700;
                    line-height: 1.35;
                    margin-bottom: 4px;
                }}
                .jianying-export-description {{
                    color: #94a3b8;
                    font-size: 13px;
                    line-height: 1.55;
                }}
                .jianying-export-path {{
                    padding: 10px 12px;
                    margin: 2px 0 16px;
                    border: 1px solid rgba(148, 163, 184, 0.15);
                    border-radius: 10px;
                    background: rgba(18, 22, 32, 0.6);
                    color: #cbd5e1;
                    font-size: 13px;
                    line-height: 1.45;
                    word-break: break-all;
                }}
                .jianying-export-path-label {{
                    display: block;
                    color: #64748b;
                    font-size: 12px;
                    margin-bottom: 4px;
                }}
            </style>
            <div class="jianying-export-panel">
                <div class="jianying-export-icon">📤</div>
                <div>
                    <div class="jianying-export-title">{dialog_title}</div>
                    <div class="jianying-export-description">{dialog_description}</div>
                </div>
            </div>
            <div class="jianying-export-path">
                <span class="jianying-export-path-label">{destination_label}</span>
                {destination_path}
            </div>
            """,
            unsafe_allow_html=True,
        )

        draft_name = st.text_input(
            tr("Jianying draft name"),
            key="draft_name_input",
            placeholder="NarratoAI_",
        )

        error = st.session_state.get('jianying_export_error')
        if error:
            st.error(f"{tr('Failed to export Jianying draft')}: {error}")

        cancel_col, confirm_col = st.columns(2)
        with cancel_col:
            if st.button(tr("Cancel"), key="cancel_export", use_container_width=True):
                st.session_state['jianying_export_error'] = None
                st.rerun()

        with confirm_col:
            if st.button(tr("Confirm Export"), key="confirm_export", type="primary", use_container_width=True):
                draft_name = (draft_name or "").strip()
                if not draft_name:
                    st.error(tr("Please enter draft name"))
                    return

                task_id = str(uuid.uuid4())
                st.session_state['task_id'] = task_id

                try:
                    params = get_jianying_export_params(draft_name)
                except Exception as e:
                    logger.error(f"Failed to build params: {e}")
                    st.session_state['jianying_export_error'] = f"{tr('Failed to build parameters')}: {e}"
                    st.error(st.session_state['jianying_export_error'])
                    return

                with st.spinner(tr("Exporting to Jianying draft...")):
                    try:
                        from app.services import jianying_task

                        result = jianying_task.start_export_jianying_draft(task_id, params)

                        logger.info(f"Successfully exported to Jianying draft: {result['draft_name']}")
                        logger.info(f"Draft saved to: {result['draft_path']}")

                        st.session_state['jianying_export_result'] = result
                        st.session_state['jianying_export_error'] = None
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Failed to export to Jianying draft: {e}")
                        import traceback
                        logger.error(f"Error details: {traceback.format_exc()}")
                        st.session_state['jianying_export_error'] = str(e)
                        st.session_state['jianying_export_result'] = None
                        st.error(f"{tr('Failed to export Jianying draft')}: {e}")

    jianying_export_dialog()

def render_export_jianying_button():
    """Render export to Jianying draft button and processing logic."""
    import os
    import time

    if 'jianying_export_result' not in st.session_state:
        st.session_state['jianying_export_result'] = None
    if 'jianying_export_error' not in st.session_state:
        st.session_state['jianying_export_error'] = None

    if st.button(tr("Export to Jianying Draft"), use_container_width=True, type="secondary"):
        config.save_config()

        if not st.session_state.get('video_clip_json_path'):
            st.error(tr("Script file cannot be empty"))
            return
        if not st.session_state.get('video_origin_path'):
            st.error(tr("Video file cannot be empty"))
            return

        jianying_draft_path = config.ui.get("jianying_draft_path", "")
        if not jianying_draft_path:
            st.error(tr("Please configure Jianying draft folder in basic settings"))
            return

        if not os.path.exists(jianying_draft_path):
            st.error(tr("Jianying draft folder does not exist").format(path=jianying_draft_path))
            return

        st.session_state['jianying_export_result'] = None
        st.session_state['jianying_export_error'] = None
        st.session_state['draft_name_input'] = f"NarratoAI_{int(time.time())}"
        _render_jianying_export_dialog()

    _render_jianying_export_status()

def _render_user_header():
    """Render user info header with subscription status"""
    user_code = st.session_state.get("user_code", "")
    user_email = st.session_state.get("user_email", "")
    user_id = st.session_state.get("user_id")

    coin_balance = 0
    is_monthly = False
    days_left = 0

    try:
        from app.services import coin_system as cs
        if user_id:
            coin_balance = cs.get_coin_balance(user_id)
            st.session_state["coin_balance"] = coin_balance

            sub = cs.get_subscription_status(user_id)
            is_monthly = sub.get("active", False)
            days_left = sub.get("days_left", 0)
            st.session_state["is_monthly_active"] = is_monthly
    except Exception:
        coin_balance = st.session_state.get("coin_balance", 0)
        is_monthly = st.session_state.get("is_monthly_active", False)

    # --- Subscription Badge ---
    if is_monthly:
        sub_badge = (
            f'<span style="display:inline-block;padding:3px 10px;'
            f'border-radius:999px;font-size:0.65rem;font-weight:800;'
            f'background:linear-gradient(135deg,#10b981,#06b6d4);color:#fff;'
            f'box-shadow:0 2px 8px rgba(16,185,129,0.4);">'
            f'🌟 MONTHLY · {days_left} ရက်</span>'
        )
    else:
        sub_badge = (
            '<span style="display:inline-block;padding:3px 10px;'
            'border-radius:999px;font-size:0.65rem;font-weight:800;'
            'background:rgba(148,163,184,0.15);color:#94a3b8;'
            'border:1px solid rgba(148,163,184,0.3);">'
            '🆓 FREE</span>'
        )

    info_col, coin_col, logout_col = st.columns([3, 1, 1])

    with info_col:
        st.markdown(
            f'<div style="font-size:0.85rem;color:#94a3b8;padding-top:4px;">'
            f'👤 <b style="color:#e2e8f0;">{user_code}</b> · '
            f'<span style="color:#64748b;">{user_email}</span> '
            f'{sub_badge}'
            f'</div>',
            unsafe_allow_html=True,
        )

    with coin_col:
        st.markdown(
            f'<div style="text-align:right;font-size:1.05rem;font-weight:800;'
            f'color:#c4b5fd;padding-top:4px;">💰 {coin_balance} Coin</div>',
            unsafe_allow_html=True,
        )

    with logout_col:
        if st.button("🚪 Logout", key="logout_btn", use_container_width=True):
            auth_panel.logout()
            st.rerun()

def main():
    """Main function."""
    init_log()
    init_global_state()

    # ========================================================================
    # 🔐 LOGIN GATE — Login မဝင်ရင် Auth Page ပဲ ပြ
    # ========================================================================
    if not auth_panel.require_login(tr):
        return

    if 'llm_providers_registered' not in st.session_state:
        try:
            from app.services.llm.providers import register_all_providers
            register_all_providers()
            st.session_state['llm_providers_registered'] = True
            logger.info("LLM providers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register LLM providers: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            st.error(tr("LLM initialization failed").format(error=str(e)))

    if 'hwaccel_logged' not in st.session_state:
        st.session_state['hwaccel_logged'] = False

    hwaccel_info = ffmpeg_utils.detect_hardware_acceleration()
    if not st.session_state['hwaccel_logged']:
        if hwaccel_info["available"]:
            logger.info(f"FFmpeg HW accel available | Type: {hwaccel_info['type']} | Encoder: {hwaccel_info['encoder']}")
        else:
            logger.warning(f"FFmpeg HW accel not available: {hwaccel_info['message']}")
        st.session_state['hwaccel_logged'] = True

    try:
        utils.init_resources()
    except Exception as e:
        logger.warning(f"Resource init warning: {e}")

    # ============================================================================
    # 🎨 PS AI RECAP — SNAPPY DESIGN SYSTEM v5.0
    # ============================================================================
    st.markdown(
        """
        <style>
            .stApp {
                background: #0a0d14 !important;
            }
            html, body, [class*="css"] {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter',
                             'Helvetica Neue', Arial, sans-serif !important;
                -webkit-font-smoothing: antialiased !important;
                -moz-osx-font-smoothing: grayscale !important;
            }
            .psai-header {
                display: flex;
                align-items: center;
                gap: 18px;
                padding: 8px 0 12px;
            }
            .psai-sticker {
                width: 68px;
                height: 68px;
                border-radius: 20px;
                background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 50%, #06b6d4 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 36px;
                position: relative;
                flex-shrink: 0;
                box-shadow:
                    0 10px 30px rgba(139, 92, 246, 0.35),
                    0 4px 12px rgba(0, 0, 0, 0.4),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2);
            }
            .psai-title-wrap {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            .psai-title {
                font-size: 2.2rem;
                font-weight: 900;
                letter-spacing: -0.5px;
                line-height: 1;
                background: linear-gradient(135deg, #ffffff 0%, #c4b5fd 50%, #8b5cf6 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .psai-subtitle {
                font-size: 0.72rem;
                font-weight: 600;
                letter-spacing: 3px;
                text-transform: uppercase;
                color: #64748b;
                padding-left: 3px;
            }
            .psai-badge {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                padding: 3px 10px;
                border-radius: 999px;
                font-size: 0.62rem;
                font-weight: 800;
                letter-spacing: 0.8px;
                background: linear-gradient(135deg, #f43f5e, #ec4899);
                color: #ffffff;
                vertical-align: middle;
                box-shadow:
                    0 2px 8px rgba(244, 63, 94, 0.4),
                    inset 0 1px 0 rgba(255, 255, 255, 0.3);
            }
            .step-header {
                font-size: 1.1rem;
                font-weight: 700;
                color: #e2e8f0;
                margin: 28px 0 14px;
                padding: 12px 18px;
                border-radius: 10px;
                position: relative;
                letter-spacing: 0.2px;
                background: linear-gradient(90deg,
                    rgba(139, 92, 246, 0.12) 0%,
                    rgba(6, 182, 212, 0.04) 50%,
                    transparent 100%);
                overflow: hidden;
            }
            .step-header::before {
                content: '';
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                width: 4px;
                background: linear-gradient(180deg, #8b5cf6, #06b6d4);
                border-radius: 0 4px 4px 0;
            }
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
                position: sticky;
                top: 3rem;
                align-self: flex-start;
                max-height: calc(100vh - 4rem);
                overflow-y: auto;
                padding-right: 8px;
            }
            div[data-testid="stCheckbox"] label[data-baseweb="checkbox"] > div:first-child {
                width: 50px !important;
                height: 28px !important;
                min-width: 50px !important;
                max-width: 50px !important;
                border-radius: 999px !important;
                background: #1e2436 !important;
                border: 1.5px solid rgba(148, 163, 184, 0.22) !important;
                position: relative !important;
                display: flex !important;
                align-items: center !important;
                padding: 2px !important;
                box-sizing: border-box !important;
                transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease !important;
                box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.5) !important;
                cursor: pointer !important;
            }
            div[data-testid="stCheckbox"] label[data-baseweb="checkbox"] > div:first-child > div {
                width: 20px !important;
                height: 20px !important;
                min-width: 20px !important;
                border-radius: 50% !important;
                background: #ffffff !important;
                box-shadow:
                    0 2px 6px rgba(0, 0, 0, 0.5),
                    0 1px 2px rgba(0, 0, 0, 0.35) !important;
                transition: transform 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important;
                transform: translateX(0) !important;
                color: transparent !important;
                font-size: 0 !important;
                position: relative !important;
                z-index: 2 !important;
            }
            div[data-testid="stCheckbox"] label[data-baseweb="checkbox"] > div:first-child > div svg,
            div[data-testid="stCheckbox"] label[data-baseweb="checkbox"] > div:first-child > div::before,
            div[data-testid="stCheckbox"] label[data-baseweb="checkbox"] > div:first-child > div::after {
                display: none !important;
            }
            div[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:has(input[aria-checked="true"]) > div:first-child,
            div[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:has(input:checked) > div:first-child {
                background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%) !important;
                border-color: rgba(167, 139, 250, 0.6) !important;
                box-shadow:
                    inset 0 2px 3px rgba(0, 0, 0, 0.12),
                    0 0 12px rgba(139, 92, 246, 0.5) !important;
            }
            div[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:has(input[aria-checked="true"]) > div:first-child > div,
            div[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:has(input:checked) > div:first-child > div {
                transform: translateX(22px) !important;
            }
            div[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:hover > div:first-child {
                border-color: rgba(139, 92, 246, 0.5) !important;
            }
            div[data-testid="stSlider"] [role="slider"] {
                background: #ffffff !important;
                border: 3px solid #8b5cf6 !important;
                box-shadow:
                    0 0 12px rgba(139, 92, 246, 0.6),
                    0 2px 6px rgba(0, 0, 0, 0.35) !important;
                width: 16px !important;
                height: 16px !important;
                transition: box-shadow 0.15s ease !important;
            }
            div[data-testid="stSlider"] [role="slider"]:hover {
                box-shadow:
                    0 0 18px rgba(139, 92, 246, 0.85),
                    0 3px 8px rgba(0, 0, 0, 0.4) !important;
            }
            div[data-testid="stButton"] > button[kind="primary"],
            div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
                background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
                border: none;
                color: #ffffff;
                font-weight: 700;
                font-size: 0.92rem;
                letter-spacing: 0.4px;
                border-radius: 12px;
                padding: 0.7rem 1.5rem;
                box-shadow:
                    0 4px 14px rgba(139, 92, 246, 0.4),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2);
                transition: background 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease !important;
            }
            div[data-testid="stButton"] > button[kind="primary"]:hover {
                transform: translateY(-1px);
                box-shadow:
                    0 6px 20px rgba(139, 92, 246, 0.55),
                    inset 0 1px 0 rgba(255, 255, 255, 0.25);
                background: linear-gradient(135deg, #a78bfa 0%, #818cf8 100%);
            }
            div[data-testid="stButton"] > button[kind="primary"]:active {
                transform: scale(0.98);
            }
            div[data-testid="stButton"] > button[kind="secondary"],
            div[data-testid="stButton"] > button[data-testid="baseButton-secondary"] {
                background: rgba(139, 92, 246, 0.06);
                border: 1px solid rgba(139, 92, 246, 0.3);
                color: #c4b5fd;
                font-weight: 600;
                border-radius: 12px;
                padding: 0.65rem 1.3rem;
                transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
            }
            div[data-testid="stButton"] > button[kind="secondary"]:hover {
                background: rgba(139, 92, 246, 0.15);
                border-color: #8b5cf6;
                color: #ffffff;
            }
            div[data-testid="stButton"] > button {
                border-radius: 12px;
                font-weight: 600;
            }
            div[data-testid="stDownloadButton"] > button {
                background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
                border: none;
                color: #ffffff;
                font-weight: 700;
                border-radius: 12px;
                box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4);
                transition: box-shadow 0.15s ease, transform 0.15s ease !important;
            }
            div[data-testid="stDownloadButton"] > button:hover {
                transform: translateY(-1px);
                box-shadow: 0 6px 20px rgba(16, 185, 129, 0.55);
            }
            div[data-testid="stVerticalBlockBorderWrapper"] {
                border-radius: 14px !important;
                border: 1px solid rgba(148, 163, 184, 0.1) !important;
                background: rgba(18, 22, 32, 0.7) !important;
                box-shadow:
                    0 1px 0 rgba(255, 255, 255, 0.03) inset,
                    0 2px 12px rgba(0, 0, 0, 0.15);
                transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:hover {
                border-color: rgba(139, 92, 246, 0.25) !important;
                box-shadow:
                    0 1px 0 rgba(255, 255, 255, 0.05) inset,
                    0 4px 16px rgba(139, 92, 246, 0.1);
            }
            div[data-testid="stSelectbox"] > div > div {
                background: rgba(18, 22, 32, 0.8);
                border: 1px solid rgba(148, 163, 184, 0.12);
                border-radius: 10px;
                transition: border-color 0.15s ease, background 0.15s ease !important;
            }
            div[data-testid="stSelectbox"] > div > div:hover {
                border-color: rgba(139, 92, 246, 0.45);
                background: rgba(139, 92, 246, 0.05);
            }
            div[data-testid="stSelectbox"] > div > div:focus-within {
                border-color: #8b5cf6;
                box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.15);
            }
            div[data-testid="stTextInput"] input,
            div[data-testid="stTextArea"] textarea,
            div[data-testid="stNumberInput"] input {
                background: rgba(18, 22, 32, 0.8) !important;
                border: 1px solid rgba(148, 163, 184, 0.12) !important;
                border-radius: 10px !important;
                color: #e2e8f0 !important;
                transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
            }
            div[data-testid="stTextInput"] input:focus,
            div[data-testid="stTextArea"] textarea:focus,
            div[data-testid="stNumberInput"] input:focus {
                border-color: #8b5cf6 !important;
                box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.15) !important;
                background: rgba(18, 22, 32, 1) !important;
            }
            div[data-testid="stTabs"] button[role="tab"] {
                border-radius: 10px 10px 0 0;
                font-weight: 600;
                color: #64748b;
                border: none !important;
                transition: color 0.15s ease, background 0.15s ease !important;
            }
            div[data-testid="stTabs"] button[role="tab"]:hover {
                color: #ffffff;
                background: rgba(139, 92, 246, 0.06);
            }
            div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
                color: #ffffff;
                background: linear-gradient(180deg, rgba(139, 92, 246, 0.18), transparent);
                border-bottom: 2px solid #8b5cf6 !important;
            }
            div[data-testid="stExpander"] {
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 14px;
                background: rgba(18, 22, 32, 0.6);
                overflow: hidden;
                transition: border-color 0.15s ease, background 0.15s ease !important;
            }
            div[data-testid="stExpander"]:hover {
                border-color: rgba(139, 92, 246, 0.3);
                background: rgba(139, 92, 246, 0.03);
            }
            div[data-testid="stExpander"] summary {
                font-weight: 650;
                color: #cbd5e1;
                padding: 0.75rem 1rem;
                transition: color 0.15s ease !important;
            }
            div[data-testid="stExpander"] summary:hover {
                color: #ffffff;
            }
            div[data-testid="stFileUploader"] section {
                border: 1.5px dashed rgba(139, 92, 246, 0.35);
                border-radius: 14px;
                background: rgba(139, 92, 246, 0.04);
                transition: border-color 0.15s ease, background 0.15s ease !important;
            }
            div[data-testid="stFileUploader"] section:hover {
                border-color: #8b5cf6;
                background: rgba(139, 92, 246, 0.08);
            }
            div[data-testid="stProgress"] > div > div > div > div {
                background: linear-gradient(90deg, #8b5cf6 0%, #6366f1 50%, #06b6d4 100%);
                background-size: 200% 100%;
                animation: psaiProgress 3s linear infinite;
                box-shadow: 0 0 12px rgba(139, 92, 246, 0.5);
            }
            @keyframes psaiProgress {
                0% { background-position: 0% 50%; }
                100% { background-position: 200% 50%; }
            }
            div[data-testid="stAlert"] {
                border-radius: 12px;
                border-left-width: 4px;
            }
            div[data-testid="stRadio"] label {
                padding: 6px 12px;
                border-radius: 8px;
                transition: background 0.15s ease, color 0.15s ease !important;
            }
            div[data-testid="stRadio"] label:hover {
                background: rgba(139, 92, 246, 0.06);
                color: #ffffff;
            }
            ::-webkit-scrollbar {
                width: 10px;
                height: 10px;
            }
            ::-webkit-scrollbar-track {
                background: rgba(15, 19, 32, 0.5);
                border-radius: 999px;
            }
            ::-webkit-scrollbar-thumb {
                background: linear-gradient(180deg, #8b5cf6, #6366f1);
                border-radius: 999px;
                border: 2px solid rgba(15, 19, 32, 0.8);
            }
            ::-webkit-scrollbar-thumb:hover {
                background: linear-gradient(180deg, #a78bfa, #818cf8);
            }
            hr {
                border: none;
                height: 1px;
                background: linear-gradient(90deg,
                    transparent 0%,
                    rgba(139, 92, 246, 0.3) 50%,
                    transparent 100%);
                margin: 24px 0;
            }
            section[data-testid="stSidebar"] {
                background: rgba(10, 13, 20, 0.95);
                border-right: 1px solid rgba(148, 163, 184, 0.08);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================================
    # 👤 USER HEADER
    # ========================================================================
    _render_user_header()
    st.markdown("---")

    # ========================================================================
    # 💰 COIN PANEL
    # ========================================================================
    with st.expander("💰 Coin — Balance, Calculator & History", expanded=False):
        coin_panel.render_coin_panel()

    # ========================================================================
    # 💳 PAYMENT PANEL
    # ========================================================================
    with st.expander("💳 Coin ဝယ်ရန် (Payment)", expanded=False):
        payment_panel.render_payment_panel()

    # ========================================================================
    # ⚙️ SIDEBAR
    # ========================================================================
    with st.sidebar:
        st.markdown(
            '<div style="font-size:0.95rem;font-weight:700;color:#e2e8f0;'
            'margin-bottom:8px;">⚙️ Settings</div>',
            unsafe_allow_html=True,
        )
        basic_settings.render_basic_settings(tr)

    # ========================================================================
    # 📽️ HEADER ROW
    # ========================================================================
    header_left, header_right = st.columns([2, 1])

    with header_left:
        st.markdown(
            """
            <div class="psai-header">
                <div class="psai-sticker">🎬</div>
                <div class="psai-title-wrap">
                    <div class="psai-title">PS AI Recap <span class="psai-badge">PRO</span></div>
                    <div class="psai-subtitle">Movie Recap Studio · v0.8.7</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with header_right:
        antivirus_settings.render_antivirus_panel(tr)

    # ========================================================================
    # 🖥️ MAIN WORKSPACE
    # ========================================================================
    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.markdown(
            '<div class="step-header">📥 Step 1 — Input (Video Upload & Script)</div>',
            unsafe_allow_html=True,
        )
        script_settings.render_script_panel(tr)

        st.markdown(
            '<div class="step-header">⚙️ Step 2 — Configure (Audio / Video / Subtitle)</div>',
            unsafe_allow_html=True,
        )

        config_row = st.columns(2)
        with config_row[0]:
            audio_settings.render_audio_panel(tr)
        with config_row[1]:
            video_settings.render_video_panel(tr)

        subtitle_settings.render_subtitle_panel(tr)
        system_settings.render_system_panel(tr)

        st.markdown(
            '<div class="step-header">🚀 Step 3 — Enhance (Advanced Studio)</div>',
            unsafe_allow_html=True,
        )
        advanced_features.render_advanced_features(tr)

    with right_col:
        advanced_features.render_video_preview_panel(tr)

    # ========================================================================
    # 📤 STEP 4: OUTPUT
    # ========================================================================
    st.markdown(
        '<div class="step-header">📤 Step 4 — Output (Generate & Export)</div>',
        unsafe_allow_html=True,
    )
    render_generate_button()
    render_export_jianying_button()

if __name__ == "__main__":
    main()