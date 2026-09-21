import streamlit as st
import os
from app.config import config
from app.utils import utils


# ============================================================================
# 🛡 ANTI-VIRUS MODE PANEL
# ============================================================================

# Widget keys with their default (neutral) values
_AV_WIDGET_DEFAULTS = {
    "antivirus_auto_sync_widget": False,
    "antivirus_segment_sync_widget": False,
    "antivirus_auto_music_widget": False,
    "antivirus_music_mood_widget": "Auto Detect",
    "antivirus_bgm_file_widget": "",
    "antivirus_bgm_volume_widget": 30,
    "antivirus_mute_original_widget": False,
    "antivirus_noise_reduction_widget": False,
    "antivirus_fade_duration_widget": 2.0,
    "antivirus_auto_clips_widget": False,
    "antivirus_clip_duration_widget": 3,
    "antivirus_clip_speed_var_widget": 0.05,
    "antivirus_mirror_mode_widget": False,
    "antivirus_micro_rotation_widget": 0.0,
    "antivirus_film_grain_widget": 0,
    "antivirus_vignette_widget": False,
    "antivirus_auto_loop_widget": False,
    "antivirus_pitch_shift_widget": 0,
}

# AUTO mode forces these values
_AV_AUTO_VALUES = {
    "antivirus_auto_sync_widget": True,
    "antivirus_segment_sync_widget": True,
    "antivirus_auto_music_widget": True,
    "antivirus_music_mood_widget": "Auto Detect",
    "antivirus_bgm_file_widget": "",
    "antivirus_bgm_volume_widget": 30,
    "antivirus_mute_original_widget": False,
    "antivirus_noise_reduction_widget": True,
    "antivirus_fade_duration_widget": 2.0,
    "antivirus_auto_clips_widget": True,
    "antivirus_clip_duration_widget": 3,
    "antivirus_clip_speed_var_widget": 0.05,
    "antivirus_mirror_mode_widget": True,
    "antivirus_micro_rotation_widget": 0.5,
    "antivirus_film_grain_widget": 8,
    "antivirus_vignette_widget": True,
    "antivirus_auto_loop_widget": False,
    "antivirus_pitch_shift_widget": 1,
}


def _init_av_widget_keys():
    """Initialize all Anti-Virus widget keys with neutral defaults."""
    for key, default_value in _AV_WIDGET_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def _apply_av_auto_values():
    """Force all Anti-Virus widget values to AUTO mode settings."""
    for key, value in _AV_AUTO_VALUES.items():
        st.session_state[key] = value


def _apply_av_neutral_values():
    """Restore all Anti-Virus widget values to neutral defaults."""
    for key, value in _AV_WIDGET_DEFAULTS.items():
        st.session_state[key] = value


def _list_bgm_files():
    """Return list of BGM files available in the resource folder."""
    try:
        bgm_dir = utils.resource_dir("songs")
    except Exception:
        bgm_dir = ""

    if not bgm_dir or not os.path.isdir(bgm_dir):
        return []

    try:
        files = sorted([
            f for f in os.listdir(bgm_dir)
            if f.lower().endswith((".mp3", ".wav", ".m4a", ".aac", ".flac"))
        ])
        return files
    except OSError:
        return []


