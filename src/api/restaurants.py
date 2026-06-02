"""API: restaurants list."""

from flask import Blueprint, jsonify
from src.models.review import Review
from src.data import RESTAURANTS

restaurants_bp = Blueprint("restaurants", __name__)


@restaurants_bp.route("/api/restaurants")
def api_restaurants():
    result = []
    for r in RESTAURANTS:
        reviews = Review.query.filter_by(resto_id=r["id"]).all()
        avg = (
            round(sum(rv.rating for rv in reviews) / len(reviews), 1)
            if reviews
            else None
        )
        result.append({**r, "avg_rating": avg, "review_count": len(reviews)})
    return jsonify(result)
