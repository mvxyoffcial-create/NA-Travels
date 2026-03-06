"""
NA Travels - Destinations Routes
GET    /api/destinations              - List/search destinations
GET    /api/destinations/featured     - Featured destinations
GET    /api/destinations/categories   - All categories
GET    /api/destinations/:slug        - Single destination
"""
from flask import Blueprint, request, jsonify
from bson import ObjectId
from app import mongo
from utils.helpers import mongo_to_dict, get_pagination_params, paginate_cursor

destinations_bp = Blueprint("destinations", __name__)


# ── List / Search ─────────────────────────────────────────────────────────────
@destinations_bp.route("/", methods=["GET"])
def list_destinations():
    page, per_page = get_pagination_params()
    query = {}

    # Search
    search = request.args.get("q", "").strip()
    if search:
        query["$text"] = {"$search": search}

    # Filters
    category = request.args.get("category")
    if category:
        query["category"] = category

    country = request.args.get("country")
    if country:
        query["country"] = {"$regex": country, "$options": "i"}

    # Only published
    query["is_published"] = True

    # Sort
    sort_by = request.args.get("sort", "created_at")
    sort_map = {
        "created_at": [("created_at", -1)],
        "rating": [("average_rating", -1)],
        "popular": [("review_count", -1)],
        "name": [("name", 1)],
    }
    sort = sort_map.get(sort_by, [("created_at", -1)])

    total = mongo.db.destinations.count_documents(query)
    cursor = mongo.db.destinations.find(query).sort(sort)
    result = paginate_cursor(cursor, page, per_page, total)
    result["items"] = mongo_to_dict(result["items"])

    return jsonify({"success": True, **result})


# ── Featured ──────────────────────────────────────────────────────────────────
@destinations_bp.route("/featured", methods=["GET"])
def featured_destinations():
    limit = min(12, int(request.args.get("limit", 6)))
    destinations = list(
        mongo.db.destinations.find({"is_published": True, "is_featured": True})
        .sort("average_rating", -1)
        .limit(limit)
    )
    return jsonify({"success": True, "destinations": mongo_to_dict(destinations)})


# ── Categories ────────────────────────────────────────────────────────────────
@destinations_bp.route("/categories", methods=["GET"])
def get_categories():
    pipeline = [
        {"$match": {"is_published": True}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    categories = list(mongo.db.destinations.aggregate(pipeline))
    return jsonify({
        "success": True,
        "categories": [{"name": c["_id"], "count": c["count"]} for c in categories if c["_id"]]
    })


# ── Countries ─────────────────────────────────────────────────────────────────
@destinations_bp.route("/countries", methods=["GET"])
def get_countries():
    pipeline = [
        {"$match": {"is_published": True}},
        {"$group": {"_id": "$country", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    countries = list(mongo.db.destinations.aggregate(pipeline))
    return jsonify({
        "success": True,
        "countries": [{"name": c["_id"], "count": c["count"]} for c in countries if c["_id"]]
    })


# ── Single Destination ────────────────────────────────────────────────────────
@destinations_bp.route("/<slug>", methods=["GET"])
def get_destination(slug):
    # Try by slug first, then by ID
    if ObjectId.is_valid(slug):
        dest = mongo.db.destinations.find_one({"_id": ObjectId(slug), "is_published": True})
    else:
        dest = mongo.db.destinations.find_one({"slug": slug, "is_published": True})

    if not dest:
        return jsonify({"success": False, "message": "Destination not found"}), 404

    # Increment view count
    mongo.db.destinations.update_one({"_id": dest["_id"]}, {"$inc": {"views": 1}})

    # Get recent reviews
    reviews = list(
        mongo.db.reviews.find({"destination_id": str(dest["_id"]), "is_approved": True})
        .sort("created_at", -1)
        .limit(5)
    )

    result = mongo_to_dict(dest)
    result["recent_reviews"] = mongo_to_dict(reviews)

    return jsonify({"success": True, "destination": result})
