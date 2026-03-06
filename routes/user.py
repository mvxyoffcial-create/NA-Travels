"""
NA Travels - User Profile Routes
GET    /api/user/profile
PUT    /api/user/profile
POST   /api/user/avatar
DELETE /api/user/avatar
POST   /api/user/change-password
GET    /api/user/favorites
POST   /api/user/favorites/:destination_id
DELETE /api/user/favorites/:destination_id
GET    /api/user/reviews
GET    /api/user/:username  (public profile)
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from app import mongo
from utils.helpers import (
    check_password, hash_password, validate_password,
    save_image, delete_image, mongo_to_dict, now_utc
)

user_bp = Blueprint("user", __name__)


def _safe_user(user):
    """Return safe user dict (no password)."""
    d = mongo_to_dict(user)
    d.pop("password", None)
    return d


# ── Get Profile ───────────────────────────────────────────────────────────────
@user_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    return jsonify({"success": True, "user": _safe_user(user)})


# ── Update Profile ────────────────────────────────────────────────────────────
@user_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    allowed = ["full_name", "bio", "phone", "country", "website", "social_links"]
    updates = {k: data[k] for k in allowed if k in data}

    if not updates:
        return jsonify({"success": False, "message": "No valid fields to update"}), 400

    # Validate username change
    if "username" in data:
        new_username = data["username"].strip().lower()
        if new_username:
            existing = mongo.db.users.find_one({"username": new_username, "_id": {"$ne": ObjectId(user_id)}})
            if existing:
                return jsonify({"success": False, "message": "Username already taken"}), 409
            updates["username"] = new_username

    updates["updated_at"] = now_utc()
    mongo.db.users.update_one({"_id": ObjectId(user_id)}, {"$set": updates})

    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    return jsonify({"success": True, "message": "Profile updated", "user": _safe_user(user)})


# ── Upload Avatar ─────────────────────────────────────────────────────────────
@user_bp.route("/avatar", methods=["POST"])
@jwt_required()
def upload_avatar():
    user_id = get_jwt_identity()
    if "avatar" not in request.files:
        return jsonify({"success": False, "message": "No file provided"}), 400

    file = request.files["avatar"]
    path = save_image(file, "avatars", max_size=(400, 400))
    if not path:
        return jsonify({"success": False, "message": "Invalid image file. Allowed: JPG, PNG, GIF, WEBP"}), 400

    # Delete old avatar
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if user and user.get("avatar") and not user["avatar"].startswith("http"):
        delete_image(user["avatar"])

    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"avatar": f"/{path}", "updated_at": now_utc()}}
    )
    return jsonify({"success": True, "message": "Avatar updated", "avatar": f"/{path}"})


# ── Delete Avatar ─────────────────────────────────────────────────────────────
@user_bp.route("/avatar", methods=["DELETE"])
@jwt_required()
def delete_avatar():
    user_id = get_jwt_identity()
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if user and user.get("avatar") and not user["avatar"].startswith("http"):
        delete_image(user["avatar"].lstrip("/"))

    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"avatar": None, "updated_at": now_utc()}}
    )
    return jsonify({"success": True, "message": "Avatar removed"})


# ── Change Password ───────────────────────────────────────────────────────────
@user_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not current_password or not new_password:
        return jsonify({"success": False, "message": "Both current and new password required"}), 400

    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user or user.get("auth_provider") == "google":
        return jsonify({"success": False, "message": "Cannot change password for Google accounts"}), 400

    if not check_password(current_password, user["password"]):
        return jsonify({"success": False, "message": "Current password is incorrect"}), 401

    valid, msg = validate_password(new_password)
    if not valid:
        return jsonify({"success": False, "message": msg}), 400

    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password": hash_password(new_password), "updated_at": now_utc()}}
    )
    return jsonify({"success": True, "message": "Password changed successfully"})


# ── Favorites ─────────────────────────────────────────────────────────────────
@user_bp.route("/favorites", methods=["GET"])
@jwt_required()
def get_favorites():
    user_id = get_jwt_identity()
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)}, {"favorites": 1})
    favorites_ids = [ObjectId(fid) for fid in (user.get("favorites") or []) if ObjectId.is_valid(fid)]
    destinations = list(mongo.db.destinations.find({"_id": {"$in": favorites_ids}}))
    return jsonify({"success": True, "favorites": mongo_to_dict(destinations)})


@user_bp.route("/favorites/<destination_id>", methods=["POST"])
@jwt_required()
def add_favorite(destination_id):
    user_id = get_jwt_identity()
    if not ObjectId.is_valid(destination_id):
        return jsonify({"success": False, "message": "Invalid destination ID"}), 400

    dest = mongo.db.destinations.find_one({"_id": ObjectId(destination_id)})
    if not dest:
        return jsonify({"success": False, "message": "Destination not found"}), 404

    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$addToSet": {"favorites": destination_id}}
    )
    return jsonify({"success": True, "message": "Added to favorites"})


@user_bp.route("/favorites/<destination_id>", methods=["DELETE"])
@jwt_required()
def remove_favorite(destination_id):
    user_id = get_jwt_identity()
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"favorites": destination_id}}
    )
    return jsonify({"success": True, "message": "Removed from favorites"})


# ── User's Reviews ────────────────────────────────────────────────────────────
@user_bp.route("/reviews", methods=["GET"])
@jwt_required()
def get_my_reviews():
    user_id = get_jwt_identity()
    reviews = list(mongo.db.reviews.find({"user_id": user_id}).sort("created_at", -1))
    return jsonify({"success": True, "reviews": mongo_to_dict(reviews), "total": len(reviews)})


# ── Public Profile ────────────────────────────────────────────────────────────
@user_bp.route("/<username>", methods=["GET"])
def get_public_profile(username):
    user = mongo.db.users.find_one({"username": username.lower()})
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    public_data = {
        "username": user.get("username"),
        "full_name": user.get("full_name"),
        "avatar": user.get("avatar"),
        "bio": user.get("bio"),
        "country": user.get("country"),
        "created_at": user.get("created_at"),
    }
    review_count = mongo.db.reviews.count_documents({"user_id": str(user["_id"])})
    public_data["review_count"] = review_count

    return jsonify({"success": True, "user": mongo_to_dict(public_data)})
