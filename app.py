"""
NA Travels - Main Application Entry Point
Tourist Website Backend API
"""
import os
import logging
from flask import Flask, jsonify
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# Initialize extensions
mongo = PyMongo()
jwt = JWTManager()
mail = Mail()
limiter = Limiter(key_func=get_remote_address)

def create_app():
    app = Flask(__name__)

    # ── Logging ──────────────────────────────────────────────────────────────
    logging.basicConfig(level=logging.INFO)

    # ── Config ───────────────────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["MONGO_URI"] = os.environ.get("MONGO_URI", "mongodb://localhost:27017/na_travels")

    # JWT
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "jwt-secret-change-me")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(seconds=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 3600)))
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(seconds=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", 2592000)))
    app.config["JWT_TOKEN_LOCATION"] = ["headers"]
    app.config["JWT_HEADER_NAME"] = "Authorization"
    app.config["JWT_HEADER_TYPE"] = "Bearer"

    # Mail
    app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "True") == "True"
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", "NA Travels <noreply@natravels.com>")

    # File Upload
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))  # 10MB
    app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", "static/uploads")
    app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif", "webp"}

    # Google OAuth
    app.config["GOOGLE_CLIENT_ID"] = os.environ.get("GOOGLE_CLIENT_ID")
    app.config["GOOGLE_CLIENT_SECRET"] = os.environ.get("GOOGLE_CLIENT_SECRET")
    app.config["FRONTEND_URL"] = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    # ── Extensions Init ───────────────────────────────────────────────────────
    mongo.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                app.config["FRONTEND_URL"],
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:8080",
            ],
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "expose_headers": ["Content-Range", "X-Content-Range"],
            "supports_credentials": True,
            "max_age": 86400,
        }
    })

    # ── JWT Error Handlers ────────────────────────────────────────────────────
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"success": False, "message": "Token has expired"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"success": False, "message": "Invalid token"}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"success": False, "message": "Authorization token required"}), 401

    # ── Upload folder ─────────────────────────────────────────────────────────
    os.makedirs(os.path.join(app.root_path, app.config["UPLOAD_FOLDER"], "photos"), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, app.config["UPLOAD_FOLDER"], "avatars"), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, app.config["UPLOAD_FOLDER"], "destinations"), exist_ok=True)

    # ── Register Blueprints ───────────────────────────────────────────────────
    from routes.auth import auth_bp
    from routes.user import user_bp
    from routes.destinations import destinations_bp
    from routes.reviews import reviews_bp
    from routes.photos import photos_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(destinations_bp, url_prefix="/api/destinations")
    app.register_blueprint(reviews_bp, url_prefix="/api/reviews")
    app.register_blueprint(photos_bp, url_prefix="/api/photos")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # ── DB Indexes ────────────────────────────────────────────────────────────
    with app.app_context():
        try:
            mongo.db.users.create_index("email", unique=True)
            mongo.db.users.create_index("username", unique=True)
            mongo.db.destinations.create_index("slug", unique=True)
            mongo.db.destinations.create_index([("name", "text"), ("description", "text"), ("location", "text")])
            mongo.db.reviews.create_index([("destination_id", 1), ("created_at", -1)])
            mongo.db.reviews.create_index([("user_id", 1)])
            app.logger.info("✅ MongoDB indexes created")
        except Exception as e:
            app.logger.warning(f"Index creation warning: {e}")

        # Create default admin
        _create_default_admin(app)

    # ── Health Check ──────────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return jsonify({
            "success": True,
            "message": "NA Travels API",
            "version": "1.0.0",
            "docs": "/admin"
        })

    @app.route("/health")
    def health():
        return jsonify({"status": "healthy", "service": "na-travels-api"})

    # ── Global Error Handlers ─────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "message": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"success": False, "message": "Method not allowed"}), 405

    @app.errorhandler(413)
    def file_too_large(e):
        return jsonify({"success": False, "message": "File too large. Max size is 10MB"}), 413

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"Internal error: {e}")
        return jsonify({"success": False, "message": "Internal server error"}), 500

    return app


def _create_default_admin(app):
    import bcrypt
    from datetime import datetime, timezone
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@natravels.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin123!")
    existing = mongo.db.users.find_one({"email": admin_email})
    if not existing:
        hashed = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt())
        mongo.db.users.insert_one({
            "email": admin_email,
            "username": "admin",
            "full_name": "NA Travels Admin",
            "password": hashed,
            "role": "admin",
            "is_verified": True,
            "auth_provider": "email",
            "avatar": None,
            "bio": "",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })
        app.logger.info(f"✅ Default admin created: {admin_email}")


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
