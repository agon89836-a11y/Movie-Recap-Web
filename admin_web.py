#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
PS AI Recap — Admin Web
Port 8502 · Password Protected
Receipt Approval Panel (Top Priority)
Monthly Subscription Support
"""

import os
import sys
import streamlit as st
from datetime import datetime
from loguru import logger

# ============================================================================
# PATH SETUP
# ============================================================================
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from app.config import config
from app.services import coin_system as cs
from app.utils import utils


# ============================================================================
# ADMIN PASSWORD
# ============================================================================
ADMIN_PASSWORD = "PSARecapAdmin@2026"


# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="PS AI Recap — Admin",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================================
# CSS
# ============================================================================
st.markdown(
    """
    <style>
        .stApp { background: #0a0d14 !important; }

        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter',
                         'Helvetica Neue', Arial, sans-serif !important;
            -webkit-font-smoothing: antialiased !important;
        }

        .admin-header {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 10px 0 18px;
        }
        .admin-logo {
            width: 60px; height: 60px;
            border-radius: 16px;
            background: linear-gradient(135deg, #f43f5e, #ec4899);
            display: flex; align-items: center; justify-content: center;
            font-size: 30px;
            box-shadow: 0 10px 30px rgba(244,63,94,0.4);
        }
        .admin-title {
            font-size: 1.8rem;
            font-weight: 900;
            background: linear-gradient(135deg, #ffffff, #fda4af, #f43f5e);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1;
        }
        .admin-sub {
            font-size: 0.7rem;
            color: #64748b;
            letter-spacing: 3px;
            text-transform: uppercase;
            margin-top: 4px;
        }

        .stat-card {
            padding: 18px 20px;
            border-radius: 14px;
            background: linear-gradient(155deg, rgba(22,26,38,0.95), rgba(18,22,32,0.85));
            border: 1px solid rgba(148,163,184,0.14);
            transition: all 0.25s ease;
        }
        .stat-card:hover {
            transform: translateY(-2px);
            border-color: rgba(139,92,246,0.35);
        }
        .stat-label {
            font-size: 0.72rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }
        .stat-value {
            font-size: 1.6rem;
            font-weight: 900;
            background: linear-gradient(135deg, #c4b5fd, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1.2;
        }
        .stat-value.warn {
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stat-value.ok {
            background: linear-gradient(135deg, #34d399, #10b981);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .tx-card {
            padding: 16px 20px;
            border-radius: 14px;
            background: linear-gradient(155deg, rgba(22,26,38,0.95), rgba(18,22,32,0.85));
            border: 1px solid rgba(148,163,184,0.14);
            border-left: 4px solid #f59e0b;
            margin-bottom: 10px;
        }
        .tx-row {
            display: flex;
            justify-content: space-between;
            font-size: 0.82rem;
            color: #cbd5e1;
            margin: 3px 0;
        }
        .tx-label { color: #64748b; }
        .tx-value { font-weight: 700; color: #e2e8f0; }

        div[data-testid="stButton"] > button {
            border-radius: 10px !important;
            font-weight: 700 !important;
            transition: all 0.15s ease !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================================
# ADMIN LOGIN
# ============================================================================
def _init_admin_state():
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False


def _admin_login():
    """Admin Password Login"""
    st.markdown(
        """
        <div style="text-align:center;padding:50px 0 20px;">
            <div style="font-size:3rem;margin-bottom:10px;">🔐</div>
            <div style="font-size:1.6rem;font-weight:900;
                        background:linear-gradient(135deg,#ffffff,#fda4af,#f43f5e);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                        background-clip:text;">
                Admin Panel
            </div>
            <div style="font-size:0.72rem;color:#64748b;letter-spacing:3px;
                        text-transform:uppercase;margin-top:6px;">
                PS AI Recap · Private
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 2, 1])
    with center:
        with st.form("admin_login_form"):
            pwd = st.text_input(
                "🔑 Admin Password",
                type="password",
                placeholder="••••••••",
                key="admin_pwd_input",
            )
            submit = st.form_submit_button(
                "🚪 Login", use_container_width=True, type="primary"
            )

        if submit:
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("❌ Password မှားနေပါတယ်")


# ============================================================================
# TOP STATS BAR
# ============================================================================
def _render_stats_bar():
    """Top Stats — Today Revenue, Pending, Users, Coin"""
    try:
        conn = cs.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transactions WHERE status = 'pending'")
        pending_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transactions WHERE status = 'approved'")
        approved_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COALESCE(SUM(amount_mmk), 0) FROM transactions WHERE status = 'approved'"
        )
        total_revenue = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(coin_balance), 0) FROM users")
        total_coins = cursor.fetchone()[0]

        conn.close()
    except Exception as e:
        st.error(f"Stats error: {e}")
        return

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">👥 Users</div>
                <div class="stat-value">{total_users:,}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        warn = "warn" if pending_count > 0 else ""
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">⏳ Pending</div>
                <div class="stat-value {warn}">{pending_count:,}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">✅ Approved</div>
                <div class="stat-value ok">{approved_count:,}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">💰 Revenue (MMK)</div>
                <div class="stat-value ok">{total_revenue:,.0f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-label">🪙 Coins in System</div>
                <div class="stat-value">{total_coins:,}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================================
# RECEIPT / PAYMENT APPROVAL PANEL (TOP PRIORITY)
# ============================================================================
def _render_receipt_panel():
    """Pending Payment Approval Panel"""
    st.markdown(
        """
        <div style="font-size:1.15rem;font-weight:800;color:#e2e8f0;
                    margin:22px 0 14px;display:flex;align-items:center;gap:10px;">
            💳 Receipt Approval Panel
            <span style="font-size:0.7rem;background:linear-gradient(135deg,#f43f5e,#ec4899);
                         color:#fff;padding:3px 10px;border-radius:999px;
                         font-weight:800;letter-spacing:0.5px;">TOP PRIORITY</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        conn = cs.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT t.*, u.user_code, u.email
            FROM transactions t
            JOIN users u ON u.id = t.user_id
            WHERE t.status = 'pending'
            ORDER BY t.id ASC
            """
        )
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        st.error(f"Transactions ရယူမရ: {e}")
        return

    if not rows:
        st.success("✨ Pending Payment မရှိပါ — အားလုံး စစ်ဆေးပြီးပါပြီ")
        return

    st.caption(f"🔔 Pending: **{len(rows)}** ခု")

    for idx, row in enumerate(rows, start=1):
        tx_id = row["id"]
        user_code = row["user_code"]
        email = row["email"]
        pkg_name = row["package_name"]
        amount = row["amount_mmk"]
        coins = row["coins"]
        method = row["method"]
        ref_no = row["reference_no"]
        shot_path = row["screenshot_path"]
        created = row["created_at"]

        is_monthly = pkg_name in ("Monthly", "Monthly Subscription", "Starter")
        pkg_tag = "🌟 MONTHLY" if is_monthly else "🪙 TOP-UP"

        with st.container(border=True):
            head_col, status_col = st.columns([4, 1])

            with head_col:
                st.markdown(
                    f"""
                    <div style="font-size:1rem;font-weight:800;color:#f0f2f7;">
                        #{idx} · {user_code} · {pkg_name}
                        <span style="font-size:0.7rem;background:linear-gradient(135deg,#10b981,#06b6d4);
                                     color:#fff;padding:2px 8px;border-radius:999px;
                                     margin-left:6px;">{pkg_tag}</span>
                    </div>
                    <div style="font-size:0.75rem;color:#64748b;margin-top:2px;">
                        {email}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with status_col:
                st.markdown(
                    '<div style="text-align:right;font-size:0.72rem;'
                    'color:#f59e0b;font-weight:800;">⏳ PENDING</div>',
                    unsafe_allow_html=True,
                )

            info_col, img_col = st.columns([1, 1])

            with info_col:
                st.markdown(
                    f"""
                    <div class="tx-card" style="margin-top:10px;border-left-color:#8b5cf6;">
                        <div class="tx-row">
                            <span class="tx-label">💰 Amount</span>
                            <span class="tx-value">{amount:,} ကျပ်</span>
                        </div>
                        <div class="tx-row">
                            <span class="tx-label">🪙 Coins</span>
                            <span class="tx-value">{coins:,} Coin</span>
                        </div>
                        <div class="tx-row">
                            <span class="tx-label">💳 Method</span>
                            <span class="tx-value">{method.upper()}</span>
                        </div>
                        <div class="tx-row">
                            <span class="tx-label">🔢 Ref (last 5)</span>
                            <span class="tx-value" style="font-family:monospace;
                                       color:#10b981;letter-spacing:2px;">{ref_no}</span>
                        </div>
                        <div class="tx-row">
                            <span class="tx-label">📅 Time</span>
                            <span class="tx-value">{created}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with img_col:
                if shot_path and os.path.exists(shot_path):
                    try:
                        st.image(shot_path, caption="📸 ပြေစာ", use_container_width=True)
                    except Exception:
                        st.warning("⚠️ Screenshot ပြသ မရနိုင်ပါ")
                else:
                    st.warning("⚠️ Screenshot မရှိပါ")

            # --- Action Buttons ---
            b1, b2, b3 = st.columns([1, 1, 2])

            with b1:
                if st.button(
                    "✅ Approve",
                    key=f"approve_{tx_id}",
                    use_container_width=True,
                    type="primary",
                ):
                    _approve_transaction(tx_id, row["user_id"], coins, pkg_name)

            with b2:
                if st.button(
                    "❌ Reject",
                    key=f"reject_{tx_id}",
                    use_container_width=True,
                ):
                    _reject_transaction(tx_id)

            with b3:
                if is_monthly:
                    st.caption(
                        f"⚠️ Approve နှိပ်ရင် — **{coins} Coin** + **Monthly ၃၀ ရက်**"
                    )
                else:
                    st.caption(
                        f"⚠️ Approve နှိပ်ရင် — **{coins} Coin** ထည့်မယ်"
                    )


def _approve_transaction(tx_id: int, user_id: int, coins: int, pkg_name: str):
    """Approve Payment — Add Coin + Activate Monthly if applicable"""
    try:
        conn = cs.get_connection()
        cursor = conn.cursor()

        # Update transaction status
        cursor.execute(
            "UPDATE transactions SET status = 'approved', approved_at = CURRENT_TIMESTAMP WHERE id = ?",
            (tx_id,),
        )
        conn.commit()
        conn.close()

        # 1. Coin ထည့်
        cs.add_coins(user_id, coins, f"Payment Approved: {pkg_name}")

        # 2. Monthly ဆိုရင် — Activate
        is_monthly = pkg_name in ("Monthly", "Monthly Subscription", "Starter")
        if is_monthly:
            cs.activate_monthly(user_id, days=30)
            cs.mark_starter_purchased(user_id)
            logger.info(f"Monthly activated: user {user_id} (+30 days)")

        logger.info(f"Admin approved tx#{tx_id} — {coins} coins added to user {user_id}")
        if is_monthly:
            st.success(f"✅ Approve — {coins} Coin + Monthly ၃၀ ရက် ထည့်ပြီး")
        else:
            st.success(f"✅ Approve — {coins} Coin ထည့်ပြီး")
        st.rerun()

    except Exception as e:
        logger.error(f"Approve failed: {e}")
        st.error(f"❌ Approve မအောင်မြင်ပါ: {e}")


def _reject_transaction(tx_id: int):
    """Reject Payment"""
    try:
        conn = cs.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE transactions SET status = 'rejected' WHERE id = ?",
            (tx_id,),
        )
        conn.commit()
        conn.close()
        logger.info(f"Admin rejected tx#{tx_id}")
        st.warning("❌ Reject လိုက်ပါပြီ")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Reject မအောင်မြင်ပါ: {e}")


# ============================================================================
# USER MANAGEMENT
# ============================================================================
def _render_user_management():
    """User List + Coin Add/Remove + Subscription Status"""
    st.markdown(
        '<div style="font-size:1.15rem;font-weight:800;color:#e2e8f0;'
        'margin:22px 0 14px;">👥 User Management</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        search = st.text_input(
            "🔍 User ရှာရန် — Email / User ID",
            placeholder="PSA-1001 (သို့) test@gmail.com",
            key="admin_user_search",
        )

        try:
            conn = cs.get_connection()
            cursor = conn.cursor()
            if search:
                cursor.execute(
                    """
                    SELECT id, user_code, email, display_name, coin_balance,
                           tier, has_starter, status, created_at, last_login
                    FROM users
                    WHERE user_code LIKE ? OR email LIKE ?
                    ORDER BY id DESC
                    LIMIT 50
                    """,
                    (f"%{search}%", f"%{search}%"),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, user_code, email, display_name, coin_balance,
                           tier, has_starter, status, created_at, last_login
                    FROM users
                    ORDER BY id DESC
                    LIMIT 50
                    """
                )
            users = cursor.fetchall()
            conn.close()
        except Exception as e:
            st.error(f"Users ရယူမရ: {e}")
            return

        if not users:
            st.caption("📭 User မတွေ့ပါ")
            return

        st.caption(f"Found: **{len(users)}** users")

        for u in users:
            uid = u["id"]

            # Subscription စစ်
            sub_active = cs.is_monthly_active(uid)
            sub = cs.get_subscription_status(uid)
            days_left = sub.get("days_left", 0)
            sub_icon = "🌟" if sub_active else "🆓"
            sub_text = f"Monthly ({days_left} ရက်)" if sub_active else "Free"

            with st.expander(
                f"👤 {u['user_code']} · {u['email']} · 💰 {u['coin_balance']} Coin · {sub_icon} {sub_text}",
                expanded=False,
            ):
                c1, c2 = st.columns(2)

                with c1:
                    st.markdown(
                        f"""
                        **📋 User Info**
                        - User ID: `{u['user_code']}`
                        - Email: {u['email']}
                        - Name: {u['display_name'] or '-'}
                        - Status: **{u['status']}**
                        - {sub_icon} **Subscription: {sub_text}**
                        - Joined: {u['created_at']}
                        - Last Login: {u['last_login'] or '-'}
                        """
                    )

                with c2:
                    st.markdown(f"**💰 Coin Balance: {u['coin_balance']}**")

                    add_col, rem_col = st.columns(2)
                    with add_col:
                        add_amount = st.number_input(
                            "➕ Add Coin",
                            min_value=0,
                            max_value=100000,
                            value=0,
                            step=10,
                            key=f"add_coin_{uid}",
                        )
                        if st.button("Add", key=f"btn_add_{uid}", use_container_width=True):
                            if add_amount > 0:
                                cs.add_coins(uid, int(add_amount), "Admin Manual Add")
                                st.success(f"✅ {add_amount} Coin ထည့်ပြီး")
                                st.rerun()

                    with rem_col:
                        rem_amount = st.number_input(
                            "➖ Remove Coin",
                            min_value=0,
                            max_value=100000,
                            value=0,
                            step=10,
                            key=f"rem_coin_{uid}",
                        )
                        if st.button("Remove", key=f"btn_rem_{uid}", use_container_width=True):
                            if rem_amount > 0:
                                cs.deduct_coins(uid, int(rem_amount), "Admin Manual Remove")
                                st.warning(f"⚠️ {rem_amount} Coin ဖြတ်ပြီး")
                                st.rerun()


# ============================================================================
# RECENT ACTIVITY
# ============================================================================
def _render_recent_activity():
    """Recent Transactions"""
    st.markdown(
        '<div style="font-size:1.15rem;font-weight:800;color:#e2e8f0;'
        'margin:22px 0 14px;">📋 Recent Activity</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        try:
            conn = cs.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT t.package_name, t.amount_mmk, t.coins, t.method,
                       t.reference_no, t.status, t.created_at,
                       u.user_code, u.email
                FROM transactions t
                JOIN users u ON u.id = t.user_id
                ORDER BY t.id DESC
                LIMIT 20
                """
            )
            rows = cursor.fetchall()
            conn.close()
        except Exception as e:
            st.error(f"Activity ရယူမရ: {e}")
            return

        if not rows:
            st.caption("📭 Activity မရှိသေး")
            return

        for row in rows:
            status = row["status"]
            if status == "pending":
                icon, color = "⏳", "#f59e0b"
            elif status == "approved":
                icon, color = "✅", "#10b981"
            else:
                icon, color = "❌", "#f43f5e"

            st.markdown(
                f"""
                <div class="tx-card" style="border-left-color:{color};padding:10px 14px;">
                    <div class="tx-row">
                        <span class="tx-value">{icon} {row['user_code']} · {row['package_name']}</span>
                        <span class="tx-value" style="color:{color};">{status.upper()}</span>
                    </div>
                    <div class="tx-row">
                        <span class="tx-label">{row['email']}</span>
                        <span class="tx-label">{row['amount_mmk']:,} ကျပ် · {row['coins']} Coin · {row['created_at']}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================================
# MAIN
# ============================================================================
def main():
    _init_admin_state()

    # --- Login Gate ---
    if not st.session_state.admin_logged_in:
        _admin_login()
        return

    # --- Header ---
    hdr_left, hdr_right = st.columns([4, 1])

    with hdr_left:
        st.markdown(
            """
            <div class="admin-header">
                <div class="admin-logo">🔐</div>
                <div>
                    <div class="admin-title">PS AI Recap · Admin</div>
                    <div class="admin-sub">Control Center · v0.8.7</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with hdr_right:
        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True, key="admin_logout_btn"):
            st.session_state.admin_logged_in = False
            st.rerun()

    st.markdown("---")

    # --- Stats Bar ---
    _render_stats_bar()

    # --- Receipt Panel (TOP PRIORITY) ---
    _render_receipt_panel()

    st.markdown("---")

    # --- Tabs: Users / Activity ---
    tab_users, tab_activity = st.tabs(["👥 Users", "📋 Activity"])

    with tab_users:
        _render_user_management()

    with tab_activity:
        _render_recent_activity()

    # --- Footer ---
    st.markdown(
        '<div style="text-align:center;color:#475569;font-size:0.72rem;'
        'margin-top:40px;padding:20px 0;">'
        '🔐 Admin Panel · PS AI Recap v0.8.7 · Only for authorized personnel'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()