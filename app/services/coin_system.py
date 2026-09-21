#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
PS AI Recap — Coin System
Database + Password Hash + User Management + Subscription + Auto-Login Token
+ Password Reset Codes
"""

import os
import sqlite3
import secrets
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from loguru import logger


# ============================================================================
# DATABASE PATH
# ============================================================================
def _get_db_path() -> str:
    try:
        from app.config import config
        base = config.root_dir
    except Exception:
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    storage = os.path.join(base, "storage")
    os.makedirs(storage, exist_ok=True)
    return os.path.join(storage, "narratoai.db")


DB_PATH = _get_db_path()


# ============================================================================
# DATABASE CONNECTION
# ============================================================================
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================================
# INITIALIZE DATABASE
# ============================================================================
def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    # --- USERS TABLE ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_code TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT DEFAULT '',
            coin_balance INTEGER DEFAULT 24,
            tier TEXT DEFAULT 'free',
            has_starter BOOLEAN DEFAULT 0,
            subscription_tier TEXT DEFAULT 'free',
            subscription_expires TIMESTAMP,
            login_token TEXT DEFAULT '',
            token_expires TIMESTAMP,
            email_verified BOOLEAN DEFAULT 0,
            status TEXT DEFAULT 'active',
            telegram_id TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)

    # --- MIGRATION: subscription columns ---
    try:
        cursor.execute("SELECT subscription_expires FROM users LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_expires TIMESTAMP")
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_tier TEXT DEFAULT 'free'")
            logger.info("Migration: Added subscription columns")
        except sqlite3.OperationalError:
            pass

    # --- MIGRATION: login_token columns ---
    try:
        cursor.execute("SELECT login_token FROM users LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN login_token TEXT DEFAULT ''")
            cursor.execute("ALTER TABLE users ADD COLUMN token_expires TIMESTAMP")
            logger.info("Migration: Added login_token columns")
        except sqlite3.OperationalError:
            pass

    # --- TRANSACTIONS TABLE ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            package_name TEXT NOT NULL,
            amount_mmk INTEGER NOT NULL,
            coins INTEGER NOT NULL,
            method TEXT DEFAULT 'kbzpay',
            reference_no TEXT DEFAULT '',
            screenshot_path TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # --- MIGRATION: transactions.notified column ---
    try:
        cursor.execute("SELECT notified FROM transactions LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN notified INTEGER DEFAULT 0")
            logger.info("Migration: Added transactions.notified column")
        except sqlite3.OperationalError:
            pass

    # --- COIN USAGE TABLE ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coin_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            coins_used INTEGER NOT NULL,
            details TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # --- PASSWORD RESET CODES TABLE ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            reset_code TEXT NOT NULL,
            method TEXT DEFAULT 'telegram',
            used BOOLEAN DEFAULT 0,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()
    logger.info(f"Database initialized: {DB_PATH}")


# ============================================================================
# USER CODE GENERATOR
# ============================================================================
def _generate_user_code() -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return f"PSA-{1001 + count}"


# ============================================================================
# PASSWORD HASH
# ============================================================================
def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _check_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


# ============================================================================
# CREATE USER
# ============================================================================
def create_user(email: str, password: str, display_name: str = "") -> Dict[str, Any]:
    email = email.strip().lower()

    if not email or "@" not in email:
        return {"success": False, "error": "Email မမှန်ကန်ဘူး"}

    if not password or len(password) < 6:
        return {"success": False, "error": "Password အနည်းဆုံး ၆ လုံး လိုတယ်"}

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        return {"success": False, "error": "ဒီ Email နဲ့ အကောင့် ရှိပြီးသား"}

    user_code = _generate_user_code()
    password_hash = _hash_password(password)

    try:
        cursor.execute("""
            INSERT INTO users (user_code, email, password_hash, display_name, coin_balance)
            VALUES (?, ?, ?, ?, 24)
        """, (user_code, email, password_hash, display_name or email.split("@")[0]))

        user_id = cursor.lastrowid
        conn.commit()

        logger.info(f"User created: {user_code} ({email})")
        return {
            "success": True,
            "user_id": user_id,
            "user_code": user_code,
            "email": email,
            "coin_balance": 24,
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Signup failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ============================================================================
# LOGIN
# ============================================================================
def login_user(email: str, password: str) -> Dict[str, Any]:
    email = email.strip().lower()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return {"success": False, "error": "Email သို့ Password မှားတယ်"}

    if user["status"] != "active":
        conn.close()
        return {"success": False, "error": "Account ပိတ်ထားတယ်"}

    if not _check_password(password, user["password_hash"]):
        conn.close()
        return {"success": False, "error": "Email သို့ Password မှားတယ်"}

    cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
    conn.commit()

    is_active = _is_monthly_active_from_row(user)

    result = {
        "success": True,
        "user_id": user["id"],
        "user_code": user["user_code"],
        "email": user["email"],
        "display_name": user["display_name"],
        "coin_balance": user["coin_balance"],
        "tier": user["tier"],
        "has_starter": bool(user["has_starter"]),
        "is_monthly_active": is_active,
        "subscription_expires": user["subscription_expires"] if "subscription_expires" in user.keys() else None,
    }
    conn.close()
    logger.info(f"Login: {user['user_code']} (Monthly: {is_active})")
    return result


# ============================================================================
# 🔑 AUTO-LOGIN TOKEN
# ============================================================================
def generate_login_token(user_id: int, days: int = 30) -> str:
    """User အတွက် Auto-Login Token ဖန်တီး"""
    try:
        token = secrets.token_urlsafe(48)
        expires = datetime.now() + timedelta(days=days)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET login_token = ?, token_expires = ? WHERE id = ?",
            (token, expires.isoformat(), user_id)
        )
        conn.commit()
        conn.close()

        logger.info(f"Token generated for user {user_id} (expires in {days} days)")
        return token
    except Exception as e:
        logger.error(f"generate_login_token failed: {e}")
        return ""


def verify_login_token(token: str) -> Optional[Dict[str, Any]]:
    """Token ကို စစ်ပြီး — User Data ပြန်"""
    if not token:
        return None

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE login_token = ?",
            (token,)
        )
        user = cursor.fetchone()
        conn.close()

        if not user:
            return None

        # Token Expiry စစ်
        expires = user["token_expires"] if "token_expires" in user.keys() else None
        if expires:
            try:
                exp_dt = datetime.fromisoformat(str(expires).replace(" ", "T"))
                if exp_dt < datetime.now():
                    logger.info(f"Token expired for user {user['user_code']}")
                    return None
            except Exception:
                pass

        if user["status"] != "active":
            return None

        is_active = _is_monthly_active_from_row(user)

        return {
            "success": True,
            "user_id": user["id"],
            "user_code": user["user_code"],
            "email": user["email"],
            "display_name": user["display_name"],
            "coin_balance": user["coin_balance"],
            "tier": user["tier"],
            "has_starter": bool(user["has_starter"]),
            "is_monthly_active": is_active,
            "subscription_expires": user["subscription_expires"] if "subscription_expires" in user.keys() else None,
        }
    except Exception as e:
        logger.error(f"verify_login_token failed: {e}")
        return None


def clear_login_token(user_id: int) -> bool:
    """Logout — Token ကို ဖျက်"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET login_token = '', token_expires = NULL WHERE id = ?",
            (user_id,)
        )
        conn.commit()
        conn.close()
        logger.info(f"Token cleared for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"clear_login_token failed: {e}")
        return False


def refresh_token_expiry(user_id: int, days: int = 30) -> bool:
    """Token ရဲ့ သက်တမ်းကို ဆက်တိုး — User ဝင်တိုင်း"""
    try:
        expires = datetime.now() + timedelta(days=days)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET token_expires = ? WHERE id = ? AND login_token != ''",
            (expires.isoformat(), user_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"refresh_token_expiry failed: {e}")
        return False


# ============================================================================
# GET USER
# ============================================================================
def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


# ============================================================================
# COIN BALANCE
# ============================================================================
def get_coin_balance(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT coin_balance FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["coin_balance"] if row else 0


def add_coins(user_id: int, coins: int, reason: str = "") -> bool:
    if coins <= 0:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET coin_balance = coin_balance + ? WHERE id = ?", (coins, user_id))
        cursor.execute(
            "INSERT INTO coin_usage (user_id, action, coins_used, details) VALUES (?, ?, ?, ?)",
            (user_id, "add", -coins, reason)
        )
        conn.commit()
        logger.info(f"Added {coins} coins to user {user_id}: {reason}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Add coins failed: {e}")
        return False
    finally:
        conn.close()


def deduct_coins(user_id: int, coins: int, reason: str = "") -> bool:
    if coins <= 0:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT coin_balance FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row or row["coin_balance"] < coins:
            return False

        cursor.execute("UPDATE users SET coin_balance = coin_balance - ? WHERE id = ?", (coins, user_id))
        cursor.execute(
            "INSERT INTO coin_usage (user_id, action, coins_used, details) VALUES (?, ?, ?, ?)",
            (user_id, "spend", coins, reason)
        )
        conn.commit()
        logger.info(f"Deducted {coins} coins from user {user_id}: {reason}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Deduct coins failed: {e}")
        return False
    finally:
        conn.close()


# ============================================================================
# STARTER (Legacy)
# ============================================================================
def mark_starter_purchased(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET has_starter = 1 WHERE id = ?", (user_id,))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def has_starter(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT has_starter FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row["has_starter"]) if row else False


# ============================================================================
# 📅 MONTHLY SUBSCRIPTION
# ============================================================================
def _is_monthly_active_from_row(user_row) -> bool:
    """Row မှ monthly active စစ်"""
    try:
        expires = user_row["subscription_expires"]
        if not expires:
            return False
        exp_dt = datetime.fromisoformat(str(expires).replace(" ", "T"))
        return exp_dt > datetime.now()
    except Exception:
        return False


def is_monthly_active(user_id: int) -> bool:
    """User Monthly Active ဖြစ်/မဖြစ် စစ်"""
    user = get_user(user_id)
    if not user:
        return False
    return _is_monthly_active_from_row(user)


def activate_monthly(user_id: int, days: int = 30) -> bool:
    """Monthly Subscription Activate/Extend"""
    try:
        user = get_user(user_id)
        if not user:
            return False

        current_expires = user.get("subscription_expires")
        now = datetime.now()
        base = now

        if current_expires:
            try:
                curr_dt = datetime.fromisoformat(str(current_expires).replace(" ", "T"))
                if curr_dt > now:
                    base = curr_dt
            except Exception:
                pass

        new_expires = base + timedelta(days=days)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET subscription_expires = ?, subscription_tier = 'monthly' WHERE id = ?",
            (new_expires.isoformat(), user_id)
        )
        conn.commit()
        conn.close()

        logger.info(f"Monthly activated: user {user_id} — expires {new_expires.isoformat()}")
        return True
    except Exception as e:
        logger.error(f"activate_monthly failed: {e}")
        return False


def get_subscription_status(user_id: int) -> Dict[str, Any]:
    """Subscription Status"""
    user = get_user(user_id)
    if not user:
        return {
            "active": False,
            "tier": "free",
            "expires": None,
            "days_left": 0,
            "has_starter": False,
        }

    is_active = _is_monthly_active_from_row(user)
    expires = user.get("subscription_expires")
    days_left = 0

    if expires:
        try:
            exp_dt = datetime.fromisoformat(str(expires).replace(" ", "T"))
            delta = exp_dt - datetime.now()
            days_left = max(0, delta.days)
        except Exception:
            pass

    return {
        "active": is_active,
        "tier": user.get("subscription_tier", "free"),
        "expires": expires,
        "days_left": days_left,
        "has_starter": bool(user.get("has_starter", False)),
    }


def is_premium_user(user_id: int) -> bool:
    """Premium Features Access"""
    return is_monthly_active(user_id)


# ============================================================================
# 🎉 CELEBRATION POPUP HELPERS
# ============================================================================
def get_unnotified_approved_tx(user_id: int) -> Optional[Dict[str, Any]]:
    """Approved ဖြစ်ပြီး — User ကို မပြရသေးတဲ့ Transaction ရှာ"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, package_name, amount_mmk, coins, method,
                   reference_no, approved_at
            FROM transactions
            WHERE user_id = ?
              AND status = 'approved'
              AND (notified IS NULL OR notified = 0)
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"get_unnotified_approved_tx failed: {e}")
        return None


def mark_tx_notified(tx_id: int) -> bool:
    """Transaction ကို — Notified အဖြစ် မှတ်"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE transactions SET notified = 1 WHERE id = ?",
            (tx_id,),
        )
        conn.commit()
        conn.close()
        logger.info(f"Transaction #{tx_id} marked as notified")
        return True
    except Exception as e:
        logger.error(f"mark_tx_notified failed: {e}")
        return False


# ============================================================================
# 🔐 PASSWORD RESET CODE — NEW
# ============================================================================
def _generate_reset_code() -> str:
    """6 လုံး ဂဏန်း Reset Code ဖန်တီး"""
    return f"{secrets.randbelow(1000000):06d}"


def create_password_reset(email: str, method: str = "telegram", hours: int = 1) -> Dict[str, Any]:
    """User အတွက် Password Reset Code ဖန်တီး

    Args:
        email: User ရဲ့ Email
        method: 'telegram' | 'email' | 'admin'
        hours: Code သက်တမ်း (နာရီ)

    Returns:
        {"success": bool, "code": str, "user_id": int, "error": str}
    """
    email = email.strip().lower()

    # User ရှာ
    user = get_user_by_email(email)
    if not user:
        # Security — "Email မရှိ" လို့ မပြ
        return {"success": False, "error": "Email မှားတယ် သို့ မရှိဘူး"}

    if user.get("status") != "active":
        return {"success": False, "error": "Account ပိတ်ထားတယ်"}

    user_id = user["id"]
    code = _generate_reset_code()
    expires_at = datetime.now() + timedelta(hours=hours)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # အကောင့်ရှိပြီးသား Code တွေကို expire လုပ်
        cursor.execute(
            "UPDATE password_resets SET used = 1 WHERE user_id = ? AND used = 0",
            (user_id,)
        )

        # Code အသစ် ထည့်
        cursor.execute(
            """
            INSERT INTO password_resets (user_id, email, reset_code, method, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, email, code, method, expires_at.isoformat())
        )
        conn.commit()
        conn.close()

        logger.info(f"Reset code created for {email} via {method}")
        return {
            "success": True,
            "code": code,
            "user_id": user_id,
            "user_code": user["user_code"],
            "email": email,
            "expires_at": expires_at.isoformat(),
            "error": "",
        }
    except Exception as e:
        logger.error(f"create_password_reset failed: {e}")
        return {"success": False, "error": str(e)}


def verify_reset_code(email: str, code: str) -> Dict[str, Any]:
    """Reset Code ကို စစ်"""
    email = email.strip().lower()
    code = (code or "").strip()

    if not email or not code:
        return {"success": False, "error": "Email နဲ့ Code ဖြည့်ပါ"}

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM password_resets
            WHERE email = ? AND reset_code = ? AND used = 0
            ORDER BY id DESC
            LIMIT 1
            """,
            (email, code)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"success": False, "error": "Code မှားတယ် သို့ သက်တမ်းကုန်ပြီ"}

        # Expiry စစ်
        expires = row["expires_at"]
        try:
            exp_dt = datetime.fromisoformat(str(expires).replace(" ", "T"))
            if exp_dt < datetime.now():
                return {"success": False, "error": "Code သက်တမ်း ကုန်သွားပြီ"}
        except Exception:
            pass

        return {
            "success": True,
            "user_id": row["user_id"],
            "email": row["email"],
            "reset_id": row["id"],
            "error": "",
        }
    except Exception as e:
        logger.error(f"verify_reset_code failed: {e}")
        return {"success": False, "error": str(e)}


def reset_password_with_code(email: str, code: str, new_password: str) -> Dict[str, Any]:
    """Reset Code သုံးပြီး Password အသစ် သတ်မှတ်"""
    email = email.strip().lower()

    if not new_password or len(new_password) < 6:
        return {"success": False, "error": "Password အနည်းဆုံး ၆ လုံး လိုတယ်"}

    # Code စစ်
    verify = verify_reset_code(email, code)
    if not verify["success"]:
        return {"success": False, "error": verify["error"]}

    user_id = verify["user_id"]
    reset_id = verify["reset_id"]

    try:
        password_hash = _hash_password(new_password)

        conn = get_connection()
        cursor = conn.cursor()

        # Password အသစ်
        cursor.execute(
            "UPDATE users SET password_hash = ?, login_token = '', token_expires = NULL WHERE id = ?",
            (password_hash, user_id)
        )

        # Code ကို Used အဖြစ် မှတ်
        cursor.execute(
            "UPDATE password_resets SET used = 1 WHERE id = ?",
            (reset_id,)
        )

        conn.commit()
        conn.close()

        logger.info(f"Password reset successful: {email}")
        return {"success": True, "error": ""}
    except Exception as e:
        logger.error(f"reset_password_with_code failed: {e}")
        return {"success": False, "error": str(e)}


def set_temp_password(user_id: int, temp_password: str = "") -> Dict[str, Any]:
    """Admin မှ Temp Password သတ်မှတ်

    Args:
        user_id: User ID
        temp_password: Temp Password (ဗလာ ဆိုရင် — auto generate)

    Returns:
        {"success": bool, "temp_password": str, "error": str}
    """
    user = get_user(user_id)
    if not user:
        return {"success": False, "error": "User မတွေ့ပါ"}

    # Auto generate
    if not temp_password:
        import random
        import string
        chars = string.ascii_letters + string.digits
        temp_password = "PSARecap@" + "".join(random.choices(chars, k=6))

    try:
        password_hash = _hash_password(temp_password)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = ?, login_token = '', token_expires = NULL WHERE id = ?",
            (password_hash, user_id)
        )
        conn.commit()
        conn.close()

        logger.info(f"Temp password set for user {user['user_code']}")
        return {
            "success": True,
            "temp_password": temp_password,
            "user_code": user["user_code"],
            "email": user["email"],
            "error": "",
        }
    except Exception as e:
        logger.error(f"set_temp_password failed: {e}")
        return {"success": False, "error": str(e)}


def cleanup_expired_resets() -> int:
    """သက်တမ်းကုန်တဲ့ Reset Codes တွေ ရှင်းလင်း"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM password_resets WHERE expires_at < ? OR used = 1",
            (datetime.now().isoformat(),)
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} expired reset codes")
        return deleted
    except Exception as e:
        logger.error(f"cleanup_expired_resets failed: {e}")
        return 0


# ============================================================================
# INIT ON IMPORT
# ============================================================================
init_database()