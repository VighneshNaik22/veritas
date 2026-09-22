import hashlib
import hmac
import logging
import os
import secrets
import smtplib
import sqlite3
import time
from email.message import EmailMessage

from db.connection import DB_PATH

OTP_TTL_SECONDS = 300
REQUEST_WINDOW_SECONDS = 900
MAX_REQUESTS_PER_WINDOW = 3
MAX_VERIFY_ATTEMPTS = 5
SESSION_TTL_SECONDS = 3600
OTP_PEPPER = (
    os.environ["VERITAS_OTP_PEPPER"].encode()
    if os.environ.get("VERITAS_OTP_PEPPER")
    else secrets.token_bytes(32)
)
DEV_MODE = os.environ.get("VERITAS_AUTH_DEV_MODE", "1").lower() in {"1", "true", "yes"}
logger = logging.getLogger("veritas.auth")


def _connect():
    return sqlite3.connect(DB_PATH)


def _hash_otp(otp):
    return hmac.new(OTP_PEPPER, otp.encode(), hashlib.sha256).hexdigest()


def _ensure_auth_schema(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS otp_challenges (
            challenge_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            otp_hash TEXT NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            used_at REAL,
            request_ip TEXT NOT NULL
        );
        """
    )
    demo_email = os.environ.get("VERITAS_DEMO_EMAIL", "demo@example.com").strip().lower()
    conn.execute(
        "UPDATE users SET email=? WHERE user_id=?",
        (demo_email, "demo-user"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, email, created_at) VALUES (?, ?, ?)",
        ("demo-user", demo_email, time.time()),
    )
    conn.commit()


def _send_otp(email, otp):
    if DEV_MODE:
        logger.warning("DEV ONLY OTP for %s: %s", email, otp)
        return "dev"

    host = os.environ.get("VERITAS_SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("VERITAS_SMTP_PORT", "587"))
    username = os.environ.get("VERITAS_SMTP_USER")
    password = os.environ.get("VERITAS_SMTP_PASSWORD")
    sender = os.environ.get("VERITAS_SMTP_FROM", username)
    if host:
        if not username or not password or not sender:
            raise RuntimeError(
                "SMTP configuration requires VERITAS_SMTP_USER, "
                "VERITAS_SMTP_PASSWORD, and VERITAS_SMTP_FROM or "
                "VERITAS_SMTP_USER"
            )
        message = EmailMessage()
        message["Subject"] = "Your VERITAS login code"
        message["From"] = sender
        message["To"] = email
        message.set_content(
            f"Your VERITAS login code is {otp}. It expires in five minutes."
        )
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(message)
        logger.info("OTP email sent via SMTP host=%s port=%s from=%s", host, port, sender)
        return "smtp"


def request_otp(email, request_ip):
    normalized = email.strip().lower()
    now = time.time()
    conn = _connect()
    try:
        _ensure_auth_schema(conn)
        user = conn.execute(
            "SELECT user_id FROM users WHERE email=?", (normalized,)
        ).fetchone()
        recent = conn.execute(
            "SELECT COUNT(*) FROM otp_challenges "
            "WHERE request_ip=? AND created_at>? ",
            (request_ip, now - REQUEST_WINDOW_SECONDS),
        ).fetchone()[0]
        if recent >= MAX_REQUESTS_PER_WINDOW:
            return False, "If the account is eligible, try again later."
        if not user:
            user_id = "user-" + secrets.token_urlsafe(18)
            conn.execute(
                "INSERT INTO users (user_id, email, created_at) VALUES (?, ?, ?)",
                (user_id, normalized, now),
            )
            user = (user_id,)
        otp = f"{secrets.randbelow(1_000_000):06d}"
        challenge_id = secrets.token_urlsafe(24)
        conn.execute(
            "INSERT INTO otp_challenges "
            "(challenge_id,user_id,otp_hash,created_at,expires_at,request_ip) "
            "VALUES (?,?,?,?,?,?)",
            (
                challenge_id,
                user[0],
                _hash_otp(otp),
                now,
                now + OTP_TTL_SECONDS,
                request_ip,
            ),
        )
        conn.commit()
        try:
            _send_otp(normalized, otp)
        except (OSError, RuntimeError, smtplib.SMTPException, TimeoutError):
            logger.exception("OTP delivery failed")
            conn.execute(
                "DELETE FROM otp_challenges WHERE challenge_id=?",
                (challenge_id,),
            )
            conn.commit()
            return True, "If the account is eligible, a code has been sent."
        return True, "If the account is eligible, a code has been sent."
    finally:
        conn.close()


def verify_otp(email, otp, request_ip):
    if not isinstance(email, str) or not isinstance(otp, str):
        return None, "Invalid or expired code."
    normalized = email.strip().lower()
    now = time.time()
    conn = _connect()
    try:
        _ensure_auth_schema(conn)
        row = conn.execute(
            "SELECT c.challenge_id, c.otp_hash, c.expires_at, c.attempts, c.used_at "
            "FROM otp_challenges c JOIN users u ON u.user_id=c.user_id "
            "WHERE u.email=? AND c.request_ip=? ORDER BY c.created_at DESC LIMIT 1",
            (normalized, request_ip),
        ).fetchone()
        if not row:
            return None, "Invalid or expired code."
        challenge_id, otp_hash, expires_at, attempts, used_at = row
        if used_at or expires_at <= now or attempts >= MAX_VERIFY_ATTEMPTS:
            return None, "Invalid or expired code."
        conn.execute(
            "UPDATE otp_challenges SET attempts=attempts+1 WHERE challenge_id=?",
            (challenge_id,),
        )
        if not hmac.compare_digest(otp_hash, _hash_otp(otp.strip())):
            conn.commit()
            return None, "Invalid or expired code."
        conn.execute(
            "UPDATE otp_challenges SET used_at=? WHERE challenge_id=?",
            (now, challenge_id),
        )
        conn.commit()
        return secrets.token_urlsafe(32), None
    finally:
        conn.close()
