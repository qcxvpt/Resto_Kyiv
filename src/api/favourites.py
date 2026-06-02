"""API: favourites (add / remove / list)."""

from flask import Blueprint, jsonify, session
from src.extensions import db
from src.models.review import Review
from src.models.favourite import Favourite
from src.data import get_resto
from src.utils import login_required

favourites_bp = Blueprint("favourites", __name__)


@favourites_bp.route("/api/favourites", methods=["GET"])
@login_required
def get_favourites():
    favs = Favourite.query.filter_by(user_id=session["user_id"]).all()
    result = []
    for f in favs:
        r = get_resto(f.resto_id)
        if r:
            reviews = Review.query.filter_by(resto_id=r["id"]).all()
            avg = (
                round(sum(rv.rating for rv in reviews) / len(reviews), 1)
                if reviews else None
            )
            result.append({**r, "avg_rating": avg, "review_count": len(reviews)})
    return jsonify(result)


@favourites_bp.route("/api/favourites/<int:resto_id>", methods=["POST"])
@login_required
def add_favourite(resto_id):
    if not get_resto(resto_id):
        return jsonify({"error": "Unknown restaurant"}), 400
    existing = Favourite.query.filter_by(user_id=session["user_id"], resto_id=resto_id).first()
    if existing:
        return jsonify({"ok": True, "already": True})
    db.session.add(Favourite(user_id=session["user_id"], resto_id=resto_id))
    db.session.commit()
    return jsonify({"ok": True})


@favourites_bp.route("/api/favourites/<int:resto_id>", methods=["DELETE"])
@login_required
def remove_favourite(resto_id):
    fav = Favourite.query.filter_by(
        user_id=session["user_id"], resto_id=resto_id
    ).first_or_404()
    db.session.delete(fav)
    db.session.commit()
    return jsonify({"ok": True})
