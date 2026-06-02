import os

from models import User, Review, Favourite
from flask import Flask, Blueprint, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
bcrypt = Bcrypt()
csrf = CSRFProtect()
limiter = Limiter(get_remote_address, default_limits=["300 per day"])

main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("main.html")


def create_app():
    application = Flask(__name__)

    application.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "dev-secret-change-in-prod"
    )

    application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///restok.db"
    application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(application)
    bcrypt.init_app(application)
    csrf.init_app(application)
    limiter.init_app(application)

    application.register_blueprint(main)

    return application


app = create_app()