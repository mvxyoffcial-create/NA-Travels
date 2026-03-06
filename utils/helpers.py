"""
NA Travels - Utility Functions
"""
import os
import re
import uuid
import bcrypt
from datetime import datetime, timezone
from functools import wraps
from flask import current_app, request, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from PIL import Image
from bson import ObjectId
import json


# ── JSON Encoder for MongoDB ObjectId ────────────────────────────────────────
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def mongo_to_dict(doc):
    """Convert MongoDB document to JSON-serializable dict."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [mongo_to_dict(d) for d in doc]
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, list):
            result[key] = [mongo_to_dict(v) if isinstance(v, dict) else
                           (str(v) if isinstance(v, ObjectId) else v) for v in value]
        elif isinstance(value, dict):
            result[key] = mongo_to_dict(value)
        else:
            result[key] = value
    return result


# ── Password ──────────────────────────────────────────────────────────────────
def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def check_password(password: str, hashed: bytes) -> bool:
    if isinstance(hashed, str):
        hashed = hashed.encode()
    return bcrypt.checkpw(password.encode(), hashed)


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    return True, "OK"


# ── Email Tokens ──────────────────────────────────────────────────────────────
def get_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_email_token(email: str, salt: str = "email-verify") -> str:
    s = get_serializer()
    return s.dumps(email, salt=salt)


def verify_email_token(token: str, salt: str = "email-verify", max_age: int = 3600):
    """Returns email on success, None on failure."""
    s = get_serializer()
    try:
        email = s.loads(token, salt=salt, max_age=max_age)
        return email
    except (BadSignature, SignatureExpired):
        return None


# ── File Upload ───────────────────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file, folder: str, max_size: tuple = (1920, 1080)) -> str | None:
    """Save and optimize uploaded image. Returns relative path or None."""
    if not file or not allowed_file(file.filename):
        return None

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = os.path.join(current_app.root_path, current_app.config["UPLOAD_FOLDER"], folder)
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)

    try:
        img = Image.open(file)
        img = img.convert("RGB")
        img.thumbnail(max_size, Image.LANCZOS)
        img.save(filepath, optimize=True, quality=85)
        return f"{current_app.config['UPLOAD_FOLDER']}/{folder}/{filename}"
    except Exception as e:
        current_app.logger.error(f"Image save error: {e}")
        return None


def delete_image(path: str):
    """Delete image file."""
    if path:
        full_path = os.path.join(current_app.root_path, path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception as e:
                current_app.logger.error(f"Image delete error: {e}")


# ── Slug ──────────────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


# ── Decorators ────────────────────────────────────────────────────────────────
def admin_required(fn):
    """Decorator: require admin role."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from app import mongo
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user or user.get("role") != "admin":
            return jsonify({"success": False, "message": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper


def verified_required(fn):
    """Decorator: require verified email."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from app import mongo
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user or not user.get("is_verified"):
            return jsonify({"success": False, "message": "Email verification required"}), 403
        return fn(*args, **kwargs)
    return wrapper


# ── Pagination ────────────────────────────────────────────────────────────────
def get_pagination_params():
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(50, max(1, int(request.args.get("per_page", 10))))
    return page, per_page


def paginate_cursor(cursor, page: int, per_page: int, total: int):
    skip = (page - 1) * per_page
    items = list(cursor.skip(skip).limit(per_page))
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "has_next": page * per_page < total,
        "has_prev": page > 1,
    }


def now_utc():
    return datetime.now(timezone.utc)
