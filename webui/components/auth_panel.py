#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
PS AI Recap — Authentication Panel
Login / Signup UI + Cookie Auto-Login + Forgot Password
"""

import streamlit as st
import streamlit.components.v1 as components
from app.services import coin_system as cs

# ============================================================================
# CONFIG
# ============================================================================
COOKIE_NAME = "psai_token"
COOKIE_DAYS = 90

ADMIN_TELEGRAM = "@Ps2005b"

# ============================================================================
# COOKIE — SET/DELETE via JS Injection
# ============================================================================
def _set_cookie_js(key: str, value: str, days: int = COOKIE_DAYS):
    max_age = days * 86400
    safe_val = value.replace("\\", "\\\\").replace('"', '\\"')
    try:
        components.html(
            f"""
            <script>
                (function() {{
                    try {{
                        var cookieStr = "{key}=" + encodeURIComponent("{safe_val}")
                            + "; path=/; max-age={max_age}; SameSite=Lax";
                        window.parent.document.cookie = cookieStr;
                    }} catch(e) {{}}
                }})();
            </script>
            """,
            height=0,
        )
    except Exception:
        pass

def _clear_cookie_js(key: str):
    try:
        components.html(
            f"""
            <script>
                (function() {{
                    try {{
                        window.parent.document.cookie = "{key}=; path=/; max-age=0;";
                    }} catch(e) {{}}
                }})();
            </script>
            """,
            height=0,
        )
    except Exception:
        pass

# ============================================================================
# COOKIE — READ via st.context.cookies
# ============================================================================
def _get_cookie(key: str) -> str:
    try:
        cookies = st.context.cookies
        if cookies:
            val = cookies.get(key, "")
            return val or ""
    except Exception:
        pass
    return ""

# ============================================================================
# HIDE JS IFRAME
# ============================================================================
def _hide_iframes():
    st.markdown(
        """
        <style>
            iframe[title*="streamlit_components"],
            div[data-testid="stCustomComponentV1"] {
                position: fixed !important;
                left: -9999px !important;
                top: -9999px !important;
                width: 1px !important;
                height: 1px !important;
                opacity: 0.01 !important;
                pointer-events: none !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ============================================================================
# SESSION STATE + AUTO LOGIN
# ============================================================================
def _init_auth_state():
    _hide_iframes()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "user_code" not in st.session_state:
        st.session_state.user_code = ""
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    if "user_tier" not in st.session_state:
        st.session_state.user_tier = "free"
    if "has_starter" not in st.session_state:
        st.session_state.has_starter = False

    if "show_forgot" not in st.session_state:
        st.session_state.show_forgot = False
    if "forgot_step" not in st.session_state:
        st.session_state.forgot_step = 1
    if "forgot_email" not in st.session_state:
        st.session_state.forgot_email = ""

    # --- Auto Login — Cookie စစ် ---
    if not st.session_state.logged_in:
        token = _get_cookie(COOKIE_NAME)
        if token:
            last_checked = st.session_state.get("_last_token_checked", "")
            if token != last_checked:
                st.session_state["_last_token_checked"] = token
                try:
                    user_data = cs.verify_login_token(token)
                    if user_data and user_data.get("success"):
                        _apply_user_data(user_data)
                        try:
                            cs.refresh_token_expiry(user_data["user_id"], days=COOKIE_DAYS)
                        except Exception:
                            pass
                except Exception:
                    pass

def _apply_user_data(user_data):
    st.session_state.logged_in = True
    st.session_state.user_id = user_data["user_id"]
    st.session_state.user_code = user_data["user_code"]
    st.session_state.user_email = user_data["email"]
    st.session_state.user_tier = user_data.get("tier", "free")
    st.session_state.has_starter = user_data.get("has_starter", False)

def _do_login(user_data):
    _apply_user_data(user_data)
    try:
        token = cs.generate_login_token(user_data["user_id"], days=COOKIE_DAYS)
        if token:
            _set_cookie_js(COOKIE_NAME, token, days=COOKIE_DAYS)
            st.session_state["_last_token_checked"] = token
    except Exception:
        pass

def logout():
    user_id = st.session_state.get("user_id")
    if user_id:
        try:
            cs.clear_login_token(user_id)
        except Exception:
            pass
    _clear_cookie_js(COOKIE_NAME)
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_code = ""
    st.session_state.user_email = ""
    st.session_state.user_tier = "free"
    st.session_state.has_starter = False
    st.session_state["_last_token_checked"] = ""

# ============================================================================
# FORGOT PASSWORD — 3 OPTIONS
# ============================================================================
def _render_forgot_password():
    """Forgot Password Page — ၃ လမ်း"""
    st.markdown(
        """
        <div style="text-align:center;padding:20px 0 10px;">
            <div style="font-size:2.5rem;margin-bottom:8px;">🔐</div>
            <div style="font-size:1.6rem;font-weight:800;color:#e2e8f0;">
                Password ပြန်လည် သတ်မှတ်
            </div>
            <div style="font-size:0.82rem;color:#94a3b8;margin-top:6px;">
                သင့်အတွက် အဆင်ပြေတဲ့ နည်းလမ်း ရွေးပါ
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 2, 1])
    with center:
        # --- Option Tabs ---
        tab_telegram, tab_email, tab_admin = st.tabs([
            "📱 Telegram", "📧 Email", "🆘 Admin"
        ])

        # ====================================================================
        # OPTION 1: TELEGRAM
        # ====================================================================
        with tab_telegram:
            st.markdown("##### 📱 Telegram Bot မှ Reset")

            # --- Step 1: Email ထည့် ---
            if st.session_state.forgot_step == 1:
                st.info(
                    "💡 **အဆင့် ၁** — Email ထည့်ပါ\n\n"
                    "ပြီးရင် Telegram Bot (`@PSAI_Recap_Bot`) မှာ "
                    "`/reset` နှိပ်ပြီး Code ရယူပါ။"
                )

                with st.form("forgot_email_form"):
                    email = st.text_input(
                        "📧 Email",
                        placeholder="your@email.com",
                        key="forgot_email_input",
                    )
                    submitted = st.form_submit_button(
                        "➡️ ဆက်လုပ်",
                        use_container_width=True,
                        type="primary",
                    )

                if submitted:
                    if not email or "@" not in email:
                        st.error("⚠️ Email မှန်ကန်စွာ ဖြည့်ပါ")
                    else:
                        user = cs.get_user_by_email(email)
                        if user:
                            st.session_state.forgot_email = email.strip().lower()
                            st.session_state.forgot_step = 2
                            st.rerun()
                        else:
                            st.error("❌ ဒီ Email နဲ့ အကောင့် မရှိပါ")

            # --- Step 2: Code + Password အသစ် ---
            elif st.session_state.forgot_step == 2:
                st.success(
                    f"✅ Email — `{st.session_state.forgot_email}`\n\n"
                    "အခု Telegram Bot ကနေ Code ယူပြီး အောက်မှာ ထည့်ပါ။"
                )

                st.markdown(
                    f"""
                    <div style="padding:14px 18px;border-radius:10px;
                    background:linear-gradient(135deg,rgba(6,182,212,0.15),rgba(139,92,246,0.08));
                    border:1px solid rgba(6,182,212,0.4);margin:10px 0;">
                    <div style="font-size:0.85rem;color:#67e8f9;font-weight:700;
                    margin-bottom:6px;">📱 Telegram မှ Code ယူနည်း —</div>
                    <div style="font-size:0.82rem;color:#cbd5e1;line-height:1.9;">
                    ၁။ Telegram ဖွင့်ပါ<br>
                    ၂။ <b>@{ADMIN_TELEGRAM}</b> မဟုတ် —
                    <b>@PSAI_Recap_Bot</b> ကို ရှာပါ<br>
                    ၃။ <code>/reset</code> နှိပ်ပါ<br>
                    ၄။ Email ပို့ပါ<br>
                    ၅။ 6 လုံး Code ရမယ်
                    </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                with st.form("forgot_reset_form"):
                    code = st.text_input(
                        "🔐 Reset Code (6 လုံး)",
                        placeholder="123456",
                        max_chars=6,
                        key="forgot_code_input",
                    )
                    new_password = st.text_input(
                        "🔒 Password အသစ်",
                        type="password",
                        placeholder="အနည်းဆုံး ၆ လုံး",
                        key="forgot_new_pwd_input",
                    )
                    new_password2 = st.text_input(
                        "🔒 Password အသစ် ထပ်ရိုက်ပါ",
                        type="password",
                        placeholder="••••••••",
                        key="forgot_new_pwd2_input",
                    )

                    col_submit, col_back = st.columns([2, 1])
                    with col_submit:
                        reset_submit = st.form_submit_button(
                            "✅ Password အသစ် သတ်မှတ်",
                            use_container_width=True,
                            type="primary",
                        )
                    with col_back:
                        back_submit = st.form_submit_button(
                            "⬅️ နောက်သို့",
                            use_container_width=True,
                        )

                if back_submit:
                    st.session_state.forgot_step = 1
                    st.session_state.forgot_email = ""
                    st.rerun()

                if reset_submit:
                    if not code or len(code) != 6:
                        st.error("⚠️ Code — ၆ လုံး ဖြည့်ပါ")
                    elif not new_password or len(new_password) < 6:
                        st.error("⚠️ Password အနည်းဆုံး ၆ လုံး လိုတယ်")
                    elif new_password != new_password2:
                        st.error("⚠️ Password နှစ်ခု မတူဘူး")
                    else:
                        with st.spinner("စစ်ဆေးနေတယ်..."):
                            result = cs.reset_password_with_code(
                                st.session_state.forgot_email,
                                code.strip(),
                                new_password,
                            )

                        if result["success"]:
                            st.success("✅ Password အသစ် သတ်မှတ်ပြီးပါပြီ!")
                            st.info("👉 Login Tab ကို သွားပြီး Password အသစ်နဲ့ ဝင်ပါ")
                            st.session_state.forgot_step = 1
                            st.session_state.forgot_email = ""
                        else:
                            st.error(f"❌ {result['error']}")

        # ====================================================================
        # OPTION 2: EMAIL
        # ====================================================================
        with tab_email:
            st.markdown("##### 📧 Email မှ Reset")

            st.markdown(
                """
                <div style="padding:16px 20px;border-radius:12px;
                background:rgba(245,158,11,0.1);
                border:1px solid rgba(245,158,11,0.4);margin:10px 0;">
                <div style="font-size:0.95rem;color:#fbbf24;font-weight:800;
                margin-bottom:8px;">⚠️ လောလောဆယ် မရနိုင်သေးပါ</div>
                <div style="font-size:0.82rem;color:#cbd5e1;line-height:1.9;">
                📧 Email Reset Service ကို — <b>မကြာမီ</b> ထည့်ပေးပါမယ်။<br><br>
                🙏 အခုလောလောဆယ် — <b style="color:#67e8f9;">Telegram</b> သို့မဟုတ်
                <b style="color:#67e8f9;">Admin</b> ကို သုံးပါ။
                </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ====================================================================
        # OPTION 3: ADMIN
        # ====================================================================
        with tab_admin:
            st.markdown("##### 🆘 Admin ကို ဆက်သွယ်")

            st.markdown(
                f"""
                <div style="padding:18px 22px;border-radius:14px;
                background:linear-gradient(135deg,rgba(244,63,94,0.12),rgba(236,72,153,0.08));
                border:1px solid rgba(244,63,94,0.4);margin:10px 0;">
                <div style="font-size:1.05rem;color:#fb7185;font-weight:800;
                margin-bottom:12px;">📞 Admin — @Ps2005b</div>
                <div style="font-size:0.85rem;color:#cbd5e1;line-height:1.9;">
                <b>Admin ကို ဆက်သွယ်ပြီး ပြောပါ —</b><br><br>
                ၁။ သင့် <b style="color:#67e8f9;">Email</b><br>
                ၂။ သင့် <b style="color:#67e8f9;">User ID</b> (သိရင်)<br>
                ၃။ ပြဿနာ ရှင်းလင်းချက်<br><br>
                Admin က သင့်ကို <b style="color:#34d399;">Temp Password</b>
                ပေးပါလိမ့်မယ်။
                </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f'<a href="https://t.me/Ps2005b" target="_blank" '
                f'style="display:block;text-align:center;padding:14px;'
                f'border-radius:12px;text-decoration:none;'
                f'background:linear-gradient(135deg,#0088cc,#006699);'
                f'color:white;font-weight:800;font-size:1rem;margin-top:10px;">'
                f'📱 Telegram — @Ps2005b ကို ဆက်သွယ်</a>',
                unsafe_allow_html=True,
            )

        # --- Back to Login ---
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⬅️ Login သို့ ပြန်သွား", key="back_to_login_btn", use_container_width=True):
            st.session_state.show_forgot = False
            st.session_state.forgot_step = 1
            st.session_state.forgot_email = ""
            st.rerun()

# ============================================================================
# AUTH PAGE
# ============================================================================
def render_auth_page(tr=None):
    """Render Login/Signup page OR Forgot Password"""
    _init_auth_state()

    # --- Forgot Password Page ---
    if st.session_state.get("show_forgot"):
        _render_forgot_password()
        return

    # --- Normal Auth Page ---
    st.markdown(
        """
        <div style="text-align:center;padding:40px 0 20px;">
            <div style="font-size:3.5rem;margin-bottom:10px;">🎬</div>
            <div style="font-size:2.2rem;font-weight:900;
                        background:linear-gradient(135deg,#ffffff,#c4b5fd,#8b5cf6);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                        background-clip:text;margin-bottom:6px;">
                PS AI Recap
            </div>
            <div style="font-size:0.75rem;font-weight:600;letter-spacing:3px;
                        color:#64748b;text-transform:uppercase;">
                Movie Recap Studio
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 2, 1])
    with center:
        tab_login, tab_signup = st.tabs(["🔐 Login", "✨ Signup"])

        with tab_login:
            st.markdown("##### အကောင့် ဝင်ရန်")

            with st.form("login_form", clear_on_submit=False):
                login_email = st.text_input(
                    "📧 Email",
                    placeholder="your@email.com",
                    key="login_email_input",
                )
                login_password = st.text_input(
                    "🔒 Password",
                    type="password",
                    placeholder="••••••••",
                    key="login_password_input",
                )
                login_submit = st.form_submit_button(
                    "🔐 Login",
                    use_container_width=True,
                    type="primary",
                )

            # --- Forgot Password Button ---
            if st.button("🔑 Password မေ့သွားလား?", key="forgot_pwd_btn",
                         use_container_width=True):
                st.session_state.show_forgot = True
                st.session_state.forgot_step = 1
                st.session_state.forgot_email = ""
                st.rerun()

            if login_submit:
                if not login_email or not login_password:
                    st.error("⚠️ Email နှင့် Password ဖြည့်ပါ")
                else:
                    with st.spinner("စစ်ဆေးနေတယ်..."):
                        result = cs.login_user(login_email, login_password)

                    if result["success"]:
                        _do_login(result)
                        st.success(f"✅ ကြိုဆိုပါတယ် {result['user_code']}!")
                        st.rerun()
                    else:
                        st.error(f"❌ {result['error']}")

            st.markdown(
                '<div style="text-align:center;margin-top:14px;'
                'font-size:0.78rem;color:#64748b;">'
                '💾 Login ဝင်ပြီးရင် — ၉၀ ရက် အတွင်း — Password ထပ် ရိုက်ရမှာ မဟုတ်ပါ'
                '</div>',
                unsafe_allow_html=True,
            )

        with tab_signup:
            st.markdown("##### အကောင့် အသစ် ဖွင့်ရန်")
            st.caption("🎁 Signup လုပ်ရင် — **၂၄ Coin အခမဲ့** ရမယ်")

            with st.form("signup_form", clear_on_submit=False):
                signup_email = st.text_input(
                    "📧 Email",
                    placeholder="your@email.com",
                    key="signup_email_input",
                )
                signup_name = st.text_input(
                    "👤 နာမည် (Optional)",
                    placeholder="Your Name",
                    key="signup_name_input",
                )
                signup_password = st.text_input(
                    "🔒 Password",
                    type="password",
                    placeholder="အနည်းဆုံး ၆ လုံး",
                    key="signup_password_input",
                )
                signup_password2 = st.text_input(
                    "🔒 Password ထပ်ရိုက်ပါ",
                    type="password",
                    placeholder="••••••••",
                    key="signup_password2_input",
                )
                signup_submit = st.form_submit_button(
                    "✨ Signup",
                    use_container_width=True,
                    type="primary",
                )

            if signup_submit:
                if not signup_email or not signup_password:
                    st.error("⚠️ Email နှင့် Password ဖြည့်ပါ")
                elif signup_password != signup_password2:
                    st.error("⚠️ Password နှစ်ခု မတူဘူး")
                elif len(signup_password) < 6:
                    st.error("⚠️ Password အနည်းဆုံး ၆ လုံး လိုတယ်")
                else:
                    with st.spinner("အကောင့် ဖန်တီးနေတယ်..."):
                        result = cs.create_user(
                            signup_email,
                            signup_password,
                            signup_name,
                        )

                    if result["success"]:
                        st.success(
                            f"✅ အကောင့် ဖွင့်ပြီးပါပြီ! "
                            f"သင့် ID: **{result['user_code']}** · "
                            f"🎁 **၂၄ Coin** ရပါပြီ"
                        )
                        st.info("👉 **Login** tab ကို သွားပြီး ဝင်ပါ")
                    else:
                        st.error(f"❌ {result['error']}")

        st.markdown(
            '<div style="text-align:center;margin-top:30px;'
            'font-size:0.72rem;color:#475569;">'
            'PS AI Recap v0.8.7 · Powered by NarratoAI'
            '</div>',
            unsafe_allow_html=True,
        )

# ============================================================================
# GATE
# ============================================================================
def require_login(tr=None) -> bool:
    _init_auth_state()
    if not st.session_state.logged_in:
        render_auth_page(tr)
        return False
    return True

def is_logged_in() -> bool:
    _init_auth_state()
    return bool(st.session_state.logged_in)

def get_current_user_id():
    _init_auth_state()
    return st.session_state.user_id

def get_current_user_code() -> str:
    _init_auth_state()
    return st.session_state.user_code