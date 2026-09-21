#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
PS AI Recap — Coin Panel
Balance + Dynamic Cost Calculator + History + Antivirus Pricing
"""

import streamlit as st
from app.services import coin_system as cs

# ============================================================================
# 🎯 DYNAMIC COST — Enable လုပ်ထားတဲ့ Feature တွေပဲ တွက်
# ============================================================================
def calculate_video_cost(video_minutes: float) -> dict:
    """Video အရှည် + Enabled Features ပေါ် မူတည်ပြီး Coin Cost တွက်"""
    m = max(0.5, float(video_minutes or 1))
    cost = {}

    # --- Always: Video Generation ---
    cost["video_generate"] = round(1.5 * m)

    # --- Always: TTS Voice ---
    cost["tts"] = round(0.5 * m)

    # --- Conditional: Subtitle Transcribe ---
    if st.session_state.get("subtitle_enabled", True):
        cost["transcribe"] = round(0.8 * m)

    # --- Conditional: Voice Clone (Premium only) ---
    if st.session_state.get("voice_clone_enabled", False):
        try:
            user_id = st.session_state.get("user_id")
            if user_id and cs.is_monthly_active(user_id):
                cost["voice_clone"] = round(0.5 * m)
        except Exception:
            pass

    # --- Conditional: AI Thumbnail ---
    if st.session_state.get("ai_thumbnail_enabled", False):
        cost["ai_thumbnail"] = 2

    # --- Conditional: AI Title ---
    if st.session_state.get("ai_title_enabled", False):
        cost["ai_title"] = 1

    # --- Conditional: AI Tags ---
    if st.session_state.get("ai_tags_enabled", False):
        cost["ai_tags"] = 1

    # --- Conditional: Auto Subtitle ---
    if st.session_state.get("ai_auto_subtitle", False):
        cost["ai_subtitle"] = 2

    # --- Conditional: Auto Cut ---
    if st.session_state.get("ai_auto_cut", False):
        cost["ai_cut"] = 2

    # --- Conditional: Scene Detection ---
    if st.session_state.get("scene_detection_enabled", False):
        cost["scene_detect"] = 2

    # ========================================================================
    # 🛡 ANTI-VIRUS MODE — Professional Pricing
    # ========================================================================
    _av_auto = bool(st.session_state.get("antivirus_auto_mode_widget", False))

    if _av_auto:
        # Auto Mode = 5 + (0.5 × minutes) — Cap 15
        av_cost = 5 + round(0.5 * m)
        cost["antivirus"] = min(15, av_cost)
    else:
        # Manual Mode — 3-Tier Pricing
        av_cost = 0

        # --- Tier 1 (HIGH IMPACT — 3 Coin each) ---
        if st.session_state.get("antivirus_auto_music_widget", False):
            av_cost += 3
        if st.session_state.get("antivirus_auto_clips_widget", False):
            av_cost += 3
        if st.session_state.get("antivirus_noise_reduction_widget", False):
            av_cost += 3

        # --- Tier 2 (MEDIUM IMPACT — 2 Coin each) ---
        if st.session_state.get("antivirus_auto_sync_widget", False):
            av_cost += 2
        if int(st.session_state.get("antivirus_pitch_shift_widget", 0)) != 0:
            av_cost += 2
        if st.session_state.get("antivirus_mute_original_widget", False):
            av_cost += 2
        if st.session_state.get("antivirus_mirror_mode_widget", False):
            av_cost += 2

        # --- Tier 3 (LOW IMPACT — 1 Coin each) ---
        if st.session_state.get("antivirus_segment_sync_widget", False):
            av_cost += 1
        if float(st.session_state.get("antivirus_micro_rotation_widget", 0.0)) > 0.01:
            av_cost += 1
        if int(st.session_state.get("antivirus_film_grain_widget", 0)) > 0:
            av_cost += 1
        if st.session_state.get("antivirus_vignette_widget", False):
            av_cost += 1
        if st.session_state.get("antivirus_auto_loop_widget", False):
            av_cost += 1

        if av_cost > 0:
            cost["antivirus"] = av_cost

    # --- Total ---
    cost["total"] = sum(v for k, v in cost.items() if k != "total")
    return cost

def get_voice_clone_rate(user_tier: str) -> int:
    """Voice Clone — Tier အလိုက် Coin/မိနစ်"""
    rates = {
        "free": 0,
        "starter": 7,
        "pro": 6,
        "business": 5,
        "enterprise": 5,
    }
    return rates.get(user_tier or "free", 0)

# ============================================================================
# LABELS
# ============================================================================
COST_LABELS = {
    "video_generate": "🎬 Video Generate",
    "tts": "🎙 TTS Voice",
    "transcribe": "📝 Subtitle Transcribe",
    "voice_clone": "🎤 Voice Clone",
    "ai_thumbnail": "🖼 AI Thumbnail",
    "ai_title": "📝 AI Title",
    "ai_tags": "🏷 AI Tags",
    "ai_subtitle": "💬 Auto Subtitle",
    "ai_cut": "✂️ Auto Cut",
    "scene_detect": "🎬 Scene Detection",
    "antivirus": "🛡 Anti-Virus Mode",
}

# ============================================================================
# BALANCE DISPLAY
# ============================================================================
def render_balance_card():
    """Coin Balance Card — အပေါ်မှာ ပြ"""
    user_id = st.session_state.get("user_id")
    user_code = st.session_state.get("user_code", "")
    tier = st.session_state.get("user_tier", "free")

    balance = 0
    if user_id:
        try:
            balance = cs.get_coin_balance(user_id)
            st.session_state["coin_balance"] = balance
        except Exception:
            balance = st.session_state.get("coin_balance", 0)

    tier_labels = {
        "free": "🆓 Free",
        "starter": "🥇 Starter",
        "pro": "🥈 Pro",
        "business": "🏆 Business",
        "enterprise": "👑 Enterprise",
    }
    tier_label = tier_labels.get(tier, "🆓 Free")

    st.markdown(
        f"""
        <div style="
            display:flex;justify-content:space-between;align-items:center;
            padding:16px 20px;border-radius:14px;
            background:linear-gradient(135deg,rgba(139,92,246,0.18),rgba(6,182,212,0.08));
            border:1px solid rgba(139,92,246,0.3);margin-bottom:16px;">
            <div>
                <div style="font-size:0.72rem;color:#94a3b8;
                            text-transform:uppercase;letter-spacing:1px;
                            margin-bottom:2px;">{user_code}</div>
                <div style="font-size:0.95rem;font-weight:700;color:#e2e8f0;">
                    {tier_label}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.7rem;color:#94a3b8;
                            text-transform:uppercase;letter-spacing:1px;">
                    Balance
                </div>
                <div style="font-size:1.8rem;font-weight:900;
                            background:linear-gradient(135deg,#c4b5fd,#8b5cf6);
                            -webkit-background-clip:text;
                            -webkit-text-fill-color:transparent;
                            background-clip:text;line-height:1.1;">
                    {balance} 💰
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return balance

# ============================================================================
# COIN CALCULATOR
# ============================================================================
def render_coin_calculator():
    """Coin Calculator — Video Length ရွေးပြီး Cost ကြိုကြည့်"""
    with st.container(border=True):
        st.markdown(
            '<div style="font-size:1rem;font-weight:700;color:#f0f2f7;'
            'margin-bottom:4px;">💰 Coin Calculator</div>'
            '<div style="font-size:0.78rem;color:#8a90a3;'
            'margin-bottom:12px;">Video မထုတ်ခင် Coin Cost ကြိုကြည့်ပါ</div>',
            unsafe_allow_html=True,
        )

        video_len = st.slider(
            "📹 Video အရှည် (မိနစ်)",
            min_value=1,
            max_value=30,
            value=5,
            step=1,
            key="coin_calc_video_len",
        )

        cost = calculate_video_cost(video_len)
        user_id = st.session_state.get("user_id")
        balance = 0
        if user_id:
            try:
                balance = cs.get_coin_balance(user_id)
            except Exception:
                balance = 0

        remaining = balance - cost["total"]
        enough = remaining >= 0

        rows_html = ""
        for key, label in COST_LABELS.items():
            if key in cost and cost[key] > 0:
                rows_html += (
                    f'<div style="display:flex;justify-content:space-between;">'
                    f'<span>{label}</span>'
                    f'<span style="color:#c4b5fd;font-weight:700;">'
                    f'{cost[key]} Coin</span></div>'
                )

        if not rows_html:
            rows_html = '<div style="color:#94a3b8;font-size:0.8rem;">Feature မရှိသေး</div>'

        st.markdown(
            f"""
            <div style="padding:12px 14px;border-radius:10px;
                        background:rgba(139,92,246,0.06);
                        border:1px solid rgba(139,92,246,0.18);
                        font-size:0.82rem;color:#cbd5e1;line-height:1.9;">
                {rows_html}
                <hr style="margin:6px 0;border:none;height:1px;
                           background:rgba(139,92,246,0.25);">
                <div style="display:flex;justify-content:space-between;
                            font-size:0.95rem;">
                    <span style="font-weight:700;color:#e2e8f0;">Total</span>
                    <span style="color:#8b5cf6;font-weight:800;">
                        {cost["total"]} Coin
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if enough:
            st.success(f"✅ ကျန်မယ်: **{remaining} Coin**")
        else:
            st.error(f"❌ Coin မလုံလောက် — **{abs(remaining)} Coin** ပိုလိုတယ်")

        return cost

# ============================================================================
# TRANSACTION HISTORY
# ============================================================================
def render_transaction_history():
    """User ရဲ့ Coin အသုံး History"""
    user_id = st.session_state.get("user_id")
    if not user_id:
        return

    with st.container(border=True):
        st.markdown(
            '<div style="font-size:1rem;font-weight:700;color:#f0f2f7;'
            'margin-bottom:4px;">📊 Coin History</div>'
            '<div style="font-size:0.78rem;color:#8a90a3;'
            'margin-bottom:12px;">Coin ထည့်/ဖြတ် မှတ်တမ်း</div>',
            unsafe_allow_html=True,
        )

        try:
            conn = cs.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT action, coins_used, details, created_at
                FROM coin_usage
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 20
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
            conn.close()
        except Exception as e:
            st.caption(f"History မရ: {e}")
            return

        if not rows:
            st.caption("မှတ်တမ်း မရှိသေး")
            return

        for row in rows:
            action = row["action"]
            coins = row["coins_used"]
            details = row["details"] or ""
            created = row["created_at"]

            if action == "add":
                icon = "➕"
                color = "#10b981"
                sign = "+"
                amount = abs(coins)
            else:
                icon = "➖"
                color = "#f43f5e"
                sign = "−"
                amount = abs(coins)

            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;
                            align-items:center;padding:8px 12px;margin:4px 0;
                            border-radius:8px;background:rgba(18,22,32,0.6);
                            border-left:3px solid {color};font-size:0.78rem;">
                    <div>
                        <div style="color:#e2e8f0;font-weight:600;">
                            {icon} {details or action}
                        </div>
                        <div style="color:#64748b;font-size:0.7rem;margin-top:2px;">
                            {created}
                        </div>
                    </div>
                    <div style="color:{color};font-weight:800;font-size:0.9rem;">
                        {sign}{amount}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ============================================================================
# MAIN PANEL
# ============================================================================
def render_coin_panel():
    """Coin Panel — Main Entry"""
    render_balance_card()

    col1, col2 = st.columns([1, 1])

    with col1:
        render_coin_calculator()

    with col2:
        render_transaction_history()

# ============================================================================
# PUBLIC — DEDUCT HELPER (Dynamic)
# ============================================================================
def check_and_deduct_for_video(video_minutes: float) -> dict:
    """Video မထုတ်ခင် — Coin စစ်ပြီး ဖြတ်"""
    user_id = st.session_state.get("user_id")
    if not user_id:
        return {"success": False, "cost": 0, "error": "Login မဝင်ရသေး"}

    cost_data = calculate_video_cost(video_minutes)
    total_cost = cost_data["total"]

    balance = cs.get_coin_balance(user_id)
    if balance < total_cost:
        return {
            "success": False,
            "cost": total_cost,
            "error": f"Coin မလုံလောက် — {total_cost} လိုတယ်၊ {balance} ပဲ ရှိတယ်",
        }

    active_features = [
        COST_LABELS[k] for k in COST_LABELS
        if k in cost_data and cost_data[k] > 0
    ]
    reason = f"Video {video_minutes:.0f} min — " + ", ".join(active_features)

    ok = cs.deduct_coins(user_id, total_cost, reason)
    if not ok:
        return {"success": False, "cost": total_cost, "error": "Coin ဖြတ်မရ"}

    return {"success": True, "cost": total_cost, "error": ""}

# ============================================================================
# 🎯 COMPACT COST PREVIEW — Generate Button အနီး (Dynamic)
# ============================================================================
def render_generate_cost_preview(video_minutes: float = 5.0) -> bool:
    """Generate Button အနီး — Dynamic Cost Panel"""
    user_id = st.session_state.get("user_id")
    if not user_id:
        return False

    cost = calculate_video_cost(video_minutes)
    total = cost["total"]

    balance = 0
    try:
        balance = cs.get_coin_balance(user_id)
    except Exception:
        balance = 0

    remaining = balance - total
    enough = remaining >= 0

    if enough:
        bg = "linear-gradient(135deg,rgba(16,185,129,0.10),rgba(6,182,212,0.05))"
        border = "rgba(16,185,129,0.4)"
        status_color = "#34d399"
        status_icon = "✅"
        status_text = f"ကျန်မယ် — {remaining} Coin"
    else:
        bg = "linear-gradient(135deg,rgba(244,63,94,0.10),rgba(236,72,153,0.05))"
        border = "rgba(244,63,94,0.4)"
        status_color = "#fb7185"
        status_icon = "⚠️"
        status_text = f"မလုံလောက် — {abs(remaining)} Coin ပိုလိုတယ်"

    rows_html = ""
    for key, label in COST_LABELS.items():
        if key in cost and cost[key] > 0:
            rows_html += (
                f'<div style="display:flex;justify-content:space-between;">'
                f'<span>{label}</span>'
                f'<span style="color:#c4b5fd;font-weight:700;">'
                f'{cost[key]} Coin</span></div>'
            )

    if not rows_html:
        rows_html = '<div style="color:#94a3b8;font-size:0.8rem;">Feature မရှိသေး</div>'

    st.markdown(
        f"""
        <div style="
            padding:16px 20px;border-radius:14px;
            background:{bg};border:1px solid {border};
            margin:8px 0 14px;">
            <div style="display:flex;justify-content:space-between;
                        align-items:center;margin-bottom:12px;">
                <div style="font-size:0.9rem;font-weight:800;color:#e2e8f0;">
                    💰 Coin Cost Estimate
                </div>
                <div style="font-size:0.78rem;color:#94a3b8;">
                    📹 {video_minutes:.1f} min
                </div>
            </div>
            <div style="padding:12px 14px;border-radius:10px;
                        background:rgba(18,22,32,0.55);
                        border:1px solid rgba(139,92,246,0.18);
                        font-size:0.85rem;color:#cbd5e1;line-height:2;">
                {rows_html}
                <hr style="margin:8px 0;border:none;height:1px;
                           background:rgba(139,92,246,0.25);">
                <div style="display:flex;justify-content:space-between;
                            font-size:1rem;">
                    <span style="font-weight:800;color:#e2e8f0;">💰 Total</span>
                    <span style="color:#8b5cf6;font-weight:900;">{total} Coin</span>
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;
                        align-items:center;margin-top:12px;padding:10px 14px;
                        border-radius:10px;
                        background:rgba(18,22,32,0.5);
                        border-left:3px solid {status_color};">
                <div style="font-size:0.82rem;color:#94a3b8;">
                    💎 Balance: <b style="color:#e2e8f0;">{balance} Coin</b>
                </div>
                <div style="font-size:0.88rem;font-weight:800;color:{status_color};">
                    {status_icon} {status_text}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return enough