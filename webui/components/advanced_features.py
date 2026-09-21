import streamlit as st
import os
from app.config import config
from app.utils import utils

try:
    from app.services import voice_clone as _voice_clone
    _VOICE_CLONE_AVAILABLE = True
except Exception:
    _VOICE_CLONE_AVAILABLE = False

# ============================================================================
# ADMIN CONTACT INFO
# ============================================================================
ADMIN_TELEGRAM = "@Ps2005b"
ADMIN_EMAIL = ""

ADVANCED_CSS = """
<style>
    .adv-panel-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #f0f2f7;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .adv-panel-subtitle {
        font-size: 0.82rem;
        color: #8a90a3;
        margin-bottom: 16px;
    }
    .adv-section-header {
        font-size: 0.88rem;
        font-weight: 650;
        color: #a8b0c4;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin: 18px 0 10px;
        padding-bottom: 6px;
        border-bottom: 1px solid rgba(120, 130, 160, 0.12);
    }
    .adv-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        margin-left: 8px;
    }
    .adv-badge-pro {
        background: linear-gradient(135deg, #7c5cff, #4a8fff);
        color: #ffffff;
    }
    .adv-badge-beta {
        background: linear-gradient(135deg, #20bf6b, #0fb9b1);
        color: #ffffff;
    }
    .adv-style-card {
        text-align: center;
        padding: 12px 8px;
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(120, 130, 160, 0.15);
        color: #c8cfdf;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .adv-style-card.active {
        background: linear-gradient(135deg, rgba(124, 92, 255, 0.25), rgba(74, 143, 255, 0.25));
        border-color: #7c5cff;
        color: #ffffff;
    }
    .adv-style-icon {
        font-size: 1.4rem;
        display: block;
        margin-bottom: 4px;
    }
    .adv-info {
        padding: 10px 14px;
        border-left: 3px solid #7c5cff;
        background: rgba(124, 92, 255, 0.08);
        border-radius: 6px;
        font-size: 0.82rem;
        color: #b8bfd0;
        margin: 10px 0;
    }
    .adv-hero {
        background: linear-gradient(135deg, rgba(124, 92, 255, 0.18), rgba(74, 143, 255, 0.12));
        border: 1px solid rgba(124, 92, 255, 0.35);
        border-radius: 14px;
        padding: 18px 22px;
        margin-bottom: 18px;
    }
    .adv-hero-title {
        font-size: 1.4rem;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 4px;
    }
    .adv-hero-sub {
        font-size: 0.85rem;
        color: #b8bfd0;
    }
</style>
"""

def _inject_css():
    st.markdown(ADVANCED_CSS, unsafe_allow_html=True)

# ============================================================================
# 🎙 VOICE PREVIEW HANDLER
# ============================================================================
def _handle_voice_preview(voice_id: str, text: str, rate: float = 1.0,
                          pitch: float = 1.0, volume: int = 80):
    if not text or not text.strip():
        st.warning("⚠️ Please enter preview text first.")
        return

    if voice_id.startswith("mms:"):
        language = voice_id.split(":", 1)[1]
        try:
            from app.services import mms_tts
            if not mms_tts.is_available():
                st.error("❌ MMS-TTS is not available. Please run: pip install transformers scipy")
                return
            with st.spinner("🎙 Generating MMS-TTS preview..."):
                audio_path = mms_tts.synthesize(text, language=language)
            if not audio_path or not os.path.exists(audio_path):
                st.error("❌ Failed to generate MMS-TTS audio.")
                return
            if abs(volume - 80) > 1 or abs(rate - 1.0) > 0.01:
                adjusted_path = _post_process_audio(audio_path, rate=rate, volume=volume)
                if adjusted_path and os.path.exists(adjusted_path):
                    audio_path = adjusted_path
            st.success("✅ MMS-TTS preview ready!")
            with open(audio_path, "rb") as af:
                st.audio(af.read(), format="audio/wav")
        except Exception as e:
            st.error(f"❌ MMS-TTS error: {e}")
        return

    try:
        import asyncio
        import uuid
        import edge_tts
        edge_voice = voice_id
        if edge_voice.endswith("-fast"):
            edge_voice = edge_voice[: -len("-fast")]
        rate_pct = int(round((rate - 1.0) * 100))
        pitch_hz = int(round((pitch - 1.0) * 50))
        volume_pct = int(round((volume - 80)))
        with st.spinner(f"🎙 Generating Edge-TTS preview ({edge_voice})..."):
            temp_dir = utils.storage_dir("temp", create=True)
            audio_path = os.path.join(temp_dir, f"edge-preview-{uuid.uuid4()}.mp3")

            async def _synth():
                communicate = edge_tts.Communicate(
                    text=text, voice=edge_voice,
                    rate=f"{rate_pct:+d}%", pitch=f"{pitch_hz:+d}Hz",
                    volume=f"{volume_pct:+d}%",
                )
                await communicate.save(audio_path)
            asyncio.run(_synth())
        if audio_path and os.path.exists(audio_path):
            st.success(f"✅ Edge-TTS preview ready ({edge_voice})")
            with open(audio_path, "rb") as af:
                st.audio(af.read(), format="audio/mp3")
        else:
            st.error("❌ Failed to generate Edge-TTS audio.")
    except Exception as e:
        st.error(f"❌ Edge-TTS error: {e}")


def _post_process_audio(audio_path: str, rate: float = 1.0, volume: int = 80) -> str:
    try:
        import subprocess
        import uuid
        temp_dir = utils.storage_dir("temp", create=True)
        output_path = os.path.join(temp_dir, f"mms-adjusted-{uuid.uuid4()}.wav")
        filters = []
        if abs(volume - 80) > 1:
            filters.append(f"volume={volume / 80.0:.3f}")
        if abs(rate - 1.0) > 0.01:
            filters.append(f"atempo={rate:.3f}")
        if not filters:
            return audio_path
        ffmpeg_bin = "ffmpeg"
        try:
            import imageio_ffmpeg
            candidate = imageio_ffmpeg.get_ffmpeg_exe()
            if candidate and os.path.isfile(candidate):
                ffmpeg_bin = candidate
        except Exception:
            pass
        cmd = [ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error",
               "-i", audio_path, "-filter:a", ",".join(filters), output_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode == 0 and os.path.exists(output_path):
            return output_path
    except Exception:
        pass
    return audio_path


# ============================================================================
# 🔧 LLM HELPER
# ============================================================================
def _call_llm(prompt: str) -> str:
    raw = ""
    try:
        from app.services import llm as _llm
        for fn_name in ("generate_text", "generate", "chat", "ask", "invoke"):
            fn = getattr(_llm, fn_name, None)
            if callable(fn):
                try:
                    raw = fn(prompt)
                    if raw:
                        break
                except Exception:
                    continue
    except Exception:
        pass
    if not raw:
        try:
            from app.services.llm.manager import LLMManager
            manager = LLMManager()
            for fn_name in ("generate_text", "generate", "chat"):
                fn = getattr(manager, fn_name, None)
                if callable(fn):
                    try:
                        raw = fn(prompt)
                        if raw:
                            break
                    except Exception:
                        continue
        except Exception:
            pass
    if not raw:
        try:
            import requests
            provider = config.app.get("text_llm_provider", "openai")
            api_key = (config.app.get(f"text_{provider}_api_key", "") or
                       config.app.get("text_openai_api_key", ""))
            base_url = config.app.get(f"text_{provider}_base_url",
                                       config.app.get("text_openai_base_url", "https://api.openai.com/v1"))
            model = config.app.get(f"text_{provider}_model_name",
                                    config.app.get("text_openai_model_name", "gpt-4o-mini"))
            if api_key:
                resp = requests.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": [{"role": "user", "content": prompt}],
                          "temperature": 0.7, "max_tokens": 800},
                    timeout=30,
                )
                if resp.status_code == 200:
                    raw = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            pass
    return raw or ""


def _get_plot_text() -> str:
    for key in ("video_plot", "video_clip_json", "video_script"):
        val = st.session_state.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, list) and val:
            try:
                import json as _json
                return _json.dumps(val, ensure_ascii=False)[:3000]
            except Exception:
                pass
    return ""


# ============================================================================
# 💎 PREMIUM CHECK HELPER
# ============================================================================
def _is_premium_user() -> bool:
    """User Monthly Active ဖြစ်/မဖြစ် စစ်"""
    try:
        from app.services import coin_system as _cs
        user_id = st.session_state.get("user_id")
        if not user_id:
            return False
        return _cs.is_monthly_active(user_id)
    except Exception:
        return False