def render_antivirus_panel(tr):
    """Render the Anti-Virus Mode panel as a compact top-right panel."""
    _init_av_widget_keys()

    auto_key = "antivirus_auto_mode_widget"
    if auto_key not in st.session_state:
        st.session_state[auto_key] = False

    current_auto = bool(st.session_state.get(auto_key, False))
    prev_auto = st.session_state.get("_av_prev_auto_state", None)

    if prev_auto is None:
        st.session_state["_av_prev_auto_state"] = current_auto
    elif current_auto != prev_auto:
        if current_auto:
            _apply_av_auto_values()
        else:
            _apply_av_neutral_values()
        st.session_state["_av_prev_auto_state"] = current_auto

    with st.container(border=True):

        # --- Header Row ---
        head_left, head_right = st.columns([2, 1])

        with head_left:
            st.markdown(
                '<div style="font-size:1.0rem;font-weight:700;color:#f0f2f7;'
                'padding-top:6px;">🛡 Anti-Virus</div>',
                unsafe_allow_html=True,
            )

        with head_right:
            auto_mode = st.toggle(
                "ON",
                key=auto_key,
                help="ON = Auto mode (settings hidden). OFF = Manual config.",
            )

        # ====================================================================
        # AUTO ON → Hide all settings
        # ====================================================================
        if auto_mode:
            st.success("✅ Auto mode running")
            st.caption("Turn **OFF** to adjust settings manually.")

            st.markdown(
                """
                <div style="font-size:0.78rem;color:#a8b0c4;line-height:1.9;
                            background:rgba(124,92,255,0.08);padding:10px 12px;
                            border-radius:8px;border-left:3px solid #7c5cff;">
                    <b style="color:#e0e4ee;">Applied transforms:</b><br>
                    🪞 Mirror &nbsp;·&nbsp; 🎬 Rotation 0.5°<br>
                    🎞 Grain 8 &nbsp;·&nbsp; 🌑 Vignette<br>
                    🎼 Pitch +1 &nbsp;·&nbsp; ✂️ Auto Clips 3s<br>
                    🔊 Noise Reduction &nbsp;·&nbsp; 🎵 Auto Music
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

        # ====================================================================
        # AUTO OFF → Show all settings
        # ====================================================================
        st.caption("Manual mode · Turn **ON** for auto")

        # --- Sync Section ---
        st.markdown("**⚡️ Sync**")
        sync_cols = st.columns(2)

        with sync_cols[0]:
            st.toggle("Auto Sync", key="antivirus_auto_sync_widget")

        with sync_cols[1]:
            st.toggle("Segment Sync", key="antivirus_segment_sync_widget")

        # --- Background Music ---
        st.markdown("**🎵 Background Music**")

        st.toggle("Auto Music", key="antivirus_auto_music_widget")

        mood_options = [
            "Auto Detect", "Dramatic", "Horror", "Sad", "Action",
            "Romantic", "Comedy", "Mystery", "Epic", "Thriller",
        ]
        st.selectbox(
            "Music Mood",
            options=mood_options,
            key="antivirus_music_mood_widget",
        )

        # --- BGM File Picker ---
        bgm_files = _list_bgm_files()
        if bgm_files:
            bgm_options = ["— None —"] + bgm_files
            current_bgm = st.session_state.get("antivirus_bgm_file_widget", "")
            if current_bgm not in bgm_options:
                current_bgm = "— None —"
                st.session_state["antivirus_bgm_file_widget"] = ""

            selected_bgm = st.selectbox(
                "BGM File",
                options=bgm_options,
                index=bgm_options.index(current_bgm) if current_bgm in bgm_options else 0,
                key="antivirus_bgm_file_select_widget",
                help="Select a BGM file from resource/songs folder.",
            )
            st.session_state["antivirus_bgm_file_widget"] = (
                "" if selected_bgm == "— None —" else selected_bgm
            )
        else:
            st.caption("📁 No BGM files found in `resource/songs/` folder.")

        st.slider(
            "Volume",
            min_value=0, max_value=100, step=5,
            key="antivirus_bgm_volume_widget",
        )

        opt_cols = st.columns(2)
        with opt_cols[0]:
            st.toggle("Mute Original", key="antivirus_mute_original_widget")
        with opt_cols[1]:
            st.toggle("Noise Reduction", key="antivirus_noise_reduction_widget")

        st.slider(
            "Fade In/Out (s)",
            min_value=0.0, max_value=5.0, step=0.5,
            key="antivirus_fade_duration_widget",
        )

        # --- Auto Clips ---
        st.markdown("**✂️ Auto Clips**")

        auto_clips = st.toggle(
            "Enable Auto Clips",
            key="antivirus_auto_clips_widget",
            help="Automatically split video into short clips with slight speed changes.",
        )

        if auto_clips:
            clip_cols = st.columns(2)
            with clip_cols[0]:
                st.slider(
                    "Clip Duration (s)",
                    min_value=1, max_value=30, step=1,
                    key="antivirus_clip_duration_widget",
                )
            with clip_cols[1]:
                st.slider(
                    "Speed Var",
                    min_value=0.0, max_value=0.2, step=0.01,
                    format="%.2f",
                    key="antivirus_clip_speed_var_widget",
                )

        # --- Visual Effects ---
        st.markdown("**🎞 Visual Effects**")

        st.toggle(
            "🪞 Mirror Mode",
            key="antivirus_mirror_mode_widget",
            help="Flip horizontally to break frame matching.",
        )

        st.slider(
            "🎬 Micro Rotation (°)",
            min_value=0.0, max_value=3.0, step=0.1,
            key="antivirus_micro_rotation_widget",
        )

        st.slider(
            "🎞 Film Grain",
            min_value=0, max_value=30, step=1,
            key="antivirus_film_grain_widget",
        )

        st.toggle("🌑 Vignette", key="antivirus_vignette_widget")
        st.toggle("🔁 Auto Loop", key="antivirus_auto_loop_widget")

        # --- Audio Transforms ---
        st.markdown("**🎵 Audio Transforms**")

        st.slider(
            "🎼 Pitch Shift (semitones)",
            min_value=-6, max_value=6, step=1,
            key="antivirus_pitch_shift_widget",
        )

        # --- Summary ---
        st.markdown("---")

        mirror_val = bool(st.session_state.get("antivirus_mirror_mode_widget", False))
        rotation_val = float(st.session_state.get("antivirus_micro_rotation_widget", 0.0))
        grain_val = int(st.session_state.get("antivirus_film_grain_widget", 0))
        vignette_val = bool(st.session_state.get("antivirus_vignette_widget", False))
        loop_val = bool(st.session_state.get("antivirus_auto_loop_widget", False))
        pitch_val = int(st.session_state.get("antivirus_pitch_shift_widget", 0))
        clips_val = bool(st.session_state.get("antivirus_auto_clips_widget", False))
        noise_val = bool(st.session_state.get("antivirus_noise_reduction_widget", False))
        mute_val = bool(st.session_state.get("antivirus_mute_original_widget", False))
        music_val = bool(st.session_state.get("antivirus_auto_music_widget", False))
        bgm_val = st.session_state.get("antivirus_bgm_file_widget", "")

        active_count = sum([
            mirror_val,
            rotation_val > 0.01,
            grain_val > 0,
            vignette_val,
            loop_val,
            pitch_val != 0,
            clips_val,
            noise_val,
            mute_val,
            music_val or bool(bgm_val),
        ])

        if active_count == 0:
            st.caption("ℹ️ No transformative effects enabled.")
        else:
            st.caption(f"✅ {active_count} effect(s) will be applied.")


def get_antivirus_params():
    """Collect Anti-Virus Mode settings for video generation."""
    auto_mode = bool(st.session_state.get("antivirus_auto_mode_widget", False))

    if auto_mode:
        return {
            "antivirus_auto_mode": True,
            "antivirus_auto_sync": True,
            "antivirus_segment_sync": True,
            "antivirus_auto_music": True,
            "antivirus_music_mood": "Auto Detect",
            "antivirus_bgm_file": "",
            "antivirus_bgm_volume": 30,
            "antivirus_mute_original": False,
            "antivirus_noise_reduction": True,
            "antivirus_fade_duration": 2.0,
            "antivirus_auto_clips": True,
            "antivirus_clip_duration": 3,
            "antivirus_clip_speed_var": 0.05,
            "antivirus_mirror_mode": True,
            "antivirus_micro_rotation": 0.5,
            "antivirus_film_grain": 8,
            "antivirus_vignette": True,
            "antivirus_auto_loop": False,
            "antivirus_pitch_shift": 1,
        }

    return {
        "antivirus_auto_mode": False,
        "antivirus_auto_sync": bool(st.session_state.get("antivirus_auto_sync_widget", False)),
        "antivirus_segment_sync": bool(st.session_state.get("antivirus_segment_sync_widget", False)),
        "antivirus_auto_music": bool(st.session_state.get("antivirus_auto_music_widget", False)),
        "antivirus_music_mood": st.session_state.get("antivirus_music_mood_widget", "Auto Detect"),
        "antivirus_bgm_file": st.session_state.get("antivirus_bgm_file_widget", ""),
        "antivirus_bgm_volume": int(st.session_state.get("antivirus_bgm_volume_widget", 30)),
        "antivirus_mute_original": bool(st.session_state.get("antivirus_mute_original_widget", False)),
        "antivirus_noise_reduction": bool(st.session_state.get("antivirus_noise_reduction_widget", False)),
        "antivirus_fade_duration": float(st.session_state.get("antivirus_fade_duration_widget", 2.0)),
        "antivirus_auto_clips": bool(st.session_state.get("antivirus_auto_clips_widget", False)),
        "antivirus_clip_duration": int(st.session_state.get("antivirus_clip_duration_widget", 3)),
        "antivirus_clip_speed_var": float(st.session_state.get("antivirus_clip_speed_var_widget", 0.05)),
        "antivirus_mirror_mode": bool(st.session_state.get("antivirus_mirror_mode_widget", False)),
        "antivirus_micro_rotation": float(st.session_state.get("antivirus_micro_rotation_widget", 0.0)),
        "antivirus_film_grain": int(st.session_state.get("antivirus_film_grain_widget", 0)),
        "antivirus_vignette": bool(st.session_state.get("antivirus_vignette_widget", False)),
        "antivirus_auto_loop": bool(st.session_state.get("antivirus_auto_loop_widget", False)),
        "antivirus_pitch_shift": int(st.session_state.get("antivirus_pitch_shift_widget", 0)),
    }