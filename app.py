"""
RestoKyiv — Flask restaurant guide for Kyiv.
Application factory entry point.
"""

from src.extensions import db, bcrypt, csrf, limiter
from src.api.restaurants import restaurants_bp
from src.api.reviews import reviews_bp
from src.api.favourites import favourites_bp
from src.api.stats import stats_bp
from src.auth.routes import auth_bp
from src.main import main_bp

import os
from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///restok.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["WTF_CSRF_ENABLED"] = True

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(restaurants_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(favourites_bp)
    app.register_blueprint(stats_bp)

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=False, host="127.0.0.1", port=5000)
