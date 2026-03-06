"""
NA Travels - Reviews Routes
GET    /api/reviews/destination/:destination_id  - Get reviews for destination
POST   /api/reviews/destination/:destination_id  - Create review
PUT    /api/reviews/:review_id                   - Update own review
DELETE /api/reviews/:review_id                   - Delete own review
POST   /api/reviews/:review_id/like              - Like/unlike review
GET    /api/reviews/:review_id                   - Get single review
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from bson import ObjectId
from app import mongo
from utils.helpers import mongo_to_dict, get_pagination_params, paginate_cursor, now_utc, save_image

reviews_bp = Blueprint("reviews", __name__)


def _update_destination_rating(destination_id: str):
    """Recalculate and update destination's average rating."""
    pipeline = [
        {"$match": {"destination_id": destination_id, "is_approved": True}},
        {"$group": {
            "_id": None,
            "avg": {"$avg": "$rating"},
            "count": {"$sum": 1}
        }}
    ]
    result = list(mongo.db.reviews.aggregate(pipeline))
    if result:
        avg = round(result[0]["avg"], 1)
        count = result[0]["count"]
    else:
        avg = 0
        count = 0

    mongo.db.destinations.update_one(
        {"_id": ObjectId(destination_id)},
        {"$set": {"average_rating": avg, "review_count": count}}
    )


# ── Get Reviews for Destination ───────────────────────────────────────────────
@reviews_bp.route("/destination/<destination_id>", methods=["GET"])
def get_destination_reviews(destination_id):
    if not ObjectId.is_valid(destination_id):
        return jsonify({"success": False, "message": "Invalid destination ID"}), 400

    page, per_page = get_pagination_params()
    sort_by = request.args.get("sort", "created_at")
    sort_map = {
        "created_at": [("created_at", -1)],
        "rating_high": [("rating", -1)],
        "rating_low": [("rating", 1)],
        "likes": [("likes_count", -1)],
    }
    sort = sort_map.get(sort_by, [("created_at", -1)])

    query = {"destination_id": destination_id, "is_approved": True}
    total = mongo.db.reviews.count_documents(query)
    cursor = mongo.db.reviews.find(query).sort(sort)
    result = paginate_cursor(cursor, page, per_page, total)
    result["items"] = mongo_to_dict(result["items"])

    # Rating breakdown
    pipeline = [
        {"$match": query},
        {"$group": {"_id": "$rating", "count": {"$sum": 1}}}
    ]
    breakdown = {str(r["_id"]): r["count"] for r in mongo.db.reviews.aggregate(pipeline)}

    return jsonify({
        "success": True,
        "rating_breakdown": breakdown,
        **result
    })


# ── Create Review ─────────────────────────────────────────────────────────────
@reviews_bp.route("/destination/<destination_id>", methods=["POST"])
@jwt_required()
def create_review(destination_id):
    user_id = get_jwt_identity()

    if not ObjectId.is_valid(destination_id):
        return jsonify({"success": False, "message": "Invalid destination ID"}), 400

    dest = mongo.db.destinations.find_one({"_id": ObjectId(destination_id), "is_published": True})
    if not dest:
        return jsonify({"success": False, "message": "Destination not found"}), 404

    # One review per user per destination
    existing = mongo.db.reviews.find_one({"destination_id": destination_id, "user_id": user_id})
    if existing:
        return jsonify({"success": False, "message": "You've already reviewed this destination. Edit your existing review."}), 409

    data = request.get_json(silent=True) or {}
    rating = data.get("rating")
    title = data.get("title", "").strip()
    body = data.get("body", "").strip()
    visit_date = data.get("visit_date", "")
    travel_type = data.get("travel_type", "")  # solo, couple, family, group, business

    if not rating or not isinstance(rating, (int, float)):
        return jsonify({"success": False, "message": "Rating is required (1-5)"}), 400

    rating = float(rating)
    if not (1 <= rating <= 5):
        return jsonify({"success": False, "message": "Rating must be between 1 and 5"}), 400

    if not body or len(body) < 20:
        return jsonify({"success": False, "message": "Review body must be at least 20 characters"}), 400

    # Get user info
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})

    review_doc = {
        "destination_id": destination_id,
        "destination_name": dest.get("name"),
        "user_id": user_id,
        "user_name": user.get("full_name") if user else "Anonymous",
        "user_username": user.get("username") if user else "",
        "user_avatar": user.get("avatar") if user else None,
        "rating": rating,
        "title": title,
        "body": body,
        "visit_date": visit_date,
        "travel_type": travel_type,
        "photos": [],
        "likes": [],
        "likes_count": 0,
        "is_approved": True,  # Auto-approve; set False for moderation
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }

    result = mongo.db.reviews.insert_one(review_doc)
    review_doc["_id"] = result.inserted_id

    _update_destination_rating(destination_id)

    return jsonify({
        "success": True,
        "message": "Review submitted successfully",
        "review": mongo_to_dict(review_doc)
    }), 201


