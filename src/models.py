from datetime import datetime
from app import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    reviews = db.relationship(
        "Review",
        backref="author",
        lazy=True,
        cascade="all, delete-orphan"
    )


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    resto_id = db.Column(db.Integer, nullable=False)
    anonymous = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )


class Favourite(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    resto_id = db.Column(
        db.Integer,
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "resto_id",
            name="uq_user_resto"
        ),
    )