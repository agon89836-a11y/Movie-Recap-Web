#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
PS AI Recap — Payment Panel (Monthly Model)
Monthly Subscription + Optional Top-up Coins
+ Pending Status + Celebration Popup
"""

import os
import streamlit as st
from datetime import datetime, timedelta
from app.services import coin_system as cs


# ============================================================================
# MONTHLY SUBSCRIPTION — Entry Gate
# ============================================================================
MONTHLY_PACKAGE = {
    "name": "Monthly",
    "price_mmk": 3000,
    "coins": 150,
    "is_entry": True,
    "is_monthly": True,
    "duration_days": 30,
    "icon": "🌟",
    "tagline": "စတင်ဖို့ အကောင်းဆုံး အစ",
    "perks": [
        "🪙 ၁၅၀ Coin",
        "📹 ၅ မိနစ် Video ~၇ ခု",
        "🎙 Voice Clone သုံးခွင့်",
        "💎 Premium Features အားလုံး",
        "⏰ ၃၀ ရက် သက်တမ်း",
    ],
}


# ============================================================================
# TOP-UP COIN PACKAGES — Optional (Coin ပဲ)
# ============================================================================
TOPUP_PACKAGES = [
    {"name": "Top-up S",   "price_mmk": 2000,  "coins": 100,  "icon": "💧", "tagline": "အသေးစား"},
    {"name": "Top-up M",   "price_mmk": 4000,  "coins": 210,  "icon": "💧", "tagline": "အလယ်အလတ်"},
    {"name": "Top-up L",   "price_mmk": 5000,  "coins": 275,  "icon": "💧", "tagline": "အလယ်အလတ်+"},
    {"name": "Top-up XL",  "price_mmk": 6000,  "coins": 340,  "icon": "💧", "tagline": "အလယ်အလတ်++"},
    {"name": "Super",      "price_mmk": 8500,  "coins": 500,  "icon": "⚡", "tagline": "Content Creator"},
    {"name": "Mega",       "price_mmk": 10000, "coins": 620,  "icon": "⚡", "tagline": "Popular Value"},
    {"name": "Ultra",      "price_mmk": 16000, "coins": 1050, "icon": "🔥", "tagline": "Serious Creator"},
    {"name": "Titan",      "price_mmk": 20000, "coins": 1400, "icon": "🔥", "tagline": "Professional"},
    {"name": "Legend",     "price_mmk": 30000, "coins": 2250, "icon": "💎", "tagline": "Elite Creator"},
    {"name": "Master",     "price_mmk": 50000, "coins": 4000, "icon": "👑", "tagline": "Studio Level"},
    {"name": "God",        "price_mmk": 75000, "coins": 6500, "icon": "🏆", "tagline": "Ultimate Power"},
]


PAYMENT_METHODS = {
    "kbzpay": {"name": "KBZ Pay", "phone": "09-753553066", "icon": "🔵"},
    "wavepay": {"name": "Wave Pay", "phone": "09-688262875", "icon": "🟡"},
}


def _get_all_packages():
    return [MONTHLY_PACKAGE] + TOPUP_PACKAGES


def _find_package(name: str) -> dict:
    for pkg in _get_all_packages():
        if pkg["name"] == name:
            return pkg
    return {}


def _is_monthly_active(user_id: int) -> bool:
    try:
        return cs.is_monthly_active(user_id)
    except Exception:
        return False


def _get_subscription_status(user_id: int) -> dict:
    try:
        return cs.get_subscription_status(user_id)
    except Exception:
        return {"active": False, "tier": "free", "expires": None, "days_left": 0}


# ============================================================================
# PREMIUM CSS
# ============================================================================
def _inject_premium_css():
    st.markdown(
        """
        <style>
            .psai-welcome-banner {
                position: relative;
                padding: 22px 26px;
                border-radius: 18px;
                background:
                    radial-gradient(circle at 0% 0%, rgba(139,92,246,0.25), transparent 55%),
                    radial-gradient(circle at 100% 100%, rgba(6,182,212,0.18), transparent 55%),
                    linear-gradient(135deg, rgba(18,22,32,0.9), rgba(30,35,55,0.85));
                border: 1px solid rgba(139, 92, 246, 0.35);
                overflow: hidden;
                margin-bottom: 22px;
                animation: psaiFadeIn 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .psai-welcome-banner::before {
                content: '';
                position: absolute;
                top: 0; left: 0; right: 0; height: 2px;
                background: linear-gradient(90deg, transparent, #8b5cf6, #06b6d4, transparent);
            }
            @keyframes psaiFadeIn {
                from { opacity: 0; transform: translateY(-8px); }
                to   { opacity: 1; transform: translateY(0); }
            }
            @keyframes psaiCelebrateIn {
                0% { opacity: 0; transform: scale(0.85) translateY(-10px); }
                60% { opacity: 1; transform: scale(1.03) translateY(0); }
                100% { opacity: 1; transform: scale(1) translateY(0); }
            }
            @keyframes psaiGlow {
                0%, 100% { box-shadow: 0 0 30px rgba(16,185,129,0.4), 0 8px 24px rgba(0,0,0,0.4); }
                50% { box-shadow: 0 0 50px rgba(16,185,129,0.7), 0 8px 24px rgba(0,0,0,0.4); }
            }
            .psai-welcome-title {
                font-size: 1.35rem;
                font-weight: 800;
                background: linear-gradient(135deg, #ffffff 0%, #c4b5fd 60%, #8b5cf6 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 6px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .psai-welcome-desc {
                font-size: 0.88rem;
                color: #94a3b8;
                line-height: 1.7;
            }
            .psai-welcome-desc b { color: #c4b5fd; }

            .psai-section-title {
                font-size: 1.05rem;
                font-weight: 750;
                color: #e2e8f0;
                margin: 18px 0 12px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .psai-section-title::after {
                content: '';
                flex: 1;
                height: 1px;
                background: linear-gradient(90deg, rgba(139,92,246,0.4), transparent);
                margin-left: 10px;
            }

            .psai-pkg-card {
                position: relative;
                padding: 18px 20px;
                border-radius: 16px;
                background: linear-gradient(155deg, rgba(22,26,38,0.95), rgba(18,22,32,0.85));
                border: 1px solid rgba(148, 163, 184, 0.14);
                transition: all 0.28s cubic-bezier(0.34, 1.4, 0.64, 1);
                overflow: hidden;
                margin-bottom: 10px;
            }
            .psai-pkg-card:hover {
                transform: translateY(-3px);
                border-color: rgba(139, 92, 246, 0.45);
                box-shadow:
                    0 12px 32px rgba(139, 92, 246, 0.18),
                    0 4px 14px rgba(0, 0, 0, 0.25);
            }
            .psai-pkg-card::before {
                content: '';
                position: absolute;
                top: 0; left: 0; width: 4px; height: 100%;
                background: linear-gradient(180deg, #8b5cf6, #06b6d4);
                border-radius: 16px 0 0 16px;
            }
            .psai-pkg-card.monthly {
                border: 1.5px solid rgba(16, 185, 129, 0.5);
                background:
                    radial-gradient(circle at 100% 0%, rgba(16,185,129,0.15), transparent 60%),
                    linear-gradient(155deg, rgba(22,26,38,0.95), rgba(18,22,32,0.85));
            }
            .psai-pkg-card.monthly::before {
                background: linear-gradient(180deg, #10b981, #06b6d4);
            }
            .psai-pkg-card.hot {
                border: 1.5px solid rgba(245, 158, 11, 0.4);
                background:
                    radial-gradient(circle at 100% 0%, rgba(245,158,11,0.12), transparent 60%),
                    linear-gradient(155deg, rgba(22,26,38,0.95), rgba(18,22,32,0.85));
            }
            .psai-pkg-card.hot::before {
                background: linear-gradient(180deg, #f59e0b, #ef4444);
            }
            .psai-pkg-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 8px;
            }
            .psai-pkg-name {
                font-size: 1.05rem;
                font-weight: 800;
                color: #f0f2f7;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .psai-pkg-tagline {
                font-size: 0.72rem;
                color: #64748b;
                margin-top: 3px;
                font-weight: 500;
            }
            .psai-pkg-price { text-align: right; }
            .psai-pkg-price-main {
                font-size: 1.25rem;
                font-weight: 900;
                background: linear-gradient(135deg, #c4b5fd, #8b5cf6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                line-height: 1.1;
            }
            .psai-pkg-price-sub {
                font-size: 0.68rem;
                color: #64748b;
                margin-top: 2px;
            }
            .psai-pkg-coins {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 5px 12px;
                border-radius: 999px;
                background: rgba(139, 92, 246, 0.12);
                border: 1px solid rgba(139, 92, 246, 0.3);
                color: #c4b5fd;
                font-size: 0.82rem;
                font-weight: 700;
                margin-top: 8px;
            }
            .psai-pkg-rate {
                font-size: 0.72rem;
                color: #64748b;
                margin-left: 6px;
            }
            .psai-badge {
                display: inline-block;
                padding: 2px 9px;
                border-radius: 999px;
                font-size: 0.6rem;
                font-weight: 800;
                letter-spacing: 0.5px;
                margin-left: 6px;
                vertical-align: middle;
            }
            .psai-badge.entry {
                background: linear-gradient(135deg, #10b981, #06b6d4);
                color: #fff;
                box-shadow: 0 2px 8px rgba(16,185,129,0.4);
            }
            .psai-badge.hot {
                background: linear-gradient(135deg, #f59e0b, #ef4444);
                color: #fff;
                box-shadow: 0 2px 8px rgba(245,158,11,0.4);
            }
            .psai-badge.best {
                background: linear-gradient(135deg, #10b981, #06b6d4);
                color: #fff;
                box-shadow: 0 2px 8px rgba(16,185,129,0.4);
            }
            .psai-badge.active {
                background: linear-gradient(135deg, #10b981, #34d399);
                color: #fff;
                box-shadow: 0 2px 8px rgba(16,185,129,0.4);
            }

            .psai-perks {
                display: flex;
                flex-direction: column;
                gap: 5px;
                margin-top: 10px;
                padding: 10px 14px;
                border-radius: 10px;
                background: rgba(16, 185, 129, 0.05);
                border: 1px solid rgba(16, 185, 129, 0.15);
            }
            .psai-perk {
                font-size: 0.78rem;
                color: #cbd5e1;
                line-height: 1.6;
                display: flex;
                align-items: center;
                gap: 6px;
            }

            .psai-method-card {
                padding: 16px 20px;
                border-radius: 14px;
                background: linear-gradient(135deg, rgba(139,92,246,0.14), rgba(6,182,212,0.06));
                border: 1px solid rgba(139, 92, 246, 0.35);
                text-align: center;
                margin: 14px 0;
            }
            .psai-method-label {
                font-size: 0.72rem;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 1.4px;
                margin-bottom: 6px;
            }
            .psai-method-phone {
                font-size: 1.9rem;
                font-weight: 900;
                color: #e2e8f0;
                letter-spacing: 2.5px;
                font-family: 'Courier New', monospace;
            }
            .psai-method-amount {
                font-size: 0.95rem;
                color: #c4b5fd;
                margin-top: 6px;
                font-weight: 700;
            }

            .psai-tx-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 14px;
                margin: 5px 0;
                border-radius: 10px;
                background: rgba(18, 22, 32, 0.65);
                font-size: 0.8rem;
                transition: background 0.15s ease;
            }
            .psai-tx-row:hover {
                background: rgba(139, 92, 246, 0.08);
            }

            .psai-status-card {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px 20px;
                border-radius: 14px;
                margin-bottom: 16px;
            }
            .psai-status-card.active {
                background: linear-gradient(135deg, rgba(16,185,129,0.15), rgba(6,182,212,0.08));
                border: 1px solid rgba(16,185,129,0.45);
            }
            .psai-status-card.free {
                background: linear-gradient(135deg, rgba(148,163,184,0.08), rgba(100,116,139,0.04));
                border: 1px solid rgba(148,163,184,0.25);
            }

            .psai-celebration {
                position: relative;
                padding: 28px 32px;
                border-radius: 20px;
                background:
                    radial-gradient(circle at 0% 0%, rgba(16,185,129,0.25), transparent 55%),
                    radial-gradient(circle at 100% 100%, rgba(6,182,212,0.18), transparent 55%),
                    linear-gradient(135deg, rgba(18,22,32,0.98), rgba(30,35,55,0.95));
                border: 2px solid rgba(16,185,129,0.6);
                animation: psaiCelebrateIn 0.8s cubic-bezier(0.34, 1.56, 0.64, 1),
                           psaiGlow 2s ease-in-out infinite;
                margin-bottom: 22px;
                overflow: hidden;
            }
            .psai-celebration::before {
                content: '';
                position: absolute;
                top: 0; left: 0; right: 0; height: 3px;
                background: linear-gradient(90deg, transparent, #10b981, #06b6d4, #10b981, transparent);
            }
            .psai-celebration-title {
                font-size: 1.6rem;
                font-weight: 900;
                background: linear-gradient(135deg, #ffffff, #34d399, #10b981);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 6px;
            }
            .psai-celebration-sub {
                font-size: 0.9rem;
                color: #94a3b8;
                margin-bottom: 16px;
            }
            .psai-celebration-box {
                padding: 16px 20px;
                border-radius: 12px;
                background: rgba(16,185,129,0.08);
                border: 1px solid rgba(16,185,129,0.3);
                margin-bottom: 14px;
            }
            .psai-celebration-row {
                display: flex;
                justify-content: space-between;
                font-size: 0.88rem;
                color: #cbd5e1;
                margin: 5px 0;
            }
            .psai-celebration-value {
                color: #34d399;
                font-weight: 800;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================================
# 🎉 CELEBRATION POPUP
# ============================================================================
def _render_celebration_popup():
    """Approved Transaction အတွက် Celebration"""
    user_id = st.session_state.get("user_id")
    if not user_id:
        return

    shown_ids = st.session_state.get("celebration_shown", [])
    try:
        tx = cs.get_unnotified_approved_tx(user_id)
    except Exception:
        return

    if not tx:
        return

    tx_id = tx["id"]
    if tx_id in shown_ids:
        return

    pkg_name = tx.get("package_name", "")
    coins = tx.get("coins", 0)
    amount = tx.get("amount_mmk", 0)
    ref = tx.get("reference_no", "")
    is_monthly = pkg_name in ("Monthly", "Monthly Subscription", "Starter")

    bonus_line = ""
    if is_monthly:
        bonus_line = (
            '<div style="font-size:0.95rem;color:#34d399;'
            'font-weight:800;margin-top:4px;">🌟 +၃၀ ရက် Subscription</div>'
        )

    html = (
        '<div class="psai-celebration">'
        '<div class="psai-celebration-title">'
        '🎉 Payment Approved! '
        '<span style="font-size:1.8rem;">✅</span>'
        '</div>'
        '<div class="psai-celebration-sub">'
        '🎊 ကျေးဇူးတင်ပါသည် — သင့် Package ရောက်ပါပြီ'
        '</div>'
        '<div class="psai-celebration-box">'
        '<div class="psai-celebration-row">'
        '<span style="color:#94a3b8;">📦 Package</span>'
        f'<span style="color:#e2e8f0;font-weight:800;">{pkg_name}</span>'
        '</div>'
        '<div class="psai-celebration-row">'
        '<span style="color:#94a3b8;">💰 Amount</span>'
        f'<span style="color:#e2e8f0;font-weight:700;">{amount:,} ကျပ်</span>'
        '</div>'
        '<div class="psai-celebration-row">'
        '<span style="color:#94a3b8;">🪙 Coins</span>'
        f'<span class="psai-celebration-value">+{coins:,} Coin</span>'
        '</div>'
        '<div class="psai-celebration-row">'
        '<span style="color:#94a3b8;">🔢 Ref No.</span>'
        '<span style="color:#10b981;font-family:monospace;'
        f'letter-spacing:2px;font-weight:700;">{ref}</span>'
        '</div>'
        + bonus_line +
        '</div>'
        '<div style="padding:12px 16px;border-radius:10px;'
        'background:rgba(139,92,246,0.1);'
        'border:1px solid rgba(139,92,246,0.3);'
        'font-size:0.85rem;color:#c4b5fd;font-weight:700;'
        'text-align:center;">'
        '🎬 ယခု Video Generate လုပ်လို့ ရပါပြီ!'
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    try:
        cs.mark_tx_notified(tx_id)
    except Exception:
        pass
    shown_ids.append(tx_id)
    st.session_state["celebration_shown"] = shown_ids


# ============================================================================
# ⏳ PENDING STATUS
# ============================================================================
def _render_pending_status():
    """Pending Payment Status — User မြင်ရမယ့် Status Panel"""
    user_id = st.session_state.get("user_id")
    if not user_id:
        return

    try:
        conn = cs.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, package_name, amount_mmk, coins, method,
                   reference_no, status, created_at
            FROM transactions
            WHERE user_id = ? AND status = 'pending'
            ORDER BY id DESC
            """,
            (user_id,),
        )
        pending_rows = cursor.fetchall()
        conn.close()
    except Exception:
        return

    if not pending_rows:
        return

    for row in pending_rows:
        html = (
            '<div style="padding:24px 28px;border-radius:18px;'
            'background:radial-gradient(circle at 0% 0%, rgba(245,158,11,0.18), transparent 55%),'
            'radial-gradient(circle at 100% 100%, rgba(251,191,36,0.12), transparent 55%),'
            'linear-gradient(135deg, rgba(18,22,32,0.95), rgba(30,35,55,0.9));'
            'border:1.5px solid rgba(245,158,11,0.45);margin-bottom:18px;">'
            '<div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;">'
            '<span style="font-size:2rem;">⏳</span>'
            '<div>'
            '<div style="font-size:1.2rem;font-weight:800;color:#fbbf24;">'
            'Admin စစ်ဆေးနေပါသည်'
            '</div>'
            '<div style="font-size:0.82rem;color:#94a3b8;margin-top:3px;">'
            'ခနစောင့်ပေးပါဗျ — ပုံမှန်အားဖြင့် ၅–၃၀ မိနစ်အတွင်း'
            '</div>'
            '</div>'
            '</div>'
            '<div style="padding:14px 18px;border-radius:12px;'
            'background:rgba(18,22,32,0.6);border-left:3px solid #f59e0b;'
            'font-size:0.85rem;color:#cbd5e1;line-height:1.9;">'
            '<div style="display:flex;justify-content:space-between;">'
            '<span style="color:#64748b;">📦 Package</span>'
            f'<span style="color:#e2e8f0;font-weight:700;">{row["package_name"]}</span>'
            '</div>'
            '<div style="display:flex;justify-content:space-between;">'
            '<span style="color:#64748b;">💰 Amount</span>'
            f'<span style="color:#e2e8f0;font-weight:700;">{row["amount_mmk"]:,} ကျပ်</span>'
            '</div>'
            '<div style="display:flex;justify-content:space-between;">'
            '<span style="color:#64748b;">🪙 Coins</span>'
            f'<span style="color:#c4b5fd;font-weight:700;">{row["coins"]:,} Coin</span>'
            '</div>'
            '<div style="display:flex;justify-content:space-between;">'
            '<span style="color:#64748b;">💳 Method</span>'
            f'<span style="color:#e2e8f0;font-weight:700;">{row["method"].upper()}</span>'
            '</div>'
            '<div style="display:flex;justify-content:space-between;">'
            '<span style="color:#64748b;">🔢 Ref No.</span>'
            '<span style="color:#10b981;font-weight:700;'
            'font-family:monospace;letter-spacing:2px;">'
            f'{row["reference_no"]}'
            '</span>'
            '</div>'
            '<div style="display:flex;justify-content:space-between;">'
            '<span style="color:#64748b;">📅 Time</span>'
            f'<span style="color:#e2e8f0;font-weight:600;">{row["created_at"]}</span>'
            '</div>'
            '</div>'
            '<div style="margin-top:16px;padding:12px 16px;border-radius:10px;'
            'background:rgba(139,92,246,0.08);border:1px solid rgba(139,92,246,0.2);'
            'font-size:0.8rem;color:#cbd5e1;line-height:1.8;">'
            '🙏 <b style="color:#c4b5fd;">စိတ်ရှည်စွာ စောင့်ဆိုင်းပေးပါ</b><br>'
            '📞 <b>Admin ဆက်သွယ်ရန်:</b> '
            '<span style="display:inline-flex;align-items:center;'
            'gap:6px;padding:4px 12px;border-radius:999px;'
            'background:linear-gradient(135deg,rgba(41,182,246,0.18),rgba(0,136,204,0.12));'
            'border:1px solid rgba(41,182,246,0.4);'
            'box-shadow:0 2px 8px rgba(41,182,246,0.25);">'
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240" '
            'style="width:16px;height:16px;display:inline-block;flex-shrink:0;">'
            '<circle cx="120" cy="120" r="120" fill="#29B6F6"/>'
            '<path fill="#ffffff" d="M54.3 118.8l110.8-42.6c5.1-1.9 9.6 1.2 7.9 8.7'
            'l-18.9 88.9c-1.4 6.3-5.1 7.8-10.3 4.9l-28.5-21-13.7 13.2'
            'c-1.5 1.5-2.8 2.8-5.7 2.8l2-28.9 52.5-47.4c2.3-2-.5-3.2-3.5-1.2'
            'l-64.8 40.8-27.9-8.7c-6.1-1.9-6.2-6.1 1.1-8.5z"/></svg>'
            '<span style="color:#29B6F6;font-weight:700;letter-spacing:0.5px;">'
            '@Ps2005b'
            '</span>'
            '</span><br>'
            '⏱ <b>Response Time:</b> ၅–၃၀ မိနစ်'
            '</div>'
            '</div>'
        )
        st.markdown(html, unsafe_allow_html=True)


# ============================================================================
# MONTHLY PACKAGE CARD
# ============================================================================
def _render_monthly_card(pkg: dict, is_active: bool = False, days_left: int = 0, key_suffix: str = ""):
    badge = (
        '<span class="psai-badge active">✅ ACTIVE</span>'
        if is_active
        else '<span class="psai-badge entry">ENTRY</span>'
    )

    icon = pkg.get("icon", "🌟")
    tagline = pkg.get("tagline", "")
    rate = pkg["price_mmk"] / pkg["coins"]

    card_html = (
        '<div class="psai-pkg-card monthly">'
        '<div class="psai-pkg-header">'
        '<div>'
        '<div class="psai-pkg-name">'
        f'{icon} {pkg["name"]} Subscription {badge}'
        '</div>'
        f'<div class="psai-pkg-tagline">{tagline}</div>'
        '</div>'
        '<div class="psai-pkg-price">'
        f'<div class="psai-pkg-price-main">{pkg["price_mmk"]:,}</div>'
        '<div class="psai-pkg-price-sub">ကျပ် / လ</div>'
        '</div>'
        '</div>'
        '<div>'
        '<span class="psai-pkg-coins">'
        f'🪙 {pkg["coins"]} Coin '
        f'<span class="psai-pkg-rate">· {rate:.1f} ကျပ်/Coin</span>'
        '</span>'
        '</div>'
        '</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

    if pkg.get("perks"):
        perks_html = "".join(
            f'<div class="psai-perk">{p}</div>' for p in pkg["perks"]
        )
        st.markdown(
            f'<div class="psai-perks">{perks_html}</div>',
            unsafe_allow_html=True,
        )

    if is_active:
        st.success(f"✅ Monthly Active — ကျန်ရက် **{days_left} ရက်**")
        st.caption("🔄 Renew လုပ်ရင် — ကျန်ရက် + ၃၀ ရက် ထပ်တိုး")
        if st.button(
            "🔄 Monthly Renew (၃,၀၀၀ ကျပ်)",
            key=f"renew_monthly{key_suffix}",
            use_container_width=True,
            type="primary",
        ):
            st.session_state["selected_package"] = pkg["name"]
            st.session_state["show_payment_form"] = True
            st.rerun()
    else:
        if st.button(
            "🌟 Monthly ဝယ်မယ် (၃,၀၀၀ ကျပ်)",
            key=f"buy_monthly{key_suffix}",
            use_container_width=True,
            type="primary",
        ):
            st.session_state["selected_package"] = pkg["name"]
            st.session_state["show_payment_form"] = True
            st.rerun()


# ============================================================================
# TOP-UP PACKAGE CARD
# ============================================================================
def _render_topup_card(pkg: dict, key_suffix: str = ""):
    is_hot = pkg["name"] in ("Super", "Ultra")
    is_best = pkg["name"] in ("Mega", "Legend")

    card_class = "psai-pkg-card"
    if is_hot or is_best:
        card_class += " hot"

    badge_html = ""
    if is_best:
        badge_html = '<span class="psai-badge best">BEST VALUE</span>'
    elif is_hot:
        badge_html = '<span class="psai-badge hot">HOT</span>'

    icon = pkg.get("icon", "💠")
    tagline = pkg.get("tagline", "")
    rate = pkg["price_mmk"] / pkg["coins"]

    card_html = (
        f'<div class="{card_class}">'
        '<div class="psai-pkg-header">'
        '<div>'
        '<div class="psai-pkg-name">'
        f'{icon} {pkg["name"]}{badge_html}'
        '</div>'
        f'<div class="psai-pkg-tagline">{tagline}</div>'
        '</div>'
        '<div class="psai-pkg-price">'
        f'<div class="psai-pkg-price-main">{pkg["price_mmk"]:,}</div>'
        '<div class="psai-pkg-price-sub">ကျပ်</div>'
        '</div>'
        '</div>'
        '<div>'
        '<span class="psai-pkg-coins">'
        f'🪙 {pkg["coins"]} Coin '
        f'<span class="psai-pkg-rate">· {rate:.1f} ကျပ်/Coin</span>'
        '</span>'
        '</div>'
        '</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

    if st.button(
        f"💳 {pkg['name']} ဝယ်မယ်",
        key=f"buy_{pkg['name']}{key_suffix}",
        use_container_width=True,
        type="secondary",
    ):
        st.session_state["selected_package"] = pkg["name"]
        st.session_state["show_payment_form"] = True
        st.rerun()


# ============================================================================
# PAYMENT FORM
# ============================================================================
def _render_payment_form(pkg: dict):
    user_id = st.session_state.get("user_id")
    user_code = st.session_state.get("user_code", "")

    st.markdown("---")

    is_monthly = pkg.get("is_monthly", False)
    pkg_type = "🌟 Monthly Subscription" if is_monthly else "🪙 Top-up Coin"

    # --- Welcome Banner ---
    monthly_tag = " · <b>၃၀ ရက် Subscription</b>" if is_monthly else ""
    welcome_html = (
        '<div class="psai-welcome-banner">'
        '<div class="psai-welcome-title">'
        f'💳 {pkg["name"]} — {pkg_type}'
        '</div>'
        '<div class="psai-welcome-desc">'
        f'ငွေလွှဲရန် — <b>{pkg["price_mmk"]:,} ကျပ်</b> · '
        f'လက်ခံရမည် — <b>{pkg["coins"]} Coin</b>'
        f'{monthly_tag}'
        '</div>'
        '</div>'
    )
    st.markdown(welcome_html, unsafe_allow_html=True)

    # --- Payment Method ---
    method = st.radio(
        "💳 ငွေလွှဲမည့် နည်းလမ်း",
        options=list(PAYMENT_METHODS.keys()),
        format_func=lambda k: f"{PAYMENT_METHODS[k]['icon']} {PAYMENT_METHODS[k]['name']}",
        horizontal=True,
        key="payment_method_radio",
    )

    method_info = PAYMENT_METHODS[method]

    method_html = (
        '<div class="psai-method-card">'
        '<div class="psai-method-label">'
        f'{method_info["name"]} — ငွေလွှဲရန်'
        '</div>'
        '<div class="psai-method-phone">'
        f'{method_info["phone"]}'
        '</div>'
        '<div class="psai-method-amount">'
        f'💰 {pkg["price_mmk"]:,} ကျပ်'
        '</div>'
        '</div>'
    )
    st.markdown(method_html, unsafe_allow_html=True)

    st.info(
        "📌 **အဆင့်လိုက် လုပ်ဆောင်ရန်**\n\n"
        f"**၁။** {method_info['name']} App ကို ဖွင့်ပါ\n\n"
        f"**၂။** **{method_info['phone']}** သို့ ငွေလွှဲပါ\n\n"
        f"**၃။** **{pkg['price_mmk']:,} ကျပ်** လွှဲပါ\n\n"
        "**၄။** ပြေစာ (Screenshot) ရိုက်ပါ\n\n"
        "**၅။** ပြေစာထဲက **နောက်ဆုံး ၅ လုံး** ကို မှတ်ပါ\n\n"
        "**၆။** အောက်တွင် ဖြည့်ပြီး တင်ပါ"
    )

    # --- Reference No. Box ---
    ref_html = (
        '<div style="padding:12px 16px;border-radius:12px;'
        'background:linear-gradient(135deg,rgba(16,185,129,0.12),rgba(6,182,212,0.06));'
        'border:1px solid rgba(16,185,129,0.35);margin:14px 0 8px;">'
        '<div style="font-size:0.92rem;font-weight:750;color:#e2e8f0;margin-bottom:4px;">'
        '🔢 Reference No. — နောက်ဆုံး ၅ လုံးပဲ'
        '</div>'
        '<div style="font-size:0.78rem;color:#94a3b8;line-height:1.6;">'
        '💡 ပြေစာထဲမှာ ပါတဲ့ Reference No. ရဲ့ '
        '<b style="color:#c4b5fd;">နောက်ဆုံး ဂဏန်း ၅ လုံး</b> ကို '
        'ထည့်ပေးပါ။ ဥပမာ — '
        '<code style="color:#10b981;">2026091912345678</code> '
        'ဆိုရင် <code style="color:#10b981;">45678</code> ကို ထည့်ပါ။'
        '</div>'
        '</div>'
    )
    st.markdown(ref_html, unsafe_allow_html=True)

    ref_no = st.text_input(
        "နောက်ဆုံး ၅ လုံး",
        placeholder="ဥပမာ — 45678",
        max_chars=5,
        key="payment_ref_no",
        label_visibility="collapsed",
    )

    screenshot = st.file_uploader(
        "📸 ပြေစာ (Screenshot)",
        type=["png", "jpg", "jpeg"],
        key="payment_screenshot",
    )

    col_cancel, col_submit = st.columns(2)

    with col_cancel:
        if st.button("↩️ ပြန်ထွက်", use_container_width=True, key="payment_cancel"):
            st.session_state["show_payment_form"] = False
            st.session_state["selected_package"] = ""
            st.rerun()

    with col_submit:
        if st.button(
            "✅ တင်သွင်းမည်",
            use_container_width=True,
            type="primary",
            key="payment_submit",
        ):
            _submit_payment(user_id, user_code, pkg, method, ref_no, screenshot)


# ============================================================================
# SUBMIT PAYMENT
# ============================================================================
def _submit_payment(user_id, user_code, pkg, method, ref_no, screenshot):
    ref_no = (ref_no or "").strip()

    if not ref_no:
        st.warning("⚠️ Reference No. ထည့်ပေးပါ")
        return

    if not ref_no.isdigit():
        st.warning("⚠️ Reference No. က ဂဏန်း သီးသန့် ဖြစ်ရပါမယ်")
        return

    if len(ref_no) != 5:
        st.warning("⚠️ Reference No. — ၅ လုံး အတိအကျ ဖြစ်ရပါမယ်")
        return

    if screenshot is None:
        st.warning("⚠️ ပြေစာ Screenshot ထည့်ပေးပါ")
        return

    try:
        from app.utils import utils
        screenshot_dir = os.path.join(utils.storage_dir(), "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(screenshot.name)[1] or ".png"
        filename = f"{user_code}_{pkg['name']}_{timestamp}{ext}"
        screenshot_path = os.path.join(screenshot_dir, filename)

        with open(screenshot_path, "wb") as f:
            f.write(screenshot.getbuffer())
    except Exception as e:
        st.error(f"❌ Screenshot သိမ်းဆည်းမှု အဆင်မပြေ: {e}")
        return

    try:
        conn = cs.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions
                (user_id, package_name, amount_mmk, coins,
                 method, reference_no, screenshot_path, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                user_id,
                pkg["name"],
                pkg["price_mmk"],
                pkg["coins"],
                method,
                ref_no,
                screenshot_path,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"❌ ငွေလွှဲမှတ်တမ်း မသိမ်းနိုင်ပါ: {e}")
        return

    st.success("✨ ပြေစာ တင်သွင်းမှု အောင်မြင်ပါသည်")
    st.info(
        "⏳ **Admin မှ စစ်ဆေးနေပါသည်** — "
        "ပုံမှန်အားဖြင့် ၅–၃၀ မိနစ်အတွင်း Coin ရောက်ရှိပါမည်။\n\n"
        "🙏 စိတ်ရှည်စွာ စောင့်ဆိုင်းပေးသည့်အတွက် ကျေးဇူးတင်ပါသည်။"
    )

    st.session_state["show_payment_form"] = False
    st.session_state["selected_package"] = ""

    st.balloons()
    st.rerun()


# ============================================================================
# MY TRANSACTIONS
# ============================================================================
def _render_my_transactions():
    user_id = st.session_state.get("user_id")
    if not user_id:
        return

    with st.container(border=True):
        st.markdown(
            '<div class="psai-section-title">📋 ငွေလွှဲမှတ်တမ်း</div>',
            unsafe_allow_html=True,
        )

        try:
            conn = cs.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT package_name, amount_mmk, coins, method,
                       reference_no, status, created_at
                FROM transactions
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 10
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
            conn.close()
        except Exception as e:
            st.caption(f"မှတ်တမ်း မရယူနိုင်ပါ: {e}")
            return

        if not rows:
            st.caption("📭 မှတ်တမ်း မရှိသေးပါ")
            return

        for row in rows:
            status = row["status"]
            if status == "pending":
                icon, color, text = "⏳", "#f59e0b", "စစ်ဆေးနေသည်"
            elif status == "approved":
                icon, color, text = "✅", "#10b981", "အောင်မြင်ပြီး"
            else:
                icon, color, text = "❌", "#f43f5e", "ငြင်းပယ်ခဲ့သည်"

            tx_html = (
                f'<div class="psai-tx-row" style="border-left:3px solid {color};">'
                '<div>'
                '<div style="color:#e2e8f0;font-weight:600;">'
                f'{icon} {row["package_name"]} · {row["coins"]} Coin'
                '</div>'
                '<div style="color:#64748b;font-size:0.68rem;margin-top:2px;">'
                f'{row["method"]} · Ref <b>{row["reference_no"]}</b> · {row["created_at"]}'
                '</div>'
                '</div>'
                f'<div style="color:{color};font-weight:800;font-size:0.78rem;">'
                f'{text}'
                '</div>'
                '</div>'
            )
            st.markdown(tx_html, unsafe_allow_html=True)


# ============================================================================
# MAIN PANEL
# ============================================================================
def render_payment_panel():
    _inject_premium_css()

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.warning("⚠️ Login မဝင်ရသေးပါ")
        return

    # 🎉 Celebration Popup — Approved Transaction ရှိရင် ပြ
    _render_celebration_popup()

    if st.session_state.get("show_payment_form"):
        selected = st.session_state.get("selected_package", "")
        pkg = _find_package(selected)
        if pkg:
            _render_payment_form(pkg)
            return
        else:
            st.session_state["show_payment_form"] = False

    # ⏳ Pending Status — အပေါ်ဆုံး
    _render_pending_status()

    # ========================================================================
    # SUBSCRIPTION STATUS
    # ========================================================================
    sub = _get_subscription_status(user_id)
    is_active = sub.get("active", False)
    days_left = sub.get("days_left", 0)
    expires = sub.get("expires", "")

    if is_active:
        expires_str = ""
        if expires:
            try:
                exp_dt = datetime.fromisoformat(str(expires).replace(" ", "T"))
                expires_str = exp_dt.strftime("%Y-%m-%d")
            except Exception:
                expires_str = str(expires)[:10]

        status_html = (
            '<div class="psai-status-card active">'
            '<div>'
            '<div style="font-size:1rem;font-weight:800;color:#34d399;">'
            '🌟 Monthly Active'
            '</div>'
            '<div style="font-size:0.82rem;color:#94a3b8;margin-top:4px;">'
            '✅ Premium Features အားလုံး သုံးလို့ ရ'
            '</div>'
            '</div>'
            '<div style="text-align:right;">'
            '<div style="font-size:0.72rem;color:#94a3b8;">ကျန်ရက်</div>'
            '<div style="font-size:1.8rem;font-weight:900;'
            'background:linear-gradient(135deg,#34d399,#10b981);'
            '-webkit-background-clip:text;-webkit-text-fill-color:transparent;'
            'background-clip:text;line-height:1.1;">'
            f'{days_left} ရက်'
            '</div>'
            '<div style="font-size:0.68rem;color:#64748b;margin-top:2px;">'
            f'{expires_str}'
            '</div>'
            '</div>'
            '</div>'
        )
        st.markdown(status_html, unsafe_allow_html=True)
    else:
        free_html = (
            '<div class="psai-status-card free">'
            '<div>'
            '<div style="font-size:1rem;font-weight:800;color:#94a3b8;">'
            '🆓 Free User'
            '</div>'
            '<div style="font-size:0.82rem;color:#64748b;margin-top:4px;">'
            '🌟 Monthly ဝယ်ရင် — Premium Features အားလုံး ရ'
            '</div>'
            '</div>'
            '</div>'
        )
        st.markdown(free_html, unsafe_allow_html=True)

    # ========================================================================
    # MONTHLY SUBSCRIPTION (Entry Gate)
    # ========================================================================
    if not is_active:
        banner_html = (
            '<div class="psai-welcome-banner" style="'
            'border-color: rgba(16,185,129,0.4);'
            'background:'
            'radial-gradient(circle at 0% 0%, rgba(16,185,129,0.2), transparent 55%),'
            'radial-gradient(circle at 100% 100%, rgba(6,182,212,0.15), transparent 55%),'
            'linear-gradient(135deg, rgba(18,22,32,0.9), rgba(30,35,55,0.85));'
            '">'
            '<div class="psai-welcome-title">'
            '🌟 စတင်ရန် အဆင့်တစ်ဆင့်သာ လိုပါသည်'
            '</div>'
            '<div class="psai-welcome-desc">'
            '<b>Monthly Subscription (၃,၀၀၀ ကျပ်/လ)</b> ဝယ်ယူပြီးရင် '
            '<b>Premium Features အားလုံး</b> ကို '
            'ချက်ချင်း သုံးလို့ ရပါပြီ။ '
            'သင့်ခရီးစဉ် ဒီကနေ စတင်ပါ။ 🚀'
            '</div>'
            '</div>'
        )
        st.markdown(banner_html, unsafe_allow_html=True)

        st.markdown(
            '<div class="psai-section-title">🌟 Monthly Subscription</div>',
            unsafe_allow_html=True,
        )

        _render_monthly_card(MONTHLY_PACKAGE, is_active=False, key_suffix="_entry")

        with st.expander("ℹ️ Monthly Subscription အကြောင်း လေ့လာရန်"):
            st.markdown(
                """
                **🌟 Monthly Subscription — ၃,၀၀၀ ကျပ်/လ**

                ဒါက သင့်ရဲ့ **ပထမဆုံး ခရီးစဉ်** ပါ။ 
                ၃၀ ရက် သက်တမ်းနဲ့ — Premium Features အားလုံး ရပါတယ်။

                **ရရှိမည့်အရာများ —**
                - 🪙 **၁၅၀ Coin** 
                - 📹 ၅ မိနစ် Video ~၇ ခု
                - 🎙 **Voice Clone** သုံးခွင့်
                - 💎 **1080p HD** Export
                - 🚀 **Priority Queue** (၃ ဆ မြန်)
                - ⏰ **၃၀ ရက်** သက်တမ်း

                **Coin ကုန်သွားရင် —** Top-up Package ထပ်ဝယ်လို့ ရပါတယ်။
                """
            )

    else:
        st.markdown(
            '<div class="psai-section-title">🌟 Monthly Subscription — Active</div>',
            unsafe_allow_html=True,
        )

        _render_monthly_card(MONTHLY_PACKAGE, is_active=True, days_left=days_left, key_suffix="_active")

    # ========================================================================
    # TOP-UP PACKAGES
    # ========================================================================
    if is_active:
        st.markdown("---")
        st.markdown(
            '<div class="psai-section-title">🪙 Top-up Coin Packages (Optional)</div>',
            unsafe_allow_html=True,
        )
        st.caption("💰 Coin ကုန်သွားရင် — ထပ်ဝယ်လို့ ရ (Premium Features ရှိပြီးသား)")

        cols = st.columns(2)
        for idx, pkg in enumerate(TOPUP_PACKAGES):
            with cols[idx % 2]:
                _render_topup_card(pkg, key_suffix=f"_topup_{idx}")
    else:
        st.markdown("---")
        st.markdown(
            '<div class="psai-section-title" style="opacity:0.5;">'
            '🪙 Top-up Coin Packages 🔒</div>',
            unsafe_allow_html=True,
        )
        st.caption("🔒 Monthly Subscription ဝယ်ပြီးမှ Top-up Package တွေ ဝယ်လို့ ရမယ်")

    # ========================================================================
    # MY TRANSACTIONS
    # ========================================================================
    st.markdown("---")
    _render_my_transactions()


def has_starter(user_id: int) -> bool:
    """Legacy — Keep for backward compatibility"""
    return _is_monthly_active(user_id)