def _render_premium_required():
    """Premium Feature — Monthly Required Message"""
    html = (
        '<div style="padding:22px 26px;border-radius:16px;'
        'background:radial-gradient(circle at 0% 0%, rgba(139,92,246,0.2), transparent 55%),'
        'radial-gradient(circle at 100% 100%, rgba(6,182,212,0.12), transparent 55%),'
        'linear-gradient(135deg, rgba(18,22,32,0.95), rgba(30,35,55,0.9));'
        'border:1.5px solid rgba(139,92,246,0.5);margin:14px 0;">'
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">'
        '<span style="font-size:2rem;">💎</span>'
        '<div>'
        '<div style="font-size:1.15rem;font-weight:800;color:#c4b5fd;">'
        'Premium Feature — Monthly Required'
        '</div>'
        '<div style="font-size:0.82rem;color:#94a3b8;margin-top:4px;">'
        '🎙 Voice Clone ကို သုံးဖို့ Monthly Subscription လိုအပ်ပါတယ်'
        '</div>'
        '</div>'
        '</div>'
        '<div style="padding:14px 18px;border-radius:12px;'
        'background:rgba(18,22,32,0.5);border-left:3px solid #8b5cf6;'
        'font-size:0.85rem;color:#cbd5e1;line-height:1.9;">'
        '✅ ၁၅၀ Coin လစဉ်<br>'
        '✅ Voice Clone သုံးခွင့်<br>'
        '✅ 1080p HD Export<br>'
        '✅ Priority Queue (၃ ဆ မြန်)<br>'
        '✅ Premium Features အားလုံး'
        '</div>'
        '<div style="margin-top:14px;padding:12px 16px;border-radius:10px;'
        'background:linear-gradient(135deg,rgba(16,185,129,0.15),rgba(6,182,212,0.08));'
        'border:1px solid rgba(16,185,129,0.4);font-size:0.85rem;'
        'color:#34d399;font-weight:700;text-align:center;">'
        '👉 Payment Panel → Monthly Subscription ဝယ်ပါ — ၃,၀၀၀ ကျပ်/လ'
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ============================================================================
# 🏷 AI TAGS
# ============================================================================
def _generate_ai_tags(plot_text: str, hint: str = "") -> list:
    if not plot_text or not plot_text.strip():
        return []
    prompt = ("Based on this video plot/script, generate 10-15 short SEO-optimized tags. "
              "Return ONLY the tags as a comma-separated list. No numbering, no explanations.\n\n"
              f"Plot/Script:\n{plot_text[:2000]}\n\n")
    if hint:
        prompt += f"Hint: {hint}\n\n"
    prompt += "Tags:"
    raw = _call_llm(prompt)
    if not raw:
        return []
    cleaned = raw.replace("\n", ",").replace(";", ",").replace("|", ",").replace("#", "")
    tags, seen = [], set()
    for chunk in cleaned.split(","):
        tag = chunk.strip().strip(".-*•").strip()
        if not tag or len(tag) > 40:
            continue
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        tags.append(tag)
        if len(tags) >= 15:
            break
    return tags


# ============================================================================
# 📝 AI TITLE
# ============================================================================
def _generate_ai_titles(plot_text: str, hint: str = "", count: int = 5) -> list:
    if not plot_text or not plot_text.strip():
        return []
    prompt = (f"Based on this video plot/script, generate {count} catchy, SEO-optimized titles. "
              "Titles should be 40-70 characters, emotional, and click-worthy. "
              "Return ONLY the titles, one per line. No numbering, no explanations.\n\n"
              f"Plot/Script:\n{plot_text[:2000]}\n\n")
    if hint:
        prompt += f"Keyword hint: {hint}\n\n"
    prompt += "Titles:"
    raw = _call_llm(prompt)
    if not raw:
        return []
    titles, seen = [], set()
    for line in raw.split("\n"):
        title = line.strip().strip(".-*•1234567890) ").strip().strip('"').strip("'")
        if not title or len(title) < 10 or len(title) > 120:
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        titles.append(title)
        if len(titles) >= count:
            break
    return titles


# ============================================================================
# 🖼 AI THUMBNAIL
# ============================================================================
def _generate_ai_thumbnail(plot_text: str, style: str = "Cinematic", ratio: str = "16:9") -> list:
    if not plot_text or not plot_text.strip():
        return []
    style_map = {
        "Cinematic": "cinematic movie poster, dramatic lighting, film still",
        "Bold Text": "bold text overlay, movie poster, high contrast",
        "Minimal": "minimalist design, clean composition, modern poster",
        "Dramatic": "dramatic scene, intense emotion, dark atmosphere",
    }
    style_prompt = style_map.get(style, "cinematic movie poster")
    plot_excerpt = " ".join(plot_text.split()[:60])[:300]
    base_prompt = f"{style_prompt}, {plot_excerpt}, movie poster, high quality, professional, 8k, no text, no watermark"
    ratio_dims = {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (1024, 1024)}
    width, height = ratio_dims.get(ratio, (1280, 720))
    import urllib.parse
    import uuid as _uuid
    seed = _uuid.uuid4().int % 1000000
    return [f"https://image.pollinations.ai/prompt/{urllib.parse.quote(base_prompt)}?width={width}&height={height}&seed={seed}&nologo=true"]


# ============================================================================
# 🎬 VIDEO PREVIEW
# ============================================================================
def render_video_preview_panel(tr):
    _inject_css()
    with st.container(border=True):
        st.markdown('<div class="adv-panel-title">🎬 Video Preview</div>'
                    '<div class="adv-panel-subtitle">Live preview of your selected video.</div>',
                    unsafe_allow_html=True)
        preview_video_path = _resolve_preview_video_path()
        if not preview_video_path:
            st.info("📁 Please select or upload a video above.")
            return
        try:
            file_size_mb = os.path.getsize(preview_video_path) / (1024 * 1024)
            st.caption(f"📽 **{os.path.basename(preview_video_path)}** · {file_size_mb:.1f} MB")
        except OSError:
            st.caption(f"📽 {os.path.basename(preview_video_path)}")
        try:
            st.video(preview_video_path)
        except Exception as e:
            st.warning(f"Unable to preview: {e}")
            return
        st.markdown('<div class="adv-section-header">✨ Active Effects</div>', unsafe_allow_html=True)
        active_effects = _collect_active_effects()
        if not active_effects:
            st.caption("No effects enabled.")
        else:
            for effect in active_effects:
                st.markdown(f'<div class="adv-info">✅ {effect}</div>', unsafe_allow_html=True)


def _resolve_preview_video_path():
    candidates = [st.session_state.get("video_origin_path"), st.session_state.get("uploaded_video_path")]
    video_paths = st.session_state.get("video_origin_paths", [])
    if isinstance(video_paths, list):
        candidates.extend(video_paths)
    for path in candidates:
        if isinstance(path, str) and path and os.path.exists(path):
            return path
    return ""


def _collect_active_effects():
    effects = []
    cinematic = st.session_state.get("cinematic_style", "None")
    if cinematic and cinematic != "None":
        effects.append(f"Cinematic: {cinematic}")
    try:
        zoom = float(st.session_state.get("adjust_zoom_widget", 1.0) or 1.0)
    except (TypeError, ValueError):
        zoom = 1.0
    if zoom > 1.001:
        effects.append(f"Zoom: {zoom:.1f}x")
    try:
        v_speed = float(st.session_state.get("adjust_video_speed_widget", 1.0) or 1.0)
    except (TypeError, ValueError):
        v_speed = 1.0
    if abs(v_speed - 1.0) > 0.001:
        effects.append(f"Video Speed: {v_speed:.1f}x")
    try:
        voice_speed = float(st.session_state.get("adjust_voice_speed_widget", 1.0) or 1.0)
    except (TypeError, ValueError):
        voice_speed = 1.0
    if abs(voice_speed - 1.0) > 0.001:
        effects.append(f"Voice Speed: {voice_speed:.1f}x")
    if st.session_state.get("watermark_enabled"):
        effects.append(f"Watermark: '{st.session_state.get('watermark_text_widget', '')}'")
    if st.session_state.get("logo_enabled"):
        effects.append("Logo overlay")
    if st.session_state.get("blur_boxes_enabled"):
        effects.append(f"Blur Boxes: {st.session_state.get('blur_boxes_count_widget', 0)}")
    if st.session_state.get("ai_thumbnail_enabled"):
        effects.append("AI Thumbnail")
    if st.session_state.get("ai_title_enabled"):
        effects.append("AI Title")
    if st.session_state.get("ai_auto_subtitle"):
        effects.append("Auto Subtitle")
    if st.session_state.get("ai_auto_cut"):
        effects.append("Auto Cut")
    if st.session_state.get("ai_tags_enabled"):
        effects.append("AI Tags")
    if st.session_state.get("voice_clone_enabled"):
        effects.append(f"Voice Clone: {st.session_state.get('voice_clone_engine', '')}")
    if st.session_state.get("antivirus_auto_mode_widget"):
        effects.append("Anti-Virus Auto Mode")
    if st.session_state.get("subtitle_enabled", True):
        effects.append("Subtitles")
    if st.session_state.get("subtitle_mask_enabled"):
        effects.append("Subtitle Mask")
    return effects


# ============================================================================
# 🎬 CINEMATIC PANEL
# ============================================================================
def render_cinematic_panel(tr):
    _inject_css()
    with st.container(border=True):
        st.markdown('<div class="adv-panel-title">🎬 Cinematic Style</div>'
                    '<div class="adv-panel-subtitle">Apply cinematic color grading.</div>',
                    unsafe_allow_html=True)
        style_options = [("🚫", "None"), ("🎬", "Cinema"), ("🌆", "Teal"), ("⚫️", "Noir"), ("🩸", "Horror")]
        selected = st.session_state.get("cinematic_style", "None")
        cols = st.columns(len(style_options))
        for idx, (icon, name) in enumerate(style_options):
            with cols[idx]:
                is_active = "active" if selected == name else ""
                st.markdown(f'<div class="adv-style-card {is_active}">'
                            f'<span class="adv-style-icon">{icon}</span>{name}</div>',
                            unsafe_allow_html=True)
                if st.button("Select", key=f"cinematic_{name}", use_container_width=True):
                    st.session_state["cinematic_style"] = name
                    st.rerun()


# ============================================================================
# ⚙️ ADJUSTMENTS PANEL — 🎯 PENDING VALUE PATTERN
# ============================================================================
def render_adjustments_panel(tr):
    _inject_css()
    with st.container(border=True):
        st.markdown('<div class="adv-panel-title">⚙️ Adjustments</div>'
                    '<div class="adv-panel-subtitle">Fine-tune zoom, speed, and aspect ratio.</div>',
                    unsafe_allow_html=True)

        # ====================================================================
        # 🎯 Pending Value Apply — Widget မတိုင်ခင်
        # ====================================================================
        _pending_aspect = st.session_state.pop("_pending_adjust_aspect", None)
        if _pending_aspect is not None:
            st.session_state["adjust_aspect_widget"] = _pending_aspect

        st.markdown('<div class="adv-section-header">🔍 Zoom</div>', unsafe_allow_html=True)
        st.slider("Zoom Level", min_value=1.0, max_value=3.0,
                  value=float(st.session_state.get("adjust_zoom", 1.0)),
                  step=0.1, key="adjust_zoom_widget")
        st.markdown('<div class="adv-section-header">🎬 Video Speed</div>', unsafe_allow_html=True)
        st.slider("Video Speed", min_value=0.5, max_value=3.0,
                  value=float(st.session_state.get("adjust_video_speed", 1.0)),
                  step=0.1, key="adjust_video_speed_widget")
        st.markdown('<div class="adv-section-header">🔊 Voice Speed</div>', unsafe_allow_html=True)
        st.slider("Voice Speed", min_value=0.5, max_value=3.0,
                  value=float(st.session_state.get("adjust_voice_speed", 1.0)),
                  step=0.1, key="adjust_voice_speed_widget")
        st.markdown('<div class="adv-section-header">📐 Aspect Ratio</div>', unsafe_allow_html=True)
        st.selectbox("Aspect Ratio", ["Auto", "9:16", "16:9", "1:1", "4:5"], key="adjust_aspect_widget")
        st.markdown('<div class="adv-section-header">🎨 Auto Blur BG</div>', unsafe_allow_html=True)
        auto_blur_bg = st.toggle("Enable Auto Blur Background",
                                  value=bool(st.session_state.get("adjust_auto_blur_bg", False)),
                                  key="adjust_auto_blur_bg_widget")
        st.session_state["adjust_auto_blur_bg"] = auto_blur_bg


# ============================================================================
# 🤖 AI FEATURES PANEL
# ============================================================================
def render_ai_features_panel(tr):
    _inject_css()
    with st.container(border=True):
        st.markdown('<div class="adv-panel-title">🤖 AI Features '
                    '<span class="adv-badge adv-badge-pro">PRO</span></div>'
                    '<div class="adv-panel-subtitle">AI-powered thumbnail, title, subtitle, and auto-cut.</div>',
                    unsafe_allow_html=True)

        st.markdown('<div class="adv-section-header">🖼 Thumbnail</div>', unsafe_allow_html=True)
        thumb_enable = st.toggle("Enable AI Thumbnail",
                                  value=bool(st.session_state.get("ai_thumbnail_enabled", False)),
                                  key="ai_thumbnail_widget")
        st.session_state["ai_thumbnail_enabled"] = thumb_enable
        if thumb_enable:
            thumb_cols = st.columns([1, 1, 1])
            with thumb_cols[0]:
                st.selectbox("Style", ["Cinematic", "Bold Text", "Minimal", "Dramatic"], key="ai_thumb_style_widget")
            with thumb_cols[1]:
                st.selectbox("Ratio", ["16:9", "9:16", "1:1"], key="ai_thumb_ratio_widget")
            with thumb_cols[2]:
                st.number_input("Count", min_value=1, max_value=10, value=3, key="ai_thumb_count_widget")
            thumb_plot_text = _get_plot_text()
            if thumb_plot_text:
                if st.button("🎨 Generate Thumbnails", key="ai_thumb_generate_btn", use_container_width=True):
                    with st.spinner("Generating thumbnails..."):
                        style = st.session_state.get("ai_thumb_style_widget", "Cinematic")
                        ratio = st.session_state.get("ai_thumb_ratio_widget", "16:9")
                        count = int(st.session_state.get("ai_thumb_count_widget", 3))
                        urls = []
                        for _ in range(count):
                            urls.extend(_generate_ai_thumbnail(thumb_plot_text, style, ratio))
                        if urls:
                            st.session_state["ai_thumb_result"] = urls
                            st.success(f"✅ {len(urls)} thumbnail(s) generated")
            for idx, url in enumerate(st.session_state.get("ai_thumb_result", []), start=1):
                st.markdown(f"**Thumbnail #{idx}**")
                st.image(url, use_container_width=True)

        st.markdown('<div class="adv-section-header">📝 Title Generator</div>', unsafe_allow_html=True)
        title_enable = st.toggle("Enable AI Title",
                                  value=bool(st.session_state.get("ai_title_enabled", False)),
                                  key="ai_title_widget")
        st.session_state["ai_title_enabled"] = title_enable
        if title_enable:
            title_plot_text = _get_plot_text()
            if not title_plot_text:
                st.caption("📄 Plot/script not loaded yet.")
            title_hint = st.text_input("Title Keyword Hint (optional)",
                                        value=st.session_state.get("ai_title_hint", ""),
                                        key="ai_title_hint_widget",
                                        placeholder="e.g. revenge, prison, mother")
            st.session_state["ai_title_hint"] = title_hint
            title_count = st.slider("Number of Titles", min_value=3, max_value=10,
                                     value=int(st.session_state.get("ai_title_count", 5)),
                                     key="ai_title_count_widget")
            st.session_state["ai_title_count"] = title_count
            t_gen_col, t_clear_col = st.columns([3, 1])
            with t_gen_col:
                if st.button("🎯 Generate Titles", key="ai_title_generate_btn",
                             use_container_width=True, disabled=not title_plot_text):
                    with st.spinner("Generating titles..."):
                        new_titles = _generate_ai_titles(title_plot_text, hint=title_hint, count=title_count)
                    if new_titles:
                        st.session_state["ai_title_result"] = new_titles
                        st.success(f"✅ {len(new_titles)} titles generated")
            with t_clear_col:
                if st.button("🗑", key="ai_title_clear_btn", use_container_width=True):
                    st.session_state["ai_title_result"] = []
                    st.rerun()
            for idx, title in enumerate(st.session_state.get("ai_title_result", []), start=1):
                st.markdown(
                    f'<div style="padding:8px 12px;margin:5px 0;border-radius:8px;'
                    f'background:rgba(139,92,246,0.08);border-left:3px solid #8b5cf6;'
                    f'font-size:0.85rem;color:#e2e8f0;font-weight:600;">'
                    f'<span style="color:#8b5cf6;font-weight:800;margin-right:8px;">#{idx}</span>{title}</div>',
                    unsafe_allow_html=True)

        st.markdown('<div class="adv-section-header">💬 Auto Subtitle</div>', unsafe_allow_html=True)
        auto_sub_enable = st.toggle("Enable Auto Subtitle",
                                     value=bool(st.session_state.get("ai_auto_subtitle", False)),
                                     key="ai_auto_sub_widget")
        st.session_state["ai_auto_subtitle"] = auto_sub_enable
        if auto_sub_enable:
            sub_cols = st.columns(2)
            with sub_cols[0]:
                st.selectbox("Language", ["Burmese", "English", "Chinese", "Auto Detect"], key="ai_auto_sub_lang_widget")
            with sub_cols[1]:
                st.selectbox("Position", ["Bottom", "Top", "Center"], key="ai_auto_sub_pos_widget")

        st.markdown('<div class="adv-section-header">✂️ Auto Cut</div>', unsafe_allow_html=True)
        auto_cut_enable = st.toggle("Enable Auto Cut",
                                     value=bool(st.session_state.get("ai_auto_cut", False)),
                                     key="ai_auto_cut_widget")
        st.session_state["ai_auto_cut"] = auto_cut_enable
        if auto_cut_enable:
            st.slider("Clip Duration (seconds)", min_value=1, max_value=15, value=3,
                      key="ai_auto_cut_duration_widget")

        st.markdown('<div class="adv-section-header">🏷 Auto Tags</div>', unsafe_allow_html=True)
        tags_enable = st.toggle("Enable Auto Tags",
                                 value=bool(st.session_state.get("ai_tags_enabled", False)),
                                 key="ai_tags_widget")
        st.session_state["ai_tags_enabled"] = tags_enable
        if tags_enable:
            tags_plot_text = _get_plot_text()
            if not tags_plot_text:
                st.caption("📄 Plot/script not loaded yet.")
            tags_hint = st.text_input("Tag Hint (optional)",
                                       value=st.session_state.get("ai_tags_hint", ""),
                                       key="ai_tags_hint_widget",
                                       placeholder="e.g. revenge, prison, mother")
            st.session_state["ai_tags_hint"] = tags_hint
            gen_col, clear_col = st.columns([3, 1])
            with gen_col:
                if st.button("🎯 Generate Tags", key="ai_tags_generate_btn",
                             use_container_width=True, disabled=not tags_plot_text):
                    with st.spinner("Generating tags..."):
                        new_tags = _generate_ai_tags(tags_plot_text, hint=tags_hint)
                    if new_tags:
                        st.session_state["ai_tags_result"] = new_tags
                        st.success(f"✅ {len(new_tags)} tags generated")
            with clear_col:
                if st.button("🗑", key="ai_tags_clear_btn", use_container_width=True):
                    st.session_state["ai_tags_result"] = []
                    st.rerun()
            tags_result = st.session_state.get("ai_tags_result", [])
            if tags_result:
                st.markdown(
                    '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:10px;'
                    'padding:10px;border-radius:10px;background:rgba(139,92,246,0.06);'
                    'border:1px solid rgba(139,92,246,0.18);">'
                    + "".join(
                        f'<span style="display:inline-block;padding:4px 10px;'
                        f'border-radius:999px;font-size:0.76rem;font-weight:600;'
                        f'background:rgba(139,92,246,0.15);color:#c4b5fd;'
                        f'border:1px solid rgba(139,92,246,0.3);">{t}</span>'
                        for t in tags_result
                    ) + "</div>",
                    unsafe_allow_html=True,
                )


# ============================================================================
# 💧 WATERMARK PANEL
# ============================================================================
def render_watermark_panel(tr):
    _inject_css()
    with st.container(border=True):
        st.markdown('<div class="adv-panel-title">💧 Watermark</div>'
                    '<div class="adv-panel-subtitle">Add text watermark with modern styles.</div>',
                    unsafe_allow_html=True)
        wm_enable = st.toggle("Enable Watermark",
                               value=bool(st.session_state.get("watermark_enabled", False)),
                               key="watermark_enable_widget")
        st.session_state["watermark_enabled"] = wm_enable
        if not wm_enable:
            return
        st.text_input("Watermark Text", value=st.session_state.get("watermark_text", "@PSAI"),
                      key="watermark_text_widget")
        st.markdown('<div class="adv-section-header">🔤 Font</div>', unsafe_allow_html=True)
        st.selectbox("Font Family",
                     ["Inter (Modern)", "Arial", "Georgia (Serif)", "Impact (Bold)",
                      "Courier New", "Times New Roman", "Trebuchet MS", "Verdana"],
                     key="watermark_font_widget")
        st.markdown('<div class="adv-section-header">✨ Style</div>', unsafe_allow_html=True)
        style_cols = st.columns(3)
        style_options = ["None", "Shadow", "Outline", "Neon Glow", "Soft Glow", "3D Text"]
        selected_style = st.session_state.get("watermark_style", "Shadow")
        style_index = style_options.index(selected_style) if selected_style in style_options else 1
        with style_cols[0]:
            st.selectbox("Effect", style_options, index=style_index, key="watermark_style_widget")
        with style_cols[1]:
            st.color_picker("Text Color", value=st.session_state.get("watermark_color", "#FFFFFF"),
                            key="watermark_color_widget")
        with style_cols[2]:
            st.color_picker("Shadow Color", value=st.session_state.get("watermark_shadow_color", "#000000"),
                            key="watermark_shadow_color_widget")
        st.markdown('<div class="adv-section-header">🎬 Animation</div>', unsafe_allow_html=True)
        anim_cols = st.columns(2)
        with anim_cols[0]:
            st.selectbox("Animation Style",
                         ["📍 Static", "🎬 Moving (Sine Wave)", "➡️ Marquee Right",
                          "⬅️ Marquee Left", "↘️ Diagonal", "↻ Loop Circle", "✨ Fade In/Out"],
                         key="watermark_animation_widget")
        with anim_cols[1]:
            st.slider("Speed", min_value=0.5, max_value=5.0,
                      value=float(st.session_state.get("watermark_speed", 2.0)),
                      step=0.5, key="watermark_speed_widget")
        st.markdown('<div class="adv-section-header">📏 Size & Opacity</div>', unsafe_allow_html=True)
        size_cols = st.columns(2)
        with size_cols[0]:
            st.slider("Size (px)", min_value=10, max_value=150,
                      value=int(st.session_state.get("watermark_size", 40)), step=2, key="watermark_size_widget")
        with size_cols[1]:
            st.slider("Opacity (%)", min_value=0, max_value=100,
                      value=int(st.session_state.get("watermark_opacity", 70)), step=5, key="watermark_opacity_widget")
        st.markdown('<div class="adv-section-header">📍 Position</div>', unsafe_allow_html=True)
        pos_cols = st.columns(2)
        with pos_cols[0]:
            st.slider("X (%)", min_value=0, max_value=100,
                      value=int(st.session_state.get("watermark_x", 10)), key="watermark_x_widget")
        with pos_cols[1]:
            st.slider("Y (%)", min_value=0, max_value=100,
                      value=int(st.session_state.get("watermark_y", 10)), key="watermark_y_widget")


# ============================================================================
# 🖼 LOGO PANEL
# ============================================================================
def render_logo_panel(tr):
    _inject_css()
    with st.container(border=True):
        st.markdown('<div class="adv-panel-title">🖼 Logo & Branding</div>'
                    '<div class="adv-panel-subtitle">Add your channel logo with effects and filters.</div>',
                    unsafe_allow_html=True)
        logo_enable = st.toggle("Enable Logo",
                                 value=bool(st.session_state.get("logo_enabled", False)),
                                 key="logo_enable_widget")
        st.session_state["logo_enabled"] = logo_enable
        if not logo_enable:
            return
        uploaded_logo = st.file_uploader("Upload Logo (PNG/JPG/SVG)",
                                           type=["png", "jpg", "jpeg", "svg"],
                                           key="logo_upload_widget")
        if uploaded_logo is not None:
            st.success(f"Logo uploaded: {uploaded_logo.name}")
        st.markdown('<div class="adv-section-header">✨ Effect</div>', unsafe_allow_html=True)
        st.selectbox("Effect", ["None", "Shadow", "Glow", "Blur"], key="logo_effect_widget")
        st.markdown('<div class="adv-section-header">🎨 Filter</div>', unsafe_allow_html=True)
        st.selectbox("Filter", ["Normal", "White", "Rounded"], key="logo_filter_widget")
        st.markdown('<div class="adv-section-header">📏 Size & Opacity</div>', unsafe_allow_html=True)
        logo_cols = st.columns(2)
        with logo_cols[0]:
            st.slider("Size (px)", min_value=20, max_value=300,
                      value=int(st.session_state.get("logo_size", 80)), step=5, key="logo_size_widget")
        with logo_cols[1]:
            st.slider("Opacity (%)", min_value=0, max_value=100,
                      value=int(st.session_state.get("logo_opacity", 80)), step=5, key="logo_opacity_widget")
        st.markdown('<div class="adv-section-header">🔄 Rotation</div>', unsafe_allow_html=True)
        st.slider("Rotation (degrees)", min_value=0, max_value=360,
                  value=int(st.session_state.get("logo_rotation", 0)), step=5, key="logo_rotation_widget")
        st.markdown('<div class="adv-section-header">📍 Position</div>', unsafe_allow_html=True)
        logo_pos_cols = st.columns(2)
        with logo_pos_cols[0]:
            st.slider("X (%)", min_value=0, max_value=100,
                      value=int(st.session_state.get("logo_x", 80)), key="logo_x_widget")
        with logo_pos_cols[1]:
            st.slider("Y (%)", min_value=0, max_value=100,
                      value=int(st.session_state.get("logo_y", 5)), key="logo_y_widget")


# ============================================================================
# 🌫 BLUR BOXES PANEL
# ============================================================================
def render_blur_boxes_panel(tr):
    _inject_css()
    with st.container(border=True):
        st.markdown('<div class="adv-panel-title">🌫 Blur Boxes</div>'
                    '<div class="adv-panel-subtitle">Cover unwanted areas with blurred boxes.</div>',
                    unsafe_allow_html=True)
        blur_enable = st.toggle("Enable Blur Boxes",
                                 value=bool(st.session_state.get("blur_boxes_enabled", False)),
                                 key="blur_boxes_enable_widget")
        st.session_state["blur_boxes_enabled"] = blur_enable
        if not blur_enable:
            return
        num_boxes = st.slider("Number of Blur Boxes", min_value=1, max_value=5, value=3,
                              key="blur_boxes_count_widget")
        for i in range(1, num_boxes + 1):
            with st.expander(f"🌫 Blur Box {i}", expanded=(i == 1)):
                col1, col2 = st.columns(2)
                with col1:
                    st.slider("X (%)", min_value=0, max_value=100, value=10, key=f"blur_box_{i}_x")
                    st.slider("Width (%)", min_value=1, max_value=100, value=30, key=f"blur_box_{i}_width")
                with col2:
                    st.slider("Y (%)", min_value=0, max_value=100, value=10, key=f"blur_box_{i}_y")
                    st.slider("Height (%)", min_value=1, max_value=100, value=20, key=f"blur_box_{i}_height")
                st.slider("Blur Radius", min_value=1, max_value=50, value=15, key=f"blur_box_{i}_radius")


# ============================================================================
# 🎙 VOICE STUDIO PANEL — WITH PREMIUM CHECK
# ============================================================================
def render_voice_studio_panel(tr):
    _inject_css()
    with st.container(border=True):
        st.markdown('<div class="adv-panel-title">🎙 Voice Studio '
                    '<span class="adv-badge adv-badge-pro">PRO</span></div>'
                    '<div class="adv-panel-subtitle">Preview voices, clone your own, and pick presets.</div>',
                    unsafe_allow_html=True)

        tab_library, tab_clone = st.tabs(["📚 Voice Library", "🎤 Voice Clone"])

        with tab_library:
            st.markdown('<div class="adv-section-header">📚 Voice Library</div>', unsafe_allow_html=True)
            voice_library = [
                ("👩 Nilar (Female)", "my-MM-NilarNeural"),
                ("👨 Thiha (Male)", "my-MM-ThihaNeural"),
                ("👩 Female (Fast)", "my-MM-NilarNeural-fast"),
                ("🇲🇲 MMS-TTS (Burmese)", "mms:mya"),
                ("🇬🇧 English Female", "en-US-JennyNeural"),
                ("🇬🇧 English Male", "en-US-GuyNeural"),
                ("🇨🇳 Chinese Female", "zh-CN-XiaoxiaoNeural"),
            ]
            selected_voice = st.selectbox(
                "Select Voice",
                options=[v[1] for v in voice_library],
                format_func=lambda x: next((v[0] for v in voice_library if v[1] == x), x),
                key="voice_studio_select_widget",
            )
            st.session_state["voice_studio_selected"] = selected_voice

            st.markdown('<div class="adv-section-header">📝 Preview Text</div>', unsafe_allow_html=True)
            default_preview_text = "မင်္ဂလာပါ။ ဒါက PSAI ရဲ့ voice preview ဖြစ်ပါတယ်။"
            preview_text = st.text_area(
                "Text to preview",
                value=st.session_state.get("voice_studio_preview_text", default_preview_text),
                height=100, key="voice_studio_text_widget",
                label_visibility="collapsed",
                placeholder="Enter text to preview the voice...",
            )
            st.session_state["voice_studio_preview_text"] = preview_text

            char_count = len(preview_text or "")
            word_count = len((preview_text or "").split())
            estimated_seconds = max(1, round(char_count / 12))
            st.markdown(
                f'<div class="adv-info">📊 <b>Characters:</b> {char_count} · '
                f'📝 <b>Words:</b> {word_count} · ⏱ <b>Est. Duration:</b> ~{estimated_seconds}s</div>',
                unsafe_allow_html=True,
            )

            st.markdown('<div class="adv-section-header">⚙️ Voice Settings</div>', unsafe_allow_html=True)
            voice_cols = st.columns(3)
            with voice_cols[0]:
                rate = st.slider("Speed (Speaking Rate)", min_value=0.5, max_value=2.0,
                                  value=float(st.session_state.get("voice_studio_rate", 1.0)),
                                  step=0.1, key="voice_studio_rate_widget")
            with voice_cols[1]:
                pitch = st.slider("Voice Tone (Pitch)", min_value=0.5, max_value=2.0,
                                   value=float(st.session_state.get("voice_studio_pitch", 1.0)),
                                   step=0.1, key="voice_studio_pitch_widget")
            with voice_cols[2]:
                volume = st.slider("Loudness (Volume)", min_value=0, max_value=100,
                                    value=int(st.session_state.get("voice_studio_volume", 80)),
                                    step=5, key="voice_studio_volume_widget")

            preview_cols = st.columns([3, 1])
            with preview_cols[0]:
                if st.button("🔊 Preview Voice", key="voice_studio_preview_btn", use_container_width=True):
                    _handle_voice_preview(selected_voice, preview_text, rate=rate, pitch=pitch, volume=volume)
            with preview_cols[1]:
                if st.button("🔄 Reset", key="voice_studio_reset_btn", use_container_width=True):
                    st.session_state["voice_studio_preview_text"] = default_preview_text
                    st.session_state["voice_studio_rate_widget"] = 1.0
                    st.session_state["voice_studio_pitch_widget"] = 1.0
                    st.session_state["voice_studio_volume_widget"] = 80
                    st.rerun()

            st.markdown('<div class="adv-section-header">🎯 Quick Presets</div>', unsafe_allow_html=True)
            preset_cols = st.columns(3)
            with preset_cols[0]:
                if st.button("🎬 Narration", key="voice_preset_narration", use_container_width=True):
                    st.session_state["voice_studio_rate_widget"] = 1.0
                    st.session_state["voice_studio_pitch_widget"] = 1.0
                    st.session_state["voice_studio_volume_widget"] = 80
                    st.rerun()
            with preset_cols[1]:
                if st.button("📰 News", key="voice_preset_news", use_container_width=True):
                    st.session_state["voice_studio_rate_widget"] = 1.2
                    st.session_state["voice_studio_pitch_widget"] = 1.0
                    st.session_state["voice_studio_volume_widget"] = 85
                    st.rerun()
            with preset_cols[2]:
                if st.button("🎭 Drama", key="voice_preset_drama", use_container_width=True):
                    st.session_state["voice_studio_rate_widget"] = 0.9
                    st.session_state["voice_studio_pitch_widget"] = 1.1
                    st.session_state["voice_studio_volume_widget"] = 90
                    st.rerun()

        # ====================================================================
        # VOICE CLONE TAB — WITH PREMIUM CHECK
        # ====================================================================
        with tab_clone:
            clone_enable = st.toggle(
                "Enable Voice Clone",
                value=bool(st.session_state.get("voice_clone_enabled", False)),
                key="voice_clone_enable_widget",
            )
            st.session_state["voice_clone_enabled"] = clone_enable

            if not clone_enable:
                st.caption("Enable to select a clone engine and upload reference audio.")
            else:
                # ============================================================
                # 💎 PREMIUM CHECK — Monthly Subscription Required
                # ============================================================
                if not _is_premium_user():
                    _render_premium_required()
                    return

                # ============================================================
                # ✅ PREMIUM ACTIVE — Voice Clone Panel
                # ============================================================
                st.markdown('<div class="adv-section-header">⚙️ Clone Engine</div>', unsafe_allow_html=True)

                engine_options = [
                    ("IndexTTS-1.5 (Windows Local)", "indextts"),
                    ("IndexTTS-1.5 (macOS MLX)", "indextts_macos"),
                    ("IndexTTS-2 (MLX)", "indextts2"),
                    ("OmniVoice (Multilingual)", "omnivoice"),
                    ("VoxCPM-0.5B", "voxcpm_05b"),
                    ("VoxCPM-2B", "voxcpm_2b"),
                ]

                selected_engine = st.selectbox(
                    "Clone Engine",
                    options=[e[1] for e in engine_options],
                    format_func=lambda x: next((e[0] for e in engine_options if e[1] == x), x),
                    key="voice_clone_engine_widget",
                )
                st.session_state["voice_clone_engine"] = selected_engine

                engine_running = False
                engine_name = selected_engine

                if _VOICE_CLONE_AVAILABLE:
                    try:
                        engine_running = _voice_clone.is_available(selected_engine)
                        engine_name = _voice_clone.get_engine_display_name(selected_engine)
                    except Exception:
                        engine_running = False

                if engine_running:
                    online_html = (
                        '<div style="padding:16px 20px;border-radius:14px;'
                        'background:linear-gradient(135deg,rgba(16,185,129,0.15),rgba(6,182,212,0.08));'
                        'border:1px solid rgba(16,185,129,0.45);margin:10px 0 14px;">'
                        '<div style="display:flex;align-items:center;gap:10px;">'
                        '<span style="font-size:1.5rem;">🟢</span>'
                        '<div>'
                        '<div style="font-size:1rem;font-weight:800;color:#34d399;">'
                        'Voice Clone Server — Online'
                        '</div>'
                        '<div style="font-size:0.78rem;color:#94a3b8;margin-top:3px;">'
                        '✅ ချက်ချင်း ရနိုင်ပါသည် — Test လုပ်ပြီး စမ်းနိုင်ပါပြီ'
                        '</div>'
                        '</div>'
                        '</div>'
                        '</div>'
                    )
                    st.markdown(online_html, unsafe_allow_html=True)
                else:
                    offline_html = (
                        '<div style="padding:18px 22px;border-radius:14px;'
                        'background:linear-gradient(135deg,rgba(244,63,94,0.12),rgba(236,72,153,0.06));'
                        'border:1px solid rgba(244,63,94,0.4);margin:10px 0 14px;">'
                        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">'
                        '<span style="font-size:1.5rem;">🔴</span>'
                        '<div>'
                        '<div style="font-size:1rem;font-weight:800;color:#fb7185;">'
                        'Voice Clone Server — Offline'
                        '</div>'
                        '<div style="font-size:0.78rem;color:#94a3b8;margin-top:3px;">'
                        'လောလောဆယ် Voice Clone Service က မဖွင့်ထားသေးပါ'
                        '</div>'
                        '</div>'
                        '</div>'
                        '<div style="padding:12px 16px;border-radius:10px;'
                        'background:rgba(18,22,32,0.5);border-left:3px solid #f43f5e;'
                        'font-size:0.82rem;color:#cbd5e1;line-height:1.9;">'
                        '📞 <b style="color:#fb7185;">Admin ကို ဆက်သွယ်ပါ</b><br>'
                        f'💬 <b>Telegram:</b> {ADMIN_TELEGRAM}<br>'
                        '🕐 <b>Response:</b> ၅–၃၀ မိနစ်အတွင်း'
                        '</div>'
                        '<div style="margin-top:12px;font-size:0.78rem;'
                        'color:#94a3b8;line-height:1.7;">'
                        '⏰ <b style="color:#c4b5fd;">မကြာမီ ပြန်လည် ဖွင့်ပေးပါမည်</b><br>'
                        '🙏 နားလည်ပေးသည့်အတွက် ကျေးဇူးတင်ပါသည်'
                        '</div>'
                        '</div>'
                    )
                    st.markdown(offline_html, unsafe_allow_html=True)

                st.markdown('<div class="adv-section-header">🎵 Reference Audio</div>', unsafe_allow_html=True)
                ref_source = st.radio(
                    "Reference Audio Source",
                    ["Upload New", "From Resource Library"],
                    horizontal=True, key="voice_clone_ref_source_widget",
                )

                if ref_source == "Upload New":
                    uploaded_audio = st.file_uploader(
                        "Upload Reference Audio (3-10 seconds)",
                        type=["wav", "mp3", "flac", "m4a"],
                        key="voice_clone_upload_widget",
                    )
                    if uploaded_audio is not None:
                        st.success(f"Reference audio uploaded: {uploaded_audio.name}")
                        st.session_state["voice_clone_ref_audio"] = uploaded_audio.name
                else:
                    try:
                        from app.utils import utils as _utils
                        ref_dir = _utils.resource_dir("tts_reference_audio")
                    except Exception:
                        ref_dir = ""

                    ref_files = []
                    if ref_dir and os.path.isdir(ref_dir):
                        try:
                            ref_files = sorted([
                                f for f in os.listdir(ref_dir)
                                if f.lower().endswith((".wav", ".mp3", ".flac", ".m4a"))
                            ])
                        except OSError:
                            ref_files = []

                    if ref_files:
                        selected_ref = st.selectbox("Reference Audio File",
                                                     options=ref_files,
                                                     key="voice_clone_ref_file_widget")
                        st.session_state["voice_clone_ref_audio"] = selected_ref
                        try:
                            ref_path = os.path.join(ref_dir, selected_ref)
                            if os.path.exists(ref_path):
                                with open(ref_path, "rb") as af:
                                    st.audio(af.read())
                        except Exception as e:
                            st.caption(f"Preview unavailable: {e}")
                    else:
                        st.info("No reference audio files found. Upload a new one instead.")

                st.markdown('<div class="adv-section-header">🎚 Clone Quality</div>', unsafe_allow_html=True)
                quality_cols = st.columns(3)
                with quality_cols[0]:
                    clone_similarity = st.slider("Similarity", min_value=0.0, max_value=1.0,
                                                  value=float(st.session_state.get("voice_clone_similarity", 0.8)),
                                                  step=0.05, key="voice_clone_similarity_widget")
                with quality_cols[1]:
                    clone_expressiveness = st.slider("Expressiveness", min_value=0.0, max_value=1.0,
                                                      value=float(st.session_state.get("voice_clone_expressiveness", 0.6)),
                                                      step=0.05, key="voice_clone_expressiveness_widget")
                with quality_cols[2]:
                    clone_denoise = st.slider("Denoise", min_value=0, max_value=100,
                                               value=int(st.session_state.get("voice_clone_denoise", 50)),
                                               step=5, key="voice_clone_denoise_widget")

                st.markdown('<div class="adv-section-header">🔊 Test Clone</div>', unsafe_allow_html=True)
                test_text = st.text_area(
                    "Test text",
                    value=st.session_state.get("voice_clone_test_text",
                                               "မင်္ဂလာပါ။ ဒါက PSAI ရဲ့ cloned voice preview ဖြစ်ပါတယ်။"),
                    height=80, key="voice_clone_test_text_widget",
                    label_visibility="collapsed",
                )
                st.session_state["voice_clone_test_text"] = test_text

                if not engine_running:
                    st.button("🎤 Test Clone (Offline)",
                              key="voice_clone_test_btn",
                              use_container_width=True,
                              disabled=True,
                              help="Server Offline — Admin ကို ဆက်သွယ်ပါ")
                else:
                    if st.button("🎤 Test Clone", key="voice_clone_test_btn", use_container_width=True):
                        if not test_text or not test_text.strip():
                            st.warning("⚠️ Please enter test text first.")
                        else:
                            ref_audio = st.session_state.get("voice_clone_ref_audio", "")
                            with st.spinner(f"🎤 Cloning with {engine_name}..."):
                                try:
                                    audio_path, error = _voice_clone.synthesize(
                                        engine_id=selected_engine,
                                        text=test_text,
                                        reference_audio=ref_audio,
                                        similarity=clone_similarity,
                                        expressiveness=clone_expressiveness,
                                        denoise=clone_denoise,
                                    )
                                    if audio_path and os.path.exists(audio_path):
                                        st.success("✅ Clone preview ready!")
                                        with open(audio_path, "rb") as af:
                                            st.audio(af.read(), format="audio/wav")
                                    else:
                                        st.error(f"❌ Clone failed: {error}")
                                except Exception as e:
                                    st.error(f"❌ Clone error: {e}")

                st.markdown('<div class="adv-section-header">📚 Clone Library</div>', unsafe_allow_html=True)
                cloned_voices = st.session_state.get("voice_clone_library", [])
                if cloned_voices:
                    for cv in cloned_voices:
                        st.caption(f"🎤 {cv}")
                else:
                    st.caption("No cloned voices saved yet.")


# ============================================================================
# 🎬 SCENE DETECTION PANEL
# ============================================================================
def render_scene_detection_panel(tr):
    _inject_css()
    with st.container(border=True):
        st.markdown('<div class="adv-panel-title">🎬 Scene Detection '
                    '<span class="adv-badge adv-badge-beta">BETA</span></div>'
                    '<div class="adv-panel-subtitle">Auto-detect scenes and generate highlight clips.</div>',
                    unsafe_allow_html=True)
        scene_enable = st.toggle("Enable Scene Detection",
                                  value=bool(st.session_state.get("scene_detection_enabled", False)),
                                  key="scene_detection_enable_widget")
        st.session_state["scene_detection_enabled"] = scene_enable
        if not scene_enable:
            return

        st.markdown('<div class="adv-section-header">🎯 Detection Mode</div>', unsafe_allow_html=True)
        st.selectbox("Mode",
                     ["Auto Highlight", "Action Scenes", "Emotional Scenes", "Dialogue Scenes", "All Scenes"],
                     key="scene_detection_mode_widget")

        st.markdown('<div class="adv-section-header">🎚 Sensitivity</div>', unsafe_allow_html=True)
        st.slider("Sensitivity", min_value=1, max_value=10,
                  value=int(st.session_state.get("scene_sensitivity", 5)),
                  key="scene_sensitivity_widget")

        st.markdown('<div class="adv-section-header">⏱ Clip Duration</div>', unsafe_allow_html=True)
        duration_cols = st.columns(2)
        with duration_cols[0]:
            st.number_input("Min (sec)", min_value=1, max_value=60,
                            value=int(st.session_state.get("scene_min_duration", 3)),
                            key="scene_min_duration_widget")
        with duration_cols[1]:
            st.number_input("Max (sec)", min_value=5, max_value=300,
                            value=int(st.session_state.get("scene_max_duration", 15)),
                            key="scene_max_duration_widget")

        st.markdown('<div class="adv-section-header">⭐ Auto Highlights</div>', unsafe_allow_html=True)
        highlight_count = st.slider("Max Highlights", min_value=1, max_value=20,
                                     value=int(st.session_state.get("scene_highlight_count", 5)),
                                     key="scene_highlight_count_widget")
        st.session_state["scene_highlight_count"] = highlight_count

        try:
            from app.services import scene_detection as _sd
            sd_available = _sd.is_available()
        except Exception as e:
            sd_available = False
            st.caption(f"⚠️ Scene Detection service unavailable: {e}")

        if not sd_available:
            st.warning("⚠️ PySceneDetect not installed. Run: `pip install scenedetect[opencv]`")
            return

        st.markdown('<div class="adv-section-header">🚀 Detect</div>', unsafe_allow_html=True)
        video_path = _resolve_preview_video_path()
        if not video_path:
            st.caption("📁 Upload a video first to detect scenes.")

        detect_col, clear_col = st.columns([3, 1])
        with detect_col:
            if st.button("🎬 Detect Scenes", key="scene_detect_btn",
                         use_container_width=True, disabled=not video_path):
                with st.spinner("Detecting scenes..."):
                    try:
                        mode = st.session_state.get("scene_detection_mode_widget", "Auto Highlight")
                        sens = int(st.session_state.get("scene_sensitivity_widget", 5))
                        min_d = float(st.session_state.get("scene_min_duration_widget", 3))
                        max_d = float(st.session_state.get("scene_max_duration_widget", 15))
                        max_h = int(st.session_state.get("scene_highlight_count_widget", 5))
                        scenes = _sd.get_highlight_scenes(
                            video_path=video_path, mode=mode, sensitivity=sens,
                            min_duration=min_d, max_duration=max_d, max_highlights=max_h,
                        )
                        if scenes:
                            st.session_state["scene_detect_result"] = scenes
                            st.success(f"✅ {len(scenes)} scene(s) detected")
                        else:
                            st.warning("⚠️ No scenes detected. Try higher sensitivity.")
                    except Exception as e:
                        st.error(f"❌ Detection failed: {e}")

        with clear_col:
            if st.button("🗑", key="scene_clear_btn", use_container_width=True):
                st.session_state["scene_detect_result"] = []
                st.rerun()

        scenes_result = st.session_state.get("scene_detect_result", [])
        if scenes_result:
            st.markdown(
                f'<div class="adv-info">🎬 <b>{len(scenes_result)} scenes</b> detected · '
                f'📐 Total: {sum(s.get("duration", 0) for s in scenes_result):.1f}s</div>',
                unsafe_allow_html=True,
            )
            for idx, sc in enumerate(scenes_result, start=1):
                st.markdown(
                    f'<div style="padding:6px 10px;margin:3px 0;border-radius:6px;'
                    f'background:rgba(139,92,246,0.06);border-left:3px solid #8b5cf6;'
                    f'font-size:0.8rem;color:#e2e8f0;display:flex;justify-content:space-between;">'
                    f'<span><b>#{idx}</b> · {sc["start"]:.2f}s → {sc["end"]:.2f}s</span>'
                    f'<span style="color:#8b5cf6;font-weight:700;">'
                    f'{sc.get("duration", 0):.2f}s · ★ {sc.get("score", 0):.1f}</span></div>',
                    unsafe_allow_html=True,
                )


# ============================================================================
# 📚 VIDEO LIBRARY PANEL
# ============================================================================
def render_video_library_panel(tr):
    _inject_css()
    with st.container(border=True):
        st.markdown('<div class="adv-panel-title">📚 Video Library</div>'
                    '<div class="adv-panel-subtitle">Browse previous video generations.</div>',
                    unsafe_allow_html=True)
        try:
            from app.utils import utils as _utils
            tasks_dir = os.path.join(_utils.storage_dir(), "tasks")
        except Exception:
            tasks_dir = ""

        if not tasks_dir or not os.path.isdir(tasks_dir):
            st.info("No video library found yet.")
            return

        try:
            task_folders = sorted(
                [d for d in os.listdir(tasks_dir) if os.path.isdir(os.path.join(tasks_dir, d))],
                reverse=True,
            )[:20]
        except OSError:
            task_folders = []

        if not task_folders:
            st.info("No video library found yet.")
            return

        st.caption(f"Found {len(task_folders)} previous tasks")
        for task_id in task_folders:
            task_path = os.path.join(tasks_dir, task_id)
            with st.expander(f"📁 {task_id}", expanded=False):
                try:
                    files = os.listdir(task_path)
                except OSError:
                    st.caption("Unable to read task folder.")
                    continue
                video_files = [f for f in files if f.lower().endswith((".mp4", ".mov", ".mkv"))]
                if video_files:
                    for vf in video_files[:3]:
                        st.caption(f"🎬 {vf}")
                else:
                    st.caption("No output video yet.")


# ============================================================================
# 📤 EXPORT PRESETS PANEL — 🎯 PENDING VALUE PATTERN
# ============================================================================
def render_export_presets_panel(tr):
    _inject_css()
    with st.container(border=True):
        st.markdown('<div class="adv-panel-title">📤 Export Presets</div>'
                    '<div class="adv-panel-subtitle">Optimized presets for each platform.</div>',
                    unsafe_allow_html=True)
        presets = {
            "TikTok": {"ratio": "9:16", "quality": "1080p", "bitrate": "high", "icon": "🎵"},
            "YouTube": {"ratio": "16:9", "quality": "1080p", "bitrate": "high", "icon": "▶️"},
            "YouTube Shorts": {"ratio": "9:16", "quality": "1080p", "bitrate": "high", "icon": "📱"},
            "Instagram Reels": {"ratio": "9:16", "quality": "1080p", "bitrate": "medium", "icon": "📸"},
            "Instagram Post": {"ratio": "1:1", "quality": "1080p", "bitrate": "medium", "icon": "🖼"},
            "Facebook": {"ratio": "16:9", "quality": "1080p", "bitrate": "medium", "icon": "📘"},
            "Twitter/X": {"ratio": "16:9", "quality": "720p", "bitrate": "medium", "icon": "🐦"},
            "Custom": {"ratio": "Auto", "quality": "1080p", "bitrate": "high", "icon": "⚙️"},
        }
        selected_preset = st.session_state.get("export_preset", "YouTube Shorts")
        preset_names = list(presets.keys())
        cols_per_row = 4
        for i in range(0, len(preset_names), cols_per_row):
            row_cols = st.columns(cols_per_row)
            for j, name in enumerate(preset_names[i:i + cols_per_row]):
                with row_cols[j]:
                    icon = presets[name]["icon"]
                    is_active = "active" if selected_preset == name else ""
                    st.markdown(f'<div class="adv-style-card {is_active}">'
                                f'<span class="adv-style-icon">{icon}</span>{name}</div>',
                                unsafe_allow_html=True)
                    if st.button("Select", key=f"export_preset_{name}", use_container_width=True):
                        st.session_state["export_preset"] = name
                        preset_ratio = presets[name].get("ratio", "Auto")
                        if preset_ratio and preset_ratio != "Auto":
                            # 🎯 Pending Value — Widget မတိုင်ခင် — Apply ဖြစ်မယ်
                            st.session_state["_pending_adjust_aspect"] = preset_ratio
                        st.rerun()
        if selected_preset in presets:
            preset = presets[selected_preset]
            st.markdown(f'<div class="adv-info">📐 Ratio: {preset["ratio"]} · '
                        f'🎥 Quality: {preset["quality"]} · 📊 Bitrate: {preset["bitrate"]}</div>',
                        unsafe_allow_html=True)


# ============================================================================
# 📦 PARAM COLLECTION
# ============================================================================
def get_advanced_params():
    return {
        "ai_thumbnail_enabled": st.session_state.get("ai_thumbnail_enabled", False),
        "ai_thumb_style": st.session_state.get("ai_thumb_style_widget", "Cinematic"),
        "ai_thumb_ratio": st.session_state.get("ai_thumb_ratio_widget", "16:9"),
        "ai_thumb_count": st.session_state.get("ai_thumb_count_widget", 3),
        "ai_title_enabled": st.session_state.get("ai_title_enabled", False),
        "ai_title_hint": st.session_state.get("ai_title_hint", ""),
        "ai_title_count": st.session_state.get("ai_title_count", 5),
        "ai_title_result": st.session_state.get("ai_title_result", []),
        "ai_auto_subtitle": st.session_state.get("ai_auto_subtitle", False),
        "ai_auto_sub_lang": st.session_state.get("ai_auto_sub_lang_widget", "Burmese"),
        "ai_auto_sub_pos": st.session_state.get("ai_auto_sub_pos_widget", "Bottom"),
        "ai_auto_cut": st.session_state.get("ai_auto_cut", False),
        "ai_auto_cut_duration": st.session_state.get("ai_auto_cut_duration_widget", 3),
        "ai_tags_enabled": st.session_state.get("ai_tags_enabled", False),
        "ai_tags_result": st.session_state.get("ai_tags_result", []),
        "watermark_enabled": st.session_state.get("watermark_enabled", False),
        "watermark_text": st.session_state.get("watermark_text_widget", "@PSAI"),
        "watermark_font": st.session_state.get("watermark_font_widget", "Inter (Modern)"),
        "watermark_style": st.session_state.get("watermark_style_widget", "Shadow"),
        "watermark_color": st.session_state.get("watermark_color_widget", "#FFFFFF"),
        "watermark_shadow_color": st.session_state.get("watermark_shadow_color_widget", "#000000"),
        "watermark_animation": st.session_state.get("watermark_animation_widget", "📍 Static"),
        "watermark_speed": st.session_state.get("watermark_speed_widget", 2.0),
        "watermark_size": st.session_state.get("watermark_size_widget", 40),
        "watermark_opacity": st.session_state.get("watermark_opacity_widget", 70),
        "watermark_x": st.session_state.get("watermark_x_widget", 10),
        "watermark_y": st.session_state.get("watermark_y_widget", 10),
        "logo_enabled": st.session_state.get("logo_enabled", False),
        "logo_path": st.session_state.get("logo_upload_widget", None),
        "logo_effect": st.session_state.get("logo_effect_widget", "None"),
        "logo_filter": st.session_state.get("logo_filter_widget", "Normal"),
        "logo_size": st.session_state.get("logo_size_widget", 80),
        "logo_opacity": st.session_state.get("logo_opacity_widget", 80),
        "logo_rotation": st.session_state.get("logo_rotation_widget", 0),
        "logo_x": st.session_state.get("logo_x_widget", 80),
        "logo_y": st.session_state.get("logo_y_widget", 5),
        "blur_boxes_enabled": st.session_state.get("blur_boxes_enabled", False),
        "blur_boxes_count": st.session_state.get("blur_boxes_count_widget", 3),
        "blur_boxes": _collect_blur_boxes(),
        "cinematic_style": st.session_state.get("cinematic_style", "None"),
        "adjust_zoom": st.session_state.get("adjust_zoom_widget", 1.0),
        "adjust_video_speed": st.session_state.get("adjust_video_speed_widget", 1.0),
        "adjust_voice_speed": st.session_state.get("adjust_voice_speed_widget", 1.0),
        "adjust_aspect": st.session_state.get("adjust_aspect_widget", "Auto"),
        "adjust_auto_blur_bg": st.session_state.get("adjust_auto_blur_bg", False),
        "export_preset": st.session_state.get("export_preset", ""),
        "voice_clone_enabled": st.session_state.get("voice_clone_enabled", False),
        "voice_clone_engine": st.session_state.get("voice_clone_engine", "indextts"),
        "voice_clone_ref_audio": st.session_state.get("voice_clone_ref_audio", ""),
        "voice_clone_similarity": st.session_state.get("voice_clone_similarity_widget", 0.8),
        "voice_clone_expressiveness": st.session_state.get("voice_clone_expressiveness_widget", 0.6),
        "voice_clone_denoise": st.session_state.get("voice_clone_denoise_widget", 50),
        "scene_detection_enabled": st.session_state.get("scene_detection_enabled", False),
        "scene_detection_mode": st.session_state.get("scene_detection_mode_widget", "Auto Highlight"),
        "scene_sensitivity": st.session_state.get("scene_sensitivity_widget", 5),
        "scene_min_duration": st.session_state.get("scene_min_duration_widget", 3),
        "scene_max_duration": st.session_state.get("scene_max_duration_widget", 15),
        "scene_highlight_count": st.session_state.get("scene_highlight_count_widget", 5),
        "scene_detect_result": st.session_state.get("scene_detect_result", []),
    }


def _collect_blur_boxes():
    boxes = []
    count = st.session_state.get("blur_boxes_count_widget", 3)
    for i in range(1, count + 1):
        boxes.append({
            "x": st.session_state.get(f"blur_box_{i}_x", 10),
            "y": st.session_state.get(f"blur_box_{i}_y", 10),
            "width": st.session_state.get(f"blur_box_{i}_width", 30),
            "height": st.session_state.get(f"blur_box_{i}_height", 20),
            "radius": st.session_state.get(f"blur_box_{i}_radius", 15),
        })
    return boxes


# ============================================================================
# 📦 MASTER RENDER
# ============================================================================
def render_advanced_features(tr):
    st.markdown(
        '<div class="adv-hero">'
        '<div class="adv-hero-title">🚀 Advanced Studio</div>'
        '<div class="adv-hero-sub">Professional-grade tools for Movie Recap production.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    row1_cols = st.columns([1, 1])
    with row1_cols[0]:
        render_cinematic_panel(tr)
    with row1_cols[1]:
        render_adjustments_panel(tr)

    row2_cols = st.columns([1, 1])
    with row2_cols[0]:
        render_ai_features_panel(tr)
    with row2_cols[1]:
        render_watermark_panel(tr)

    row3_cols = st.columns([1, 1])
    with row3_cols[0]:
        render_logo_panel(tr)
    with row3_cols[1]:
        render_blur_boxes_panel(tr)

    row4_cols = st.columns([1, 1])
    with row4_cols[0]:
        render_voice_studio_panel(tr)
    with row4_cols[1]:
        render_scene_detection_panel(tr)

    row5_cols = st.columns([1, 1])
    with row5_cols[0]:
        render_video_library_panel(tr)
    with row5_cols[1]:
        render_export_presets_panel(tr)