"""API: aggregate statistics."""

from flask import Blueprint, jsonify
from src.models.user import User
from src.models.review import Review
from src.data import RESTAURANTS

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/api/stats")
def api_stats():
    total_reviews = Review.query.count()
    total_users = User.query.count()

    top_rated = None
    best_avg = -1.0
    for r in RESTAURANTS:
        reviews = Review.query.filter_by(resto_id=r["id"]).all()
        if reviews:
            avg = sum(rv.rating for rv in reviews) / len(reviews)
            if avg > best_avg:
                best_avg = avg
                top_rated = {"id": r["id"], "name": r["name"], "avg": round(avg, 2)}

    cuisine_counts: dict = {}
    for r in RESTAURANTS:
        c = r["cuisine"]
        cuisine_counts[c] = cuisine_counts.get(c, 0) + 1

    return jsonify({
        "total_restaurants": len(RESTAURANTS),
        "total_reviews": total_reviews,
        "total_users": total_users,
        "top_rated": top_rated,
        "cuisine_breakdown": cuisine_counts,
    })
