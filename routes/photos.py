"""
NA Travels - Photos Routes
POST   /api/photos/review/:review_id          - Add photos to review
POST   /api/photos/destination/:dest_id       - Upload photo for destination (public contribution)
DELETE /api/photos/:photo_id                  - Delete own photo
GET    /api/photos/destination/:dest_id       - Get all photos for destination
POST   /api/photos/:photo_id/like             - Like photo
"""
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from app import mongo
from utils.helpers import save_image, delete_image, mongo_to_dict, now_utc, get_pagination_params, paginate_cursor

photos_bp = Blueprint("photos", __name__)


# ── Serve Static Uploads ──────────────────────────────────────────────────────
@photos_bp.route("/static/uploads/<path:filename>")
def uploaded_file(filename):
    import os
    return send_from_directory(
        os.path.join(current_app.root_path, "static", "uploads"),
        filename
    )


# ── Upload Photos for Review ──────────────────────────────────────────────────
@photos_bp.route("/review/<review_id>", methods=["POST"])
@jwt_required()
def add_review_photos(review_id):
    user_id = get_jwt_identity()

    if not ObjectId.is_valid(review_id):
        return jsonify({"success": False, "message": "Invalid review ID"}), 400

    review = mongo.db.reviews.find_one({"_id": ObjectId(review_id)})
    if not review:
        return jsonify({"success": False, "message": "Review not found"}), 404

    if review["user_id"] != user_id:
        return jsonify({"success": False, "message": "You can only add photos to your own reviews"}), 403

    files = request.files.getlist("photos")
    if not files:
        return jsonify({"success": False, "message": "No files provided"}), 400

    if len(files) > 10:
        return jsonify({"success": False, "message": "Maximum 10 photos per review"}), 400

    saved_paths = []
    for file in files:
        path = save_image(file, "photos")
        if path:
            saved_paths.append(f"/{path}")

    if not saved_paths:
        return jsonify({"success": False, "message": "No valid images uploaded"}), 400

    mongo.db.reviews.update_one(
        {"_id": ObjectId(review_id)},
        {"$push": {"photos": {"$each": saved_paths}}, "$set": {"updated_at": now_utc()}}
    )

    return jsonify({
        "success": True,
        "message": f"{len(saved_paths)} photo(s) added",
        "photos": saved_paths
    }), 201


# ── Upload Photo for Destination (Gallery Contribution) ───────────────────────
@photos_bp.route("/destination/<destination_id>", methods=["POST"])
@jwt_required()
def upload_destination_photo(destination_id):
    user_id = get_jwt_identity()

    if not ObjectId.is_valid(destination_id):
        return jsonify({"success": False, "message": "Invalid destination ID"}), 400

    dest = mongo.db.destinations.find_one({"_id": ObjectId(destination_id), "is_published": True})
    if not dest:
        return jsonify({"success": False, "message": "Destination not found"}), 404

    if "photo" not in request.files:
        return jsonify({"success": False, "message": "No photo provided"}), 400

    file = request.files["photo"]
    caption = request.form.get("caption", "").strip()
    path = save_image(file, "destinations")

    if not path:
        return jsonify({"success": False, "message": "Invalid image file"}), 400

    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    photo_doc = {
        "destination_id": destination_id,
        "user_id": user_id,
        "user_name": user.get("full_name") if user else "Anonymous",
        "user_username": user.get("username") if user else "",
        "url": f"/{path}",
        "caption": caption,
        "likes": [],
        "likes_count": 0,
        "is_approved": True,
        "created_at": now_utc(),
    }

    result = mongo.db.photos.insert_one(photo_doc)
    photo_doc["_id"] = result.inserted_id

    return jsonify({
        "success": True,
        "message": "Photo uploaded successfully",
        "photo": mongo_to_dict(photo_doc)
    }), 201


# ── Get Destination Photos ────────────────────────────────────────────────────
@photos_bp.route("/destination/<destination_id>", methods=["GET"])
def get_destination_photos(destination_id):
    if not ObjectId.is_valid(destination_id):
        return jsonify({"success": False, "message": "Invalid destination ID"}), 400

    page, per_page = get_pagination_params()
    query = {"destination_id": destination_id, "is_approved": True}
    total = mongo.db.photos.count_documents(query)
    cursor = mongo.db.photos.find(query).sort("created_at", -1)
    result = paginate_cursor(cursor, page, per_page, total)
    result["items"] = mongo_to_dict(result["items"])

    return jsonify({"success": True, **result})


# ── Delete Photo ──────────────────────────────────────────────────────────────
@photos_bp.route("/<photo_id>", methods=["DELETE"])
@jwt_required()
def delete_photo(photo_id):
    user_id = get_jwt_identity()

    if not ObjectId.is_valid(photo_id):
        return jsonify({"success": False, "message": "Invalid photo ID"}), 400

    photo = mongo.db.photos.find_one({"_id": ObjectId(photo_id)})
    if not photo:
        return jsonify({"success": False, "message": "Photo not found"}), 404

    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if photo["user_id"] != user_id and user.get("role") != "admin":
        return jsonify({"success": False, "message": "Permission denied"}), 403

    delete_image(photo["url"].lstrip("/"))
    mongo.db.photos.delete_one({"_id": ObjectId(photo_id)})

    return jsonify({"success": True, "message": "Photo deleted"})


# ── Like Photo ────────────────────────────────────────────────────────────────
@photos_bp.route("/<photo_id>/like", methods=["POST"])
@jwt_required()
def like_photo(photo_id):
    user_id = get_jwt_identity()

    if not ObjectId.is_valid(photo_id):
        return jsonify({"success": False, "message": "Invalid photo ID"}), 400

    photo = mongo.db.photos.find_one({"_id": ObjectId(photo_id)})
    if not photo:
        return jsonify({"success": False, "message": "Photo not found"}), 404

    likes = photo.get("likes", [])
    if user_id in likes:
        mongo.db.photos.update_one(
            {"_id": ObjectId(photo_id)},
            {"$pull": {"likes": user_id}, "$inc": {"likes_count": -1}}
        )
        liked = False
    else:
        mongo.db.photos.update_one(
            {"_id": ObjectId(photo_id)},
            {"$addToSet": {"likes": user_id}, "$inc": {"likes_count": 1}}
        )
        liked = True

    updated = mongo.db.photos.find_one({"_id": ObjectId(photo_id)}, {"likes_count": 1})
    return jsonify({"success": True, "liked": liked, "likes_count": updated.get("likes_count", 0)})