# ── Update Review ─────────────────────────────────────────────────────────────
@reviews_bp.route("/<review_id>", methods=["PUT"])
@jwt_required()
def update_review(review_id):
    user_id = get_jwt_identity()

    if not ObjectId.is_valid(review_id):
        return jsonify({"success": False, "message": "Invalid review ID"}), 400

    review = mongo.db.reviews.find_one({"_id": ObjectId(review_id)})
    if not review:
        return jsonify({"success": False, "message": "Review not found"}), 404

    if review["user_id"] != user_id:
        return jsonify({"success": False, "message": "You can only edit your own reviews"}), 403

    data = request.get_json(silent=True) or {}
    updates = {}

    if "rating" in data:
        rating = float(data["rating"])
        if not (1 <= rating <= 5):
            return jsonify({"success": False, "message": "Rating must be between 1 and 5"}), 400
        updates["rating"] = rating

    if "title" in data:
        updates["title"] = data["title"].strip()

    if "body" in data:
        body = data["body"].strip()
        if len(body) < 20:
            return jsonify({"success": False, "message": "Review body must be at least 20 characters"}), 400
        updates["body"] = body

    if "visit_date" in data:
        updates["visit_date"] = data["visit_date"]

    if "travel_type" in data:
        updates["travel_type"] = data["travel_type"]

    if not updates:
        return jsonify({"success": False, "message": "No valid fields to update"}), 400

    updates["updated_at"] = now_utc()
    mongo.db.reviews.update_one({"_id": ObjectId(review_id)}, {"$set": updates})

    if "rating" in updates:
        _update_destination_rating(review["destination_id"])

    updated = mongo.db.reviews.find_one({"_id": ObjectId(review_id)})
    return jsonify({"success": True, "message": "Review updated", "review": mongo_to_dict(updated)})


# ── Delete Review ─────────────────────────────────────────────────────────────
@reviews_bp.route("/<review_id>", methods=["DELETE"])
@jwt_required()
def delete_review(review_id):
    user_id = get_jwt_identity()

    if not ObjectId.is_valid(review_id):
        return jsonify({"success": False, "message": "Invalid review ID"}), 400

    review = mongo.db.reviews.find_one({"_id": ObjectId(review_id)})
    if not review:
        return jsonify({"success": False, "message": "Review not found"}), 404

    # Allow owner or admin
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if review["user_id"] != user_id and user.get("role") != "admin":
        return jsonify({"success": False, "message": "Permission denied"}), 403

    destination_id = review["destination_id"]
    mongo.db.reviews.delete_one({"_id": ObjectId(review_id)})
    _update_destination_rating(destination_id)

    return jsonify({"success": True, "message": "Review deleted"})


# ── Like / Unlike Review ──────────────────────────────────────────────────────
@reviews_bp.route("/<review_id>/like", methods=["POST"])
@jwt_required()
def like_review(review_id):
    user_id = get_jwt_identity()

    if not ObjectId.is_valid(review_id):
        return jsonify({"success": False, "message": "Invalid review ID"}), 400

    review = mongo.db.reviews.find_one({"_id": ObjectId(review_id)})
    if not review:
        return jsonify({"success": False, "message": "Review not found"}), 404

    likes = review.get("likes", [])
    if user_id in likes:
        # Unlike
        mongo.db.reviews.update_one(
            {"_id": ObjectId(review_id)},
            {"$pull": {"likes": user_id}, "$inc": {"likes_count": -1}}
        )
        liked = False
    else:
        # Like
        mongo.db.reviews.update_one(
            {"_id": ObjectId(review_id)},
            {"$addToSet": {"likes": user_id}, "$inc": {"likes_count": 1}}
        )
        liked = True

    updated = mongo.db.reviews.find_one({"_id": ObjectId(review_id)}, {"likes_count": 1})
    return jsonify({
        "success": True,
        "liked": liked,
        "likes_count": updated.get("likes_count", 0)
    })


# ── Get Single Review ─────────────────────────────────────────────────────────
@reviews_bp.route("/<review_id>", methods=["GET"])
def get_review(review_id):
    if not ObjectId.is_valid(review_id):
        return jsonify({"success": False, "message": "Invalid review ID"}), 400

    review = mongo.db.reviews.find_one({"_id": ObjectId(review_id)})
    if not review:
        return jsonify({"success": False, "message": "Review not found"}), 404

    return jsonify({"success": True, "review": mongo_to_dict(review)})
