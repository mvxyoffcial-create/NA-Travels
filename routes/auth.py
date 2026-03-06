"""
NA Travels - Authentication Routes
POST /api/auth/register
POST /api/auth/login
POST /api/auth/google
POST /api/auth/verify-email
POST /api/auth/resend-verification
POST /api/auth/forgot-password
POST /api/auth/reset-password
POST /api/auth/refresh
POST /api/auth/logout
GET  /api/auth/me
"""
import os
import requests as http_req
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from bson import ObjectId
from app import mongo, limiter
from utils.helpers import (
    hash_password, check_password, validate_password,
    verify_email_token, mongo_to_dict, now_utc
)
from utils.emails import send_verification_email, send_password_reset_email, send_welcome_email

auth_bp = Blueprint("auth", __name__)

# Token blacklist (use Redis in production for scale)
_token_blacklist = set()


def _user_payload(user):
    """Return safe user dict for JWT/response."""
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "username": user.get("username", ""),
        "full_name": user.get("full_name", ""),
        "role": user.get("role", "user"),
        "is_verified": user.get("is_verified", False),
        "avatar": user.get("avatar"),
        "auth_provider": user.get("auth_provider", "email"),
    }


# ── Register ──────────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour")
def register():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()
    username = data.get("username", "").strip().lower()

    # Validate
    if not email or not password or not full_name:
        return jsonify({"success": False, "message": "Email, password and full name are required"}), 400

    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"success": False, "message": "Invalid email address"}), 400

    valid, msg = validate_password(password)
    if not valid:
        return jsonify({"success": False, "message": msg}), 400

    if not username:
        username = email.split("@")[0]

    # Unique checks
    if mongo.db.users.find_one({"email": email}):
        return jsonify({"success": False, "message": "Email already registered"}), 409

    if mongo.db.users.find_one({"username": username}):
        username = f"{username}_{ObjectId()!s:.6}"

    user_doc = {
        "email": email,
        "username": username,
        "full_name": full_name,
        "password": hash_password(password),
        "role": "user",
        "is_verified": False,
        "auth_provider": "email",
        "avatar": None,
        "bio": "",
        "favorites": [],
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    result = mongo.db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id

    # Send verification email
    send_verification_email(email, full_name)

    return jsonify({
        "success": True,
        "message": "Registration successful! Please check your email to verify your account.",
    }), 201


# ── Login ─────────────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
@limiter.limit("20 per hour")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400

    user = mongo.db.users.find_one({"email": email})
    if not user:
        return jsonify({"success": False, "message": "Invalid email or password"}), 401

    if user.get("auth_provider") == "google":
        return jsonify({"success": False, "message": "This account uses Google sign-in. Please use Google to log in."}), 401

    if not check_password(password, user["password"]):
        return jsonify({"success": False, "message": "Invalid email or password"}), 401

    user_id = str(user["_id"])
    access_token = create_access_token(identity=user_id)
    refresh_token = create_refresh_token(identity=user_id)

    mongo.db.users.update_one({"_id": user["_id"]}, {"$set": {"last_login": now_utc()}})

    return jsonify({
        "success": True,
        "message": "Login successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": _user_payload(user),
    })


# ── Google OAuth ──────────────────────────────────────────────────────────────
@auth_bp.route("/google", methods=["POST"])
@limiter.limit("20 per hour")
def google_auth():
    """Exchange Google ID token for NA Travels JWT."""
    data = request.get_json(silent=True) or {}
    id_token = data.get("id_token") or data.get("credential")

    if not id_token:
        return jsonify({"success": False, "message": "Google ID token required"}), 400

    # Verify with Google
    try:
        resp = http_req.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=10,
        )
        if resp.status_code != 200:
            return jsonify({"success": False, "message": "Invalid Google token"}), 401

        google_data = resp.json()
        client_id = current_app.config.get("GOOGLE_CLIENT_ID")
        if client_id and google_data.get("aud") != client_id:
            return jsonify({"success": False, "message": "Token audience mismatch"}), 401

        google_email = google_data.get("email", "").lower()
        google_name = google_data.get("name", "")
        google_picture = google_data.get("picture", "")
        google_id = google_data.get("sub")

    except Exception as e:
        current_app.logger.error(f"Google auth error: {e}")
        return jsonify({"success": False, "message": "Failed to verify Google token"}), 500

    # Find or create user
    user = mongo.db.users.find_one({"email": google_email})
    if not user:
        username = google_email.split("@")[0]
        if mongo.db.users.find_one({"username": username}):
            username = f"{username}_{google_id[:6]}"

        user_doc = {
            "email": google_email,
            "username": username,
            "full_name": google_name,
            "password": None,
            "role": "user",
            "is_verified": True,  # Google already verified email
            "auth_provider": "google",
            "google_id": google_id,
            "avatar": google_picture,
            "bio": "",
            "favorites": [],
            "created_at": now_utc(),
            "updated_at": now_utc(),
        }
        result = mongo.db.users.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id
        user = user_doc

        # Send welcome email
        send_welcome_email(google_email, google_name)
    else:
        mongo.db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": now_utc(), "google_id": google_id}}
        )

    user_id = str(user["_id"])
    access_token = create_access_token(identity=user_id)
    refresh_token = create_refresh_token(identity=user_id)

    return jsonify({
        "success": True,
        "message": "Google login successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": _user_payload(user),
    })


