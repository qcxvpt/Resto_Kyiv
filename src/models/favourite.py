from src.extensions import db


class Favourite(db.Model):
    """User's saved / favourite restaurants."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    resto_id = db.Column(db.Integer, nullable=False)
    __table_args__ = (
        db.UniqueConstraint("user_id", "resto_id", name="uq_user_resto"),
    )
