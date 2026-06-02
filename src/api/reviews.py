"""API: reviews CRUD, my-review, csrf-token."""

from flask import Blueprint, jsonify, request, session, abort
from flask_wtf.csrf import generate_csrf
from src.extensions import db
from src.models.review import Review
from src.data import get_resto
from src.utils import login_required, sanitize

reviews_bp = Blueprint("reviews", __name__)


@reviews_bp.route("/api/reviews/<int:resto_id>")
def api_reviews(resto_id):
    reviews = (
        Review.query.filter_by(resto_id=resto_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return jsonify([
        {
            "id": rv.id,
            "text": rv.text,
            "rating": rv.rating,
            "author": "Anonymous" if rv.anonymous else rv.author.username,
            "anonymous": rv.anonymous,
            "user_id": rv.user_id,
            "created_at": rv.created_at.strftime("%d.%m.%Y"),
            "mine": rv.user_id == session.get("user_id"),
        }
        for rv in reviews
    ])


@reviews_bp.route("/api/reviews", methods=["POST"])
@login_required
def post_review():
    data = request.get_json(force=True) or {}
    resto_id = int(data.get("resto_id", 0))
    text = sanitize(str(data.get("text", "")), 500)
    rating = int(data.get("rating", 0))
    anonymous = bool(data.get("anonymous", False))

    if not get_resto(resto_id):
        return jsonify({"error": "Unknown restaurant"}), 400
    if not text or len(text) < 3:
        return jsonify({"error": "Review too short"}), 400
    if rating < 1 or rating > 5:
        return jsonify({"error": "Rating must be 1-5"}), 400

    existing = Review.query.filter_by(resto_id=resto_id, user_id=session["user_id"]).first()
    if existing:
        return jsonify({"error": "already_reviewed", "review_id": existing.id}), 409

    db.session.add(Review(
        text=text, rating=rating, resto_id=resto_id,
        user_id=session["user_id"], anonymous=anonymous,
    ))
    db.session.commit()
    return jsonify({"ok": True})


@reviews_bp.route("/api/reviews/<int:review_id>", methods=["PUT"])
@login_required
def edit_review(review_id):
    rv = db.get_or_404(Review, review_id)
    if rv.user_id != session["user_id"]:
        abort(403)
    data = request.get_json(force=True) or {}
    text = sanitize(str(data.get("text", "")), 500)
    rating = int(data.get("rating", 0))
    anonymous = bool(data.get("anonymous", False))
    if not text or len(text) < 3:
        return jsonify({"error": "Review too short"}), 400
    if rating < 1 or rating > 5:
        return jsonify({"error": "Rating must be 1-5"}), 400
    rv.text, rv.rating, rv.anonymous = text, rating, anonymous
    db.session.commit()
    return jsonify({"ok": True})


@reviews_bp.route("/api/reviews/<int:review_id>", methods=["DELETE"])
@login_required
def delete_review(review_id):
    rv = db.get_or_404(Review, review_id)
    if rv.user_id != session["user_id"]:
        abort(403)
    db.session.delete(rv)
    db.session.commit()
    return jsonify({"ok": True})


@reviews_bp.route("/api/my-review/<int:resto_id>")
@login_required
def my_review(resto_id):
    rv = Review.query.filter_by(resto_id=resto_id, user_id=session["user_id"]).first()
    if not rv:
        return jsonify(None)
    return jsonify({"id": rv.id, "text": rv.text, "rating": rv.rating, "anonymous": rv.anonymous})


@reviews_bp.route("/api/csrf-token")
def csrf_token():
    return jsonify({"token": generate_csrf()})