# ── Verify Email ──────────────────────────────────────────────────────────────
@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()

    if not token:
        return jsonify({"success": False, "message": "Token is required"}), 400

    email = verify_email_token(token, salt="email-verify", max_age=86400)
    if not email:
        return jsonify({"success": False, "message": "Invalid or expired verification link. Please request a new one."}), 400

    user = mongo.db.users.find_one({"email": email})
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    if user.get("is_verified"):
        return jsonify({"success": True, "message": "Email already verified. You can log in."}), 200

    mongo.db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"is_verified": True, "updated_at": now_utc()}}
    )

    send_welcome_email(email, user.get("full_name", "Traveller"))

    return jsonify({"success": True, "message": "Email verified successfully! You can now log in."})


# ── Resend Verification ───────────────────────────────────────────────────────
@auth_bp.route("/resend-verification", methods=["POST"])
@limiter.limit("5 per hour")
def resend_verification():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"success": False, "message": "Email is required"}), 400

    user = mongo.db.users.find_one({"email": email})
    # Always return success to prevent email enumeration
    if user and not user.get("is_verified") and user.get("auth_provider") == "email":
        send_verification_email(email, user.get("full_name", "Traveller"))

    return jsonify({"success": True, "message": "If that email exists and is unverified, we've sent a new verification link."})


# ── Forgot Password ───────────────────────────────────────────────────────────
@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per hour")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"success": False, "message": "Email is required"}), 400

    user = mongo.db.users.find_one({"email": email})
    if user and user.get("auth_provider") == "email":
        send_password_reset_email(email, user.get("full_name", "Traveller"))

    return jsonify({"success": True, "message": "If that email is registered, you'll receive a password reset link shortly."})


# ── Reset Password ────────────────────────────────────────────────────────────
@auth_bp.route("/reset-password", methods=["POST"])
@limiter.limit("10 per hour")
def reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()
    new_password = data.get("password", "")

    if not token or not new_password:
        return jsonify({"success": False, "message": "Token and new password are required"}), 400

    valid, msg = validate_password(new_password)
    if not valid:
        return jsonify({"success": False, "message": msg}), 400

    email = verify_email_token(token, salt="password-reset", max_age=3600)
    if not email:
        return jsonify({"success": False, "message": "Invalid or expired reset link. Please request a new one."}), 400

    user = mongo.db.users.find_one({"email": email})
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    mongo.db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password": hash_password(new_password), "updated_at": now_utc()}}
    )

    return jsonify({"success": True, "message": "Password reset successfully. You can now log in."})


# ── Refresh Token ─────────────────────────────────────────────────────────────
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    access_token = create_access_token(identity=user_id)
    return jsonify({"success": True, "access_token": access_token})


# ── Logout ────────────────────────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    _token_blacklist.add(jti)
    return jsonify({"success": True, "message": "Logged out successfully"})


# ── Me ────────────────────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    return jsonify({"success": True, "user": _user_payload(user)})